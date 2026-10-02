import asyncio
import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/propertyflow")
os.environ.setdefault("SECRET_KEY", "debug_challenge_secret")

from decimal import Decimal


class MonthlyTimezoneTests(unittest.TestCase):
    def test_paris_check_in_just_after_midnight_counts_as_march(self):
        async def run():
            from app.services.reservations import calculate_monthly_revenue

            from app.core.database_pool import db_pool

            march = await calculate_monthly_revenue("prop-001", "tenant-a", 3, 2024)
            february = await calculate_monthly_revenue("prop-001", "tenant-a", 2, 2024)
            await db_pool.close()
            return march, february

        march, february = asyncio.run(run())

        # res-tz-1 is 2024-02-29 23:30 UTC, which is 2024-03-01 00:30 in Europe/Paris.
        self.assertEqual(Decimal(march["total"]), Decimal("2250.000"))
        self.assertEqual(march["count"], 4)
        self.assertEqual(Decimal(february["total"]), Decimal("0"))
        self.assertEqual(february["count"], 0)
