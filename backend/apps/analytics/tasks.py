"""Celery tasks for analytics: Musubi scraping, forecast generation, and external data fetch."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def scrape_musubi_prescriptions():
    """前日の処方実績を Musubi Insight からスクレイピング"""
    from .services import MusubiScraper

    yesterday = timezone.now().date() - timedelta(days=1)
    scraper = MusubiScraper()
    result = scraper.scrape_all_stores(yesterday)

    logger.info("Musubi scraping task result: %s", result)
    return result


@shared_task
def generate_prescription_forecasts():
    """翌2週間の処方予測を生成（LightGBM or 統計フォールバック）"""
    from .services import generate_forecasts_lightgbm

    today = timezone.now().date()
    target_start = today + timedelta(days=1)
    target_end = today + timedelta(days=14)

    result = generate_forecasts_lightgbm(target_start, target_end)
    logger.info("Forecast generation task result: %s", result)
    return result


@shared_task
def fetch_idwr_weekly():
    """IDWR定点報告データを週次取得（前週分）"""
    from django.core.management import call_command

    call_command("fetch_idwr")
    logger.info("IDWR weekly fetch complete")


@shared_task
def fetch_weather_daily():
    """気象データを日次取得（前日分）"""
    import time

    import requests

    from .models import AREA_STATION_MAP, WeatherRecord

    yesterday = timezone.now().date() - timedelta(days=1)
    created = 0
    errors = 0

    # Fetch for unique stations only
    seen_stations = set()
    for area, (station_name, prec_no, block_no) in AREA_STATION_MAP.items():
        if station_name in seen_stations:
            continue
        seen_stations.add(station_name)

        try:
            url = (
                f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php"
                f"?prec_no={prec_no}&block_no={block_no}"
                f"&year={yesterday.year}&month={yesterday.month}"
            )
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; pharma-shift/1.0)"},
                timeout=30,
            )
            if resp.status_code == 200:
                logger.info("Fetched weather for %s", station_name)
                created += 1
            time.sleep(3)  # Be polite to JMA servers
        except requests.RequestException as e:
            logger.warning("Weather fetch failed for %s: %s", station_name, e)
            errors += 1

    logger.info("Weather daily fetch: %d stations processed, %d errors", created, errors)
