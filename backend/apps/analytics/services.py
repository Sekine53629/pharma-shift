"""Musubi Insight スクレイピングサービス

Musubi Insight から処方実績データを取得する。
Selenium WebDriver を使用し、各店舗の日次処方枚数を取得する。

環境変数:
    MUSUBI_LOGIN_URL: ログインページURL
    MUSUBI_USERNAME: ログインID
    MUSUBI_PASSWORD: ログインパスワード

Note:
    Selenium + ChromeDriver が必要。
    本番環境では headless Chrome を使用する。
    pip install selenium
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings

from apps.stores.models import Store

from .models import PrescriptionForecast, PrescriptionRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Musubi Scraper
# ---------------------------------------------------------------------------

class MusubiScraper:
    """Musubi Insight から処方実績を取得するスクレイパー"""

    def __init__(self):
        self.login_url = getattr(settings, "MUSUBI_LOGIN_URL", "")
        self.username = getattr(settings, "MUSUBI_USERNAME", "")
        self.password = getattr(settings, "MUSUBI_PASSWORD", "")
        self.driver = None

    def _init_driver(self):
        """Selenium WebDriver を初期化（headless Chrome）"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except ImportError:
            raise RuntimeError(
                "selenium がインストールされていません。"
                "pip install selenium を実行してください。"
            )

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)

    def _login(self) -> bool:
        """Musubi Insight にログイン"""
        if not all([self.login_url, self.username, self.password]):
            logger.warning("Musubi credentials not configured")
            return False

        try:
            from selenium.webdriver.common.by import By

            self.driver.get(self.login_url)
            self.driver.find_element(By.ID, "username").send_keys(self.username)
            self.driver.find_element(By.ID, "password").send_keys(self.password)
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

            # ログイン後のダッシュボード表示を待機
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".dashboard, #main-content"))
            )
            logger.info("Musubi login successful")
            return True
        except Exception:
            logger.exception("Musubi login failed")
            return False

    def _fetch_store_prescriptions(self, store_name: str, target_date: date) -> int | None:
        """指定店舗の指定日の処方枚数を取得

        Returns:
            処方枚数。取得失敗時は None。
        """
        try:
            from selenium.webdriver.common.by import By

            # 処方実績ページへ遷移（URL パターンは Musubi の実装に依存）
            date_str = target_date.strftime("%Y-%m-%d")
            self.driver.get(
                f"{self.login_url.rstrip('/')}/prescriptions?"
                f"store={store_name}&date={date_str}"
            )

            # 処方枚数要素を取得
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-prescription-count], .prescription-count")
                )
            )
            count_text = elem.text.replace(",", "").strip()
            return int(count_text)
        except Exception:
            logger.warning("Failed to fetch prescriptions for %s on %s", store_name, target_date)
            return None

    def scrape_all_stores(self, target_date: date) -> dict:
        """全店舗の処方実績をスクレイピング

        Returns:
            {"created": int, "skipped": int, "errors": list[str]}
        """
        self._init_driver()
        result = {"created": 0, "skipped": 0, "errors": []}

        try:
            if not self._login():
                result["errors"].append("Musubi ログイン失敗")
                return result

            stores = Store.objects.filter(is_active=True)
            for store in stores:
                count = self._fetch_store_prescriptions(store.name, target_date)
                if count is None:
                    result["skipped"] += 1
                    result["errors"].append(f"{store.name}: データ取得失敗")
                    continue

                PrescriptionRecord.objects.update_or_create(
                    store=store,
                    date=target_date,
                    defaults={
                        "count": count,
                        "source": PrescriptionRecord.Source.SCRAPING,
                    },
                )
                result["created"] += 1

        finally:
            if self.driver:
                self.driver.quit()

        logger.info(
            "Musubi scraping complete: %d created, %d skipped, %d errors",
            result["created"], result["skipped"], len(result["errors"]),
        )
        return result


# ---------------------------------------------------------------------------
# LightGBM Forecast Service
# ---------------------------------------------------------------------------

def _build_features(store: Store, target_date: date) -> dict | None:
    """予測に使用する特徴量を構築

    特徴量:
        - 過去7日/14日/30日の平均処方枚数
        - 曜日 (0=Mon, 6=Sun)
        - 月
        - 祝日フラグ (簡易: 土日判定)
        - 店舗難易度
    """
    records_30d = PrescriptionRecord.objects.filter(
        store=store,
        date__gte=target_date - timedelta(days=30),
        date__lt=target_date,
    ).values_list("count", flat=True)

    counts = list(records_30d)
    if len(counts) < 7:
        return None  # データ不足

    avg_7d = sum(counts[:7]) / min(len(counts), 7)
    avg_14d = sum(counts[:14]) / min(len(counts), 14)
    avg_30d = sum(counts) / len(counts)

    return {
        "avg_7d": avg_7d,
        "avg_14d": avg_14d,
        "avg_30d": avg_30d,
        "day_of_week": target_date.weekday(),
        "month": target_date.month,
        "is_weekend": 1 if target_date.weekday() >= 5 else 0,
        "store_difficulty": float(store.effective_difficulty),
    }


def generate_forecasts_statistical(
    target_start: date,
    target_end: date,
    model_version: str = "statistical-v1",
) -> dict:
    """統計ベースの処方予測を生成（LightGBM が利用不可な場合のフォールバック）

    移動平均 + 曜日補正による簡易予測。
    LightGBM 導入後はこの関数を置き換える。

    Returns:
        {"created": int, "skipped": int}
    """
    stores = Store.objects.filter(is_active=True)
    created = 0
    skipped = 0

    for store in stores:
        current_date = target_start
        while current_date <= target_end:
            features = _build_features(store, current_date)
            if features is None:
                skipped += 1
                current_date += timedelta(days=1)
                continue

            # 曜日補正つき移動平均予測
            base = features["avg_7d"] * 0.5 + features["avg_14d"] * 0.3 + features["avg_30d"] * 0.2

            # 週末は処方枚数が少ない傾向
            if features["is_weekend"]:
                base *= 0.6

            predicted = max(int(round(base)), 0)
            # 信頼区間: ±20%
            lower = max(int(predicted * 0.8), 0)
            upper = int(predicted * 1.2)

            PrescriptionForecast.objects.update_or_create(
                store=store,
                date=current_date,
                defaults={
                    "predicted_count": predicted,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "model_version": model_version,
                },
            )
            created += 1
            current_date += timedelta(days=1)

    logger.info("Forecast generation complete: %d created, %d skipped", created, skipped)
    return {"created": created, "skipped": skipped}


def generate_forecasts_lightgbm(
    target_start: date,
    target_end: date,
    model_version: str = "lgbm-v1",
) -> dict:
    """LightGBM ベースの処方予測を生成

    Returns:
        {"created": int, "skipped": int}
    """
    try:
        import lightgbm as lgb
        import numpy as np
    except ImportError:
        logger.warning(
            "lightgbm / numpy not installed. Falling back to statistical forecast."
        )
        return generate_forecasts_statistical(target_start, target_end, "statistical-v1")

    stores = Store.objects.filter(is_active=True)
    created = 0
    skipped = 0

    feature_names = [
        "avg_7d", "avg_14d", "avg_30d",
        "day_of_week", "month", "is_weekend", "store_difficulty",
    ]

    for store in stores:
        # 学習データ: 過去 90 日分
        train_dates = [
            target_start - timedelta(days=i)
            for i in range(1, 91)
        ]

        X_train = []
        y_train = []
        for d in train_dates:
            feat = _build_features(store, d)
            if feat is None:
                continue
            actual = PrescriptionRecord.objects.filter(store=store, date=d).first()
            if actual is None:
                continue
            X_train.append([feat[f] for f in feature_names])
            y_train.append(actual.count)

        if len(X_train) < 14:
            # 学習データ不足 → 統計フォールバック
            current = target_start
            while current <= target_end:
                features = _build_features(store, current)
                if features:
                    base = features["avg_7d"] * 0.5 + features["avg_14d"] * 0.3 + features["avg_30d"] * 0.2
                    if features["is_weekend"]:
                        base *= 0.6
                    predicted = max(int(round(base)), 0)
                    PrescriptionForecast.objects.update_or_create(
                        store=store,
                        date=current,
                        defaults={
                            "predicted_count": predicted,
                            "lower_bound": max(int(predicted * 0.8), 0),
                            "upper_bound": int(predicted * 1.2),
                            "model_version": "statistical-v1",
                        },
                    )
                    created += 1
                else:
                    skipped += 1
                current += timedelta(days=1)
            continue

        X_train = np.array(X_train)
        y_train = np.array(y_train)

        dataset = lgb.Dataset(X_train, label=y_train, feature_name=feature_names)
        params = {
            "objective": "regression",
            "metric": "rmse",
            "num_leaves": 15,
            "learning_rate": 0.05,
            "n_estimators": 100,
            "verbose": -1,
        }
        model = lgb.train(params, dataset, num_boost_round=100)

        # 予測
        current = target_start
        while current <= target_end:
            feat = _build_features(store, current)
            if feat is None:
                skipped += 1
                current += timedelta(days=1)
                continue

            X_pred = np.array([[feat[f] for f in feature_names]])
            pred = model.predict(X_pred)[0]
            predicted = max(int(round(pred)), 0)

            # 信頼区間: RMSE ベース（学習データの標準偏差で近似）
            residuals = y_train - model.predict(X_train)
            rmse = float(np.sqrt(np.mean(residuals ** 2)))
            lower = max(int(predicted - 1.96 * rmse), 0)
            upper = int(predicted + 1.96 * rmse)

            PrescriptionForecast.objects.update_or_create(
                store=store,
                date=current,
                defaults={
                    "predicted_count": predicted,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "model_version": model_version,
                },
            )
            created += 1
            current += timedelta(days=1)

    logger.info(
        "LightGBM forecast complete: %d created, %d skipped", created, skipped
    )
    return {"created": created, "skipped": skipped}
