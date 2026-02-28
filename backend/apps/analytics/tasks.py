"""Celery tasks for analytics: Musubi scraping and forecast generation."""

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
