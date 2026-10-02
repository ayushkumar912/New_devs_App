import asyncio
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/propertyflow")
os.environ.setdefault("SECRET_KEY", "debug_challenge_secret")


class TenantRequiredTests(unittest.TestCase):
    def test_unknown_users_are_not_assigned_sunset(self):
        from jose import jwt

        from app.core.tenant_resolver import TenantResolver

        unknown = asyncio.run(TenantResolver.resolve_tenant_id("user-x", "nobody@example.com"))
        sunset = asyncio.run(TenantResolver.resolve_tenant_id("user-sunset", "sunset@propertyflow.com"))
        ocean = asyncio.run(TenantResolver.resolve_tenant_id("user-ocean", "ocean@propertyflow.com"))

        token = jwt.encode(
            {"email": "nobody@example.com", "app_metadata": {"tenant_id": "tenant-b"}},
            os.environ["SECRET_KEY"],
            algorithm="HS256",
        )
        from_token = asyncio.run(
            TenantResolver.resolve_tenant_id("user-x", "nobody@example.com", token=token)
        )

        self.assertIsNone(unknown)
        self.assertEqual(sunset, "tenant-a")
        self.assertEqual(ocean, "tenant-b")
        self.assertEqual(from_token, "tenant-b")

    def test_dashboard_rejects_a_user_with_no_tenant(self):
        async def run():
            from fastapi import HTTPException

            from app.api.v1 import dashboard as dashboard_api

            with self.assertRaises(HTTPException) as caught:
                await dashboard_api.get_dashboard_summary(
                    "prop-001",
                    3,
                    2024,
                    SimpleNamespace(tenant_id=None),
                )
            return caught.exception.status_code

        self.assertEqual(asyncio.run(run()), 403)
