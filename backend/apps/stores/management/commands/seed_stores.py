"""Seed the 62 managed pharmacy stores for Hokkaido area."""

from django.core.management.base import BaseCommand

from apps.stores.models import Store

# (name, area, slots, base_difficulty)
STORES = [
    ("旭川大町店", "旭川", 1, "3.0"),
    ("東光５条店", "旭川", 1, "3.0"),
    ("神居３条店", "旭川", 2, "3.0"),
    ("A3神居店", "旭川", 1, "3.0"),
    ("永山３条店", "旭川", 1, "3.0"),
    ("豊岡１２条店", "旭川", 2, "3.0"),
    ("東光１０条店", "旭川", 1, "3.0"),
    ("永山７条店", "旭川", 1, "3.0"),
    ("錦町店", "旭川", 3, "3.5"),
    ("旭川近文店", "旭川", 1, "3.0"),
    ("旭川大町３条店", "旭川", 2, "3.0"),
    ("忠和店", "旭川", 1, "3.0"),
    ("旭川末広北店", "旭川", 1, "3.0"),
    ("永山３条西店", "旭川", 1, "3.0"),
    ("永山環状通店", "旭川", 1, "3.0"),
    ("旭川豊岡５条店", "旭川", 1, "3.0"),
    ("旭川神居東店", "旭川", 1, "3.0"),
    ("旭川末広５条店", "旭川", 1, "3.0"),
    ("神居十字街店", "旭川", 1, "3.0"),
    ("旭川日赤前店", "旭川", 1, "3.0"),
    ("１条店", "旭川", 1, "3.0"),
    ("旭川６条店", "旭川", 1, "3.0"),
    ("旭川緑が丘店", "旭川", 2, "3.0"),
    ("旭川駅前店", "旭川", 3, "3.5"),
    ("旭川４条店", "旭川", 1, "3.0"),
    ("旭川４条西店", "旭川", 1, "3.0"),
    ("旭川中央店", "旭川", 1, "3.0"),
    ("旭川神楽店", "旭川", 1, "3.0"),
    ("旭川７条店", "旭川", 1, "3.0"),
    ("名寄西５条店", "名寄", 1, "3.5"),
    ("名寄西４条店", "名寄", 3, "3.5"),
    ("南稚内店", "稚内", 1, "4.0"),
    ("稚内新光店", "稚内", 1, "4.0"),
    ("稚内栄店", "稚内", 1, "4.0"),
    ("稚内潮見店", "稚内", 1, "4.0"),
    ("羽幌店", "留萌", 1, "4.0"),
    ("留萌店", "留萌", 1, "4.0"),
    ("美幌店", "北見・網走", 1, "3.5"),
    ("網走北店", "北見・網走", 1, "3.5"),
    ("紋別緑町店", "紋別", 1, "4.0"),
    ("広域紋別病院前店", "紋別", 1, "4.0"),
    ("北見メッセ店", "北見・網走", 1, "3.5"),
    ("北見三輪北店", "北見・網走", 1, "3.5"),
    ("北見公園店", "北見・網走", 1, "3.5"),
    ("富良野店", "富良野", 1, "3.5"),
    ("富良野弥生店", "富良野", 1, "3.5"),
    ("富良野緑町店", "富良野", 1, "3.5"),
    ("砂川店", "滝川・砂川", 1, "3.0"),
    ("滝川朝日町店", "滝川・砂川", 1, "3.0"),
    ("赤平店", "滝川・砂川", 1, "3.0"),
    ("帯広北店", "帯広", 1, "3.0"),
    ("釧路豊川店", "釧路", 1, "3.5"),
    ("新橋大通店", "帯広", 1, "3.0"),
    ("帯広西８条店", "帯広", 1, "3.0"),
    ("音更店", "帯広", 1, "3.0"),
    ("釧路若松店", "釧路", 1, "3.5"),
    ("釧路富士見店", "釧路", 1, "3.5"),
    ("帯広大通南２４丁目店", "帯広", 1, "3.0"),
    ("帯広西２１丁目店", "帯広", 1, "3.0"),
    ("帯広南の森店", "帯広", 1, "3.0"),
    ("中標津東店", "中標津", 1, "4.0"),
    ("中標津病院前店", "中標津", 1, "4.0"),
]


class Command(BaseCommand):
    help = "Seed the 62 managed pharmacy stores for Hokkaido area"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing stores before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = Store.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} existing stores")

        created = 0
        skipped = 0

        for name, area, slots, difficulty in STORES:
            _, was_created = Store.objects.get_or_create(
                name=name,
                defaults={
                    "area": area,
                    "slots": slots,
                    "base_difficulty": difficulty,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created} stores ({skipped} already existed). "
                f"Total: {Store.objects.count()}"
            )
        )
