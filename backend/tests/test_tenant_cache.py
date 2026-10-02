import asyncio
import os
import unittest

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5433/propertyflow"
os.environ["REDIS_URL"] = "redis://localhost:6380/0"
os.environ["SECRET_KEY"] = "debug_challenge_secret"

from decimal import Decimal


class TenantCacheTests(unittest.TestCase):
    def test_shared_property_id_does_not_cross_tenants(self):
        async def run():
            from app.services.cache import get_revenue_summary, redis_client

            await redis_client.flushdb()
            # Poison the old unscoped key. A tenant-safe lookup must ignore it.
            await redis_client.set(
                "revenue:prop-001",
                '{"property_id":"prop-001","tenant_id":"tenant-a","total":"1000.00","currency":"USD","count":3}',
            )

            from app.core.database_pool import db_pool

            sunset = await get_revenue_summary("prop-001", "tenant-a", 3, 2024)
            ocean = await get_revenue_summary("prop-001", "tenant-b", 3, 2024)
            sunset_again = await get_revenue_summary("prop-001", "tenant-a", 3, 2024)
            await db_pool.close()
            await redis_client.aclose()
            return sunset, ocean, sunset_again

        sunset, ocean, sunset_again = asyncio.run(run())

        self.assertEqual(Decimal(sunset["total"]), Decimal("2250.000"))
        self.assertEqual(sunset["tenant_id"], "tenant-a")
        self.assertEqual(Decimal(ocean["total"]), Decimal("0.00"))
        self.assertEqual(ocean["tenant_id"], "tenant-b")
        self.assertEqual(ocean["count"], 0)
        self.assertEqual(sunset_again["tenant_id"], "tenant-a")
        self.assertEqual(Decimal(sunset_again["total"]), Decimal("2250.000"))
