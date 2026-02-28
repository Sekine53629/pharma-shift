#!/usr/bin/env python
"""EDA: 気象データ × 処方枚数の相関分析

仮説:
  H1: 悪天候（大雪・低温）は短期的に来局を減少させる
  H2: しかし定期薬は尽きるので、悪天候後2-3日でリバウンド来局増
  H3: 結果として「悪天候の翌週の処方枚数」は正の相関を持つ
  H4: オンライン処方普及で天候依存性は低下傾向

分析内容:
  1. 基礎統計（天候変数と処方枚数の分布）
  2. 同時相関（天候 × 当日処方）
  3. ラグ相関（天候 → N日後の処方、N=1..14）
  4. 累積悪天候効果（3日連続悪天候 → その後の処方急増）
  5. 季節別パターン分解

Usage:
    cd backend
    python -m analysis.eda_weather_prescription
"""

import os
import re
import sys
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import django

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import numpy as np
import pandas as pd
from scipy import stats

from apps.analytics.models import (
    AREA_STATION_MAP,
    InfluenzaReport,
    PrescriptionRecord,
    WeatherRecord,
)
from apps.stores.models import Store


# ---------------------------------------------------------------------------
# 1. Fetch JMA weather data (if not enough in DB)
# ---------------------------------------------------------------------------

def fetch_jma_weather(station_name: str, prec_no: str, block_no: str,
                      year: int, month: int) -> list[dict]:
    """Fetch daily weather data from JMA for one station/month."""
    import requests

    url = (
        f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php"
        f"?prec_no={prec_no}&block_no={block_no}"
        f"&year={year}&month={month}"
    )
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; pharma-shift-eda/1.0)"},
            timeout=30,
        )
        if resp.status_code != 200:
            return []
    except Exception:
        return []

    html = resp.text
    td_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
    records = []

    for row_html in html.split("<tr"):
        tds = td_pattern.findall(row_html)
        cleaned = [re.sub(r"<[^>]+>", "", td).strip() for td in tds]
        if len(cleaned) < 10:
            continue

        try:
            day = int(cleaned[0])
            if day < 1 or day > 31:
                continue
        except ValueError:
            continue

        try:
            record_date = date(year, month, day)
        except ValueError:
            continue

        def parse_val(s):
            s = s.strip().rstrip(")]*#×").replace("--", "").replace("///", "").replace("×", "")
            if not s or s == "…":
                return None
            try:
                return float(s)
            except ValueError:
                return None

        # JMA columns for s1 (気象台) stations:
        # 0:day, 1:local_pressure, 2:sea_pressure,
        # 3:precip_total, 4:precip_max_1h, 5:precip_max_10m,
        # 6:avg_temp, 7:max_temp, 8:min_temp,
        # 9:avg_humidity, 10:min_humidity,
        # 11:avg_wind, 12:max_wind_speed, 13:max_wind_dir,
        # 14:max_gust_speed, 15:max_gust_dir,
        # 16:sunshine, 17:snowfall(合計), 18:snow_depth(最深積雪)
        # (some stations may have fewer columns)
        records.append({
            "station_name": station_name,
            "station_code": block_no,
            "date": record_date,
            "avg_temperature": parse_val(cleaned[6]) if len(cleaned) > 6 else None,
            "max_temperature": parse_val(cleaned[7]) if len(cleaned) > 7 else None,
            "min_temperature": parse_val(cleaned[8]) if len(cleaned) > 8 else None,
            "precipitation": parse_val(cleaned[3]) if len(cleaned) > 3 else None,
            "humidity": parse_val(cleaned[9]) if len(cleaned) > 9 else None,
            "snowfall": parse_val(cleaned[17]) if len(cleaned) > 17 else None,
            "snow_depth": parse_val(cleaned[18]) if len(cleaned) > 18 else None,
        })

    return records


def ensure_weather_data(station_name: str, prec_no: str, block_no: str,
                        start_date: date, end_date: date):
    """Ensure weather data exists in DB for the given period."""
    existing = WeatherRecord.objects.filter(
        station_name=station_name,
        date__gte=start_date,
        date__lte=end_date,
    ).count()

    expected_days = (end_date - start_date).days + 1
    if existing >= expected_days * 0.8:
        print(f"  {station_name}: {existing}/{expected_days} days already in DB, skipping")
        return

    print(f"  {station_name}: fetching {start_date} to {end_date}...")

    current = start_date.replace(day=1)
    total_created = 0
    while current <= end_date:
        records = fetch_jma_weather(station_name, prec_no, block_no,
                                     current.year, current.month)
        for rec in records:
            if rec["date"] < start_date or rec["date"] > end_date:
                continue
            if rec["avg_temperature"] is None:
                continue
            _, created = WeatherRecord.objects.update_or_create(
                station_name=rec["station_name"],
                date=rec["date"],
                defaults={
                    "station_code": rec["station_code"],
                    "avg_temperature": rec["avg_temperature"],
                    "max_temperature": rec["max_temperature"],
                    "min_temperature": rec["min_temperature"],
                    "precipitation": rec["precipitation"],
                    "humidity": rec["humidity"],
                    "snowfall": rec["snowfall"],
                    "snow_depth": rec["snow_depth"],
                },
            )
            if created:
                total_created += 1

        # Next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
        time.sleep(2)  # Be polite to JMA

    print(f"    → {total_created} records created")


# ---------------------------------------------------------------------------
# 2. Load data into pandas DataFrames
# ---------------------------------------------------------------------------

def load_prescription_data() -> pd.DataFrame:
    """Load all prescription records into a DataFrame."""
    qs = PrescriptionRecord.objects.select_related("store").values(
        "store__name", "store__area", "date", "count"
    )
    df = pd.DataFrame(list(qs))
    if df.empty:
        return df
    df.rename(columns={
        "store__name": "store_name",
        "store__area": "area",
        "date": "date",
        "count": "prescriptions",
    }, inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_weather_data() -> pd.DataFrame:
    """Load all weather records into a DataFrame."""
    qs = WeatherRecord.objects.values(
        "station_name", "date",
        "avg_temperature", "max_temperature", "min_temperature",
        "precipitation", "humidity", "snowfall", "snow_depth",
    )
    df = pd.DataFrame(list(qs))
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    # Convert Decimal to float
    for col in ["avg_temperature", "max_temperature", "min_temperature",
                "precipitation", "humidity", "snowfall", "snow_depth"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_influenza_data() -> pd.DataFrame:
    """Load IDWR influenza reports."""
    qs = InfluenzaReport.objects.filter(
        disease="インフルエンザ", prefecture="北海道"
    ).values("year", "week", "patients", "total_reports")
    df = pd.DataFrame(list(qs))
    if df.empty:
        return df
    # Convert week to date (Monday of that week)
    df["date"] = df.apply(
        lambda r: pd.Timestamp(date.fromisocalendar(int(r["year"]), max(int(r["week"]), 1), 1)),
        axis=1,
    )
    df["patients"] = pd.to_numeric(df["patients"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# 3. Analysis functions
# ---------------------------------------------------------------------------

def analyze_basic_stats(rx_df: pd.DataFrame, weather_df: pd.DataFrame):
    """Basic descriptive statistics."""
    print("\n" + "=" * 70)
    print("1. 基礎統計量")
    print("=" * 70)

    # Prescription stats by area
    area_stats = rx_df.groupby("area")["prescriptions"].agg(["mean", "std", "min", "max", "count"])
    print("\n■ エリア別 日次処方枚数:")
    print(area_stats.to_string())

    # Weather stats by station
    if not weather_df.empty:
        print("\n■ 気象データ (全観測所):")
        weather_cols = ["avg_temperature", "precipitation", "humidity", "snowfall", "snow_depth"]
        existing_cols = [c for c in weather_cols if c in weather_df.columns]
        print(weather_df[existing_cols].describe().to_string())

    # Day-of-week pattern
    rx_df["dow"] = rx_df["date"].dt.dayofweek
    dow_names = ["月", "火", "水", "木", "金", "土", "日"]
    dow_stats = rx_df.groupby("dow")["prescriptions"].mean()
    print("\n■ 曜日別 平均処方枚数:")
    for dow_idx, avg in dow_stats.items():
        bar = "█" * int(avg / 2)
        print(f"  {dow_names[int(dow_idx)]}: {avg:6.1f} {bar}")

    # Monthly pattern
    rx_df["month"] = rx_df["date"].dt.month
    month_stats = rx_df.groupby("month")["prescriptions"].mean()
    print("\n■ 月別 平均処方枚数:")
    for month, avg in month_stats.items():
        bar = "█" * int(avg / 2)
        print(f"  {int(month):2d}月: {avg:6.1f} {bar}")


def analyze_same_day_correlation(merged_df: pd.DataFrame):
    """Same-day correlation between weather and prescriptions."""
    print("\n" + "=" * 70)
    print("2. 同時相関分析 (当日の天候 × 当日の処方枚数)")
    print("=" * 70)

    weather_vars = [
        ("avg_temperature", "平均気温"),
        ("max_temperature", "最高気温"),
        ("min_temperature", "最低気温"),
        ("precipitation", "降水量"),
        ("humidity", "湿度"),
        ("snowfall", "降雪量"),
        ("snow_depth", "積雪深"),
    ]

    for col, label in weather_vars:
        if col not in merged_df.columns:
            continue
        valid = merged_df.dropna(subset=[col, "prescriptions"])
        if len(valid) < 10:
            continue
        r, p = stats.pearsonr(valid[col], valid["prescriptions"])
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        bar_r = "+" * int(abs(r) * 50) if r > 0 else "-" * int(abs(r) * 50)
        print(f"  {label:8s}: r={r:+.4f} (p={p:.4f}) {sig} {bar_r}")


def analyze_lag_correlation(merged_df: pd.DataFrame, max_lag: int = 14):
    """Cross-correlation with time lags.

    Key question: Does bad weather on day T predict prescription changes on day T+N?
    """
    print("\n" + "=" * 70)
    print("3. ラグ相関分析 (天候 → N日後の処方枚数)")
    print("=" * 70)
    print("  仮説: 悪天候(降雪・低温) → 短期減少 → 数日後にリバウンド増加")

    weather_vars = [
        ("avg_temperature", "平均気温"),
        ("precipitation", "降水量"),
        ("snowfall", "降雪量"),
        ("snow_depth", "積雪深"),
    ]

    for col, label in weather_vars:
        if col not in merged_df.columns:
            continue
        valid = merged_df.dropna(subset=[col]).copy()
        if len(valid) < 30:
            continue

        print(f"\n  ■ {label} → 処方枚数 (ラグ0-{max_lag}日):")
        best_r = 0
        best_lag = 0
        for lag in range(0, max_lag + 1):
            valid[f"rx_lag{lag}"] = valid["prescriptions"].shift(-lag)
            lag_valid = valid.dropna(subset=[col, f"rx_lag{lag}"])
            if len(lag_valid) < 20:
                continue
            r, p = stats.pearsonr(lag_valid[col], lag_valid[f"rx_lag{lag}"])
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else " "
            bar = "█" * int(abs(r) * 80)
            direction = "+" if r > 0 else "-"
            print(f"    lag={lag:2d}日: r={r:+.4f} {sig} {direction}{bar}")
            if abs(r) > abs(best_r):
                best_r = r
                best_lag = lag
            valid.drop(columns=[f"rx_lag{lag}"], inplace=True)

        if best_r != 0:
            print(f"    → 最強相関: lag={best_lag}日 (r={best_r:+.4f})")


def analyze_consecutive_bad_weather(merged_df: pd.DataFrame):
    """Analyze the rebound effect after consecutive bad weather days."""
    print("\n" + "=" * 70)
    print("4. 連続悪天候後のリバウンド分析")
    print("=" * 70)
    print("  仮説: 定期薬は尽きるので、悪天候後に来局が集中する")

    if "snowfall" not in merged_df.columns or merged_df["snowfall"].isna().all():
        if "precipitation" not in merged_df.columns:
            print("  ※ 降雪・降水データなし、スキップ")
            return
        # Use precipitation as fallback for non-snow season
        weather_col = "precipitation"
        threshold = merged_df[weather_col].quantile(0.75)
        label = "強降水"
    else:
        weather_col = "snowfall"
        # Define "bad weather" as snowfall > 0
        threshold = 0
        label = "降雪"

    merged_sorted = merged_df.sort_values("date").copy()

    # Mark bad weather days
    merged_sorted["bad_weather"] = merged_sorted[weather_col].fillna(0) > threshold

    # Count consecutive bad weather days (rolling sum)
    for window in [2, 3, 5]:
        col_name = f"bad_{window}d"
        merged_sorted[col_name] = (
            merged_sorted["bad_weather"]
            .rolling(window=window, min_periods=window)
            .sum()
        )

    # After N consecutive bad weather days, what happens to prescriptions?
    for window in [2, 3, 5]:
        col_name = f"bad_{window}d"
        # Find episodes where all N days were bad weather
        bad_episodes = merged_sorted[merged_sorted[col_name] >= window].index
        if len(bad_episodes) < 3:
            continue

        print(f"\n  ■ {window}日連続{label}後の処方枚数変化:")

        # Look at prescriptions in the days FOLLOWING the bad weather
        for after_days in [1, 2, 3, 5, 7]:
            changes = []
            for idx in bad_episodes:
                loc = merged_sorted.index.get_loc(idx)
                if loc + after_days < len(merged_sorted) and loc >= window:
                    rx_during = merged_sorted.iloc[loc - window + 1:loc + 1]["prescriptions"].mean()
                    rx_after = merged_sorted.iloc[loc + 1:loc + 1 + after_days]["prescriptions"].mean()
                    if not np.isnan(rx_during) and not np.isnan(rx_after):
                        changes.append((rx_after - rx_during) / rx_during * 100)

            if changes:
                mean_change = np.mean(changes)
                std_change = np.std(changes)
                n = len(changes)
                t_stat, p_val = stats.ttest_1samp(changes, 0) if n > 2 else (0, 1)
                sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
                direction = "↑" if mean_change > 0 else "↓"
                print(
                    f"    {after_days}日後: {direction}{abs(mean_change):+.1f}% "
                    f"(±{std_change:.1f}%, n={n}) {sig}"
                )


def analyze_seasonal_weather_interaction(merged_df: pd.DataFrame):
    """Analyze how weather effects differ by season."""
    print("\n" + "=" * 70)
    print("5. 季節別 天候×処方 交互作用")
    print("=" * 70)
    print("  仮説: 冬季(インフルシーズン)は天候の影響がより強い")

    merged_df = merged_df.copy()
    merged_df["month"] = merged_df["date"].dt.month

    # Define seasons
    def get_season(m):
        if m in [12, 1, 2]:
            return "冬(12-2月)"
        elif m in [3, 4, 5]:
            return "春(3-5月)"
        elif m in [6, 7, 8]:
            return "夏(6-8月)"
        else:
            return "秋(9-11月)"

    merged_df["season"] = merged_df["month"].apply(get_season)

    weather_vars = [
        ("avg_temperature", "平均気温"),
        ("precipitation", "降水量"),
    ]

    for col, label in weather_vars:
        if col not in merged_df.columns:
            continue

        print(f"\n  ■ {label} × 処方枚数 (季節別相関):")
        for season in ["冬(12-2月)", "春(3-5月)", "夏(6-8月)", "秋(9-11月)"]:
            subset = merged_df[merged_df["season"] == season].dropna(subset=[col, "prescriptions"])
            if len(subset) < 10:
                print(f"    {season}: データ不足")
                continue
            r, p = stats.pearsonr(subset[col], subset["prescriptions"])
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            n = len(subset)
            print(f"    {season}: r={r:+.4f} (p={p:.4f}, n={n}) {sig}")


def analyze_influenza_prescription_correlation(rx_df: pd.DataFrame, flu_df: pd.DataFrame):
    """Analyze correlation between influenza reports and prescriptions."""
    print("\n" + "=" * 70)
    print("6. インフルエンザ定点報告 × 処方枚数 相関")
    print("=" * 70)

    if flu_df.empty:
        print("  ※ インフルエンザデータなし")
        return

    # Aggregate prescriptions to weekly
    rx_weekly = rx_df.copy()
    rx_weekly["iso_year"] = rx_weekly["date"].dt.isocalendar().year.astype(int)
    rx_weekly["iso_week"] = rx_weekly["date"].dt.isocalendar().week.astype(int)
    rx_weekly_agg = rx_weekly.groupby(["iso_year", "iso_week"])["prescriptions"].mean().reset_index()
    rx_weekly_agg.rename(columns={"iso_year": "year", "iso_week": "week"}, inplace=True)

    # Merge with flu data
    merged = pd.merge(
        rx_weekly_agg, flu_df[["year", "week", "patients"]],
        on=["year", "week"], how="inner",
    )

    if len(merged) < 5:
        print(f"  ※ 結合データ不足 ({len(merged)}行)")
        return

    print(f"  データ: {len(merged)} 週")

    # Same-week correlation
    r, p = stats.pearsonr(merged["patients"], merged["prescriptions"])
    print(f"\n  ■ 同週相関: r={r:+.4f} (p={p:.4f})")

    # Lag analysis (flu leads prescriptions by N weeks)
    print("\n  ■ ラグ相関 (インフル → N週後の処方):")
    for lag in range(0, 5):
        merged[f"rx_lag{lag}"] = merged["prescriptions"].shift(-lag)
        valid = merged.dropna(subset=["patients", f"rx_lag{lag}"])
        if len(valid) < 5:
            continue
        r, p = stats.pearsonr(valid["patients"], valid[f"rx_lag{lag}"])
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        print(f"    lag={lag}週: r={r:+.4f} (p={p:.4f}) {sig}")

    # Show flu trend
    print("\n  ■ インフルエンザ定点報告数の推移:")
    for _, row in merged.sort_values(["year", "week"]).iterrows():
        flu_val = float(row["patients"]) if pd.notna(row["patients"]) else 0
        bar = "█" * int(flu_val)
        print(f"    {int(row['year'])}W{int(row['week']):02d}: {flu_val:6.2f} {bar}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("EDA: 気象データ × 処方枚数 相関分析")
    print("=" * 70)

    # Step 1: Ensure weather data
    print("\n[Step 1] 気象データ取得...")
    # Determine date range from prescription data
    rx_range = PrescriptionRecord.objects.aggregate(
        min_date=django.db.models.Min("date"),
        max_date=django.db.models.Max("date"),
    )
    if not rx_range["min_date"]:
        print("ERROR: 処方データがありません。先に seed_prescription_data を実行してください。")
        return

    start = rx_range["min_date"]
    end = rx_range["max_date"]
    print(f"  処方データ期間: {start} to {end}")

    # Fetch weather for main station (旭川) for the full period
    primary_station = "旭川"
    station_info = AREA_STATION_MAP.get("旭川", ("旭川", "12", "47407"))
    ensure_weather_data(station_info[0], station_info[1], station_info[2], start, end)

    # Step 2: Load all data
    print("\n[Step 2] データ読み込み...")
    rx_df = load_prescription_data()
    weather_df = load_weather_data()
    flu_df = load_influenza_data()
    print(f"  処方: {len(rx_df)} rows, 天候: {len(weather_df)} rows, インフル: {len(flu_df)} rows")

    if rx_df.empty:
        print("ERROR: データが空です")
        return

    # Step 3: Merge prescription and weather data
    # For simplicity, use only 旭川 area stores with 旭川 weather
    asahikawa_stores = rx_df[rx_df["area"] == "旭川"].copy()
    asahikawa_weather = weather_df[weather_df["station_name"] == primary_station].copy()

    # Aggregate prescriptions by date (sum across all 旭川 stores)
    rx_daily = asahikawa_stores.groupby("date")["prescriptions"].agg(["sum", "mean", "count"]).reset_index()
    rx_daily.rename(columns={"sum": "total_rx", "mean": "prescriptions", "count": "store_count"}, inplace=True)

    if asahikawa_weather.empty:
        print("\n※ 旭川の気象データが取得できませんでした。全エリアの処方データで分析します。")
        # Fall back to overall analysis without weather
        analyze_basic_stats(rx_df, weather_df)
        analyze_influenza_prescription_correlation(rx_df, flu_df)
        return

    # Merge on date
    merged = pd.merge(rx_daily, asahikawa_weather, on="date", how="inner")
    print(f"  結合データ: {len(merged)} rows (旭川エリア × 旭川気象台)")

    # Step 4: Run all analyses
    analyze_basic_stats(rx_df, weather_df)
    analyze_same_day_correlation(merged)
    analyze_lag_correlation(merged)
    analyze_consecutive_bad_weather(merged)
    analyze_seasonal_weather_interaction(merged)
    analyze_influenza_prescription_correlation(rx_df, flu_df)

    # Summary
    print("\n" + "=" * 70)
    print("分析サマリー")
    print("=" * 70)
    print("""
  ※ 注意: 現在の処方データはシミュレーション生成データです。
  　 実際のMusubiデータで再実行すると、真の相関が見えます。

  次のステップ:
    1. Musubiから実データを取得 (CSV upload or scraping)
    2. 本分析を再実行して真の天候効果を検証
    3. 有意なラグが見つかれば、LightGBM特徴量に追加
    4. オンライン処方率も変数に加えて天候依存性の変化を追跡
    """)


if __name__ == "__main__":
    main()
