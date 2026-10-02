import asyncio
import os
import unittest
from decimal import Decimal
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/propertyflow")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("SECRET_KEY", "debug_challenge_secret")


class MoneyPrecisionTests(unittest.TestCase):
    def test_half_up_rounding_does_not_use_binary_floats(self):
        from app.services.reservations import to_money

        self.assertEqual(to_money("333.335"), "333.34")
        self.assertEqual(to_money(Decimal("1000.000")), "1000.00")
        self.assertEqual(to_money("1776.500"), "1776.50")

    def test_dashboard_returns_cent_string_for_subcent_bookings(self):
        async def run():
            from app.api.v1 import dashboard as dashboard_api
            from app.core.database_pool import db_pool
            from app.services.cache import redis_client

            await redis_client.flushdb()
            sunset = await dashboard_api.get_dashboard_summary(
                "prop-001", 3, 2024, SimpleNamespace(tenant_id="tenant-a")
            )
            ocean = await dashboard_api.get_dashboard_summary(
                "prop-004", 3, 2024, SimpleNamespace(tenant_id="tenant-b")
            )
            await db_pool.close()
            await redis_client.aclose()
            return sunset, ocean

        sunset, ocean = asyncio.run(run())

        self.assertIsInstance(sunset["total_revenue"], str)
        self.assertEqual(sunset["total_revenue"], "2250.00")
        self.assertEqual(ocean["total_revenue"], "1776.50")
        self.assertEqual(ocean["reservations_count"], 4)
