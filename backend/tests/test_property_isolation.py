import asyncio
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/propertyflow")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("SECRET_KEY", "debug_challenge_secret")


class PropertyIsolationTests(unittest.TestCase):
    def test_each_tenant_sees_only_its_properties(self):
        async def run():
            from app.core.database_pool import db_pool
            from app.services.reservations import list_tenant_properties

            sunset = await list_tenant_properties("tenant-a")
            ocean = await list_tenant_properties("tenant-b")
            await db_pool.close()
            return sunset, ocean

        sunset, ocean = asyncio.run(run())

        sunset_by_id = {row["id"]: row["name"] for row in sunset}
        ocean_by_id = {row["id"]: row["name"] for row in ocean}

        self.assertEqual(set(sunset_by_id), {"prop-001", "prop-002", "prop-003"})
        self.assertEqual(sunset_by_id["prop-001"], "Beach House Alpha")
        self.assertEqual(set(ocean_by_id), {"prop-001", "prop-004", "prop-005"})
        self.assertEqual(ocean_by_id["prop-001"], "Mountain Lodge Beta")

    def test_summary_rejects_another_tenants_property(self):
        async def run():
            from fastapi import HTTPException

            from app.api.v1 import dashboard as dashboard_api
            from app.core.database_pool import db_pool

            try:
                await dashboard_api.get_dashboard_summary(
                    "prop-002",
                    3,
                    2024,
                    SimpleNamespace(tenant_id="tenant-b"),
                )
                self.fail("expected 404")
            except HTTPException as exc:
                status_code = exc.status_code
            await db_pool.close()
            return status_code

        self.assertEqual(asyncio.run(run()), 404)
