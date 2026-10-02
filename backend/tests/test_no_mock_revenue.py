import asyncio
import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/propertyflow")
os.environ.setdefault("SECRET_KEY", "debug_challenge_secret")


class NoMockRevenueTests(unittest.TestCase):
    def test_database_failure_does_not_invent_revenue(self):
        async def run():
            from app.config import settings
            from app.core.database_pool import db_pool
            from app.services.reservations import RevenueUnavailable, calculate_total_revenue

            original = settings.database_url
            settings.database_url = "postgresql://postgres:postgres@127.0.0.1:1/propertyflow"
            await db_pool.close()
            try:
                await db_pool.initialize()
                with self.assertRaises(RevenueUnavailable):
                    await calculate_total_revenue("prop-001", "tenant-a")
            finally:
                settings.database_url = original
                await db_pool.close()

        asyncio.run(run())

    def test_summary_reports_unavailable_instead_of_mock_totals(self):
        async def run():
            from types import SimpleNamespace

            from fastapi import HTTPException

            from app.api.v1 import dashboard as dashboard_api
            from app.services.reservations import RevenueUnavailable

            async def unavailable(property_id, tenant_id):
                raise RevenueUnavailable("down")

            original = dashboard_api.get_revenue_summary
            dashboard_api.get_revenue_summary = unavailable
            try:
                with self.assertRaises(HTTPException) as caught:
                    await dashboard_api.get_dashboard_summary(
                        "prop-001",
                        SimpleNamespace(tenant_id="tenant-a"),
                    )
                self.assertEqual(caught.exception.status_code, 503)
            finally:
                dashboard_api.get_revenue_summary = original

        asyncio.run(run())
