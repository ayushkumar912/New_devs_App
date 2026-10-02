import asyncio
import os
import unittest

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5433/propertyflow"
os.environ["SECRET_KEY"] = "debug_challenge_secret"

from decimal import Decimal


class DatabasePoolTests(unittest.TestCase):
    def test_rewrites_libpq_url_for_asyncpg(self):
        from app.core.database_pool import to_async_database_url

        self.assertEqual(
            to_async_database_url("postgresql://postgres:postgres@db:5432/propertyflow"),
            "postgresql+asyncpg://postgres:postgres@db:5432/propertyflow",
        )
        self.assertEqual(
            to_async_database_url("postgres://postgres:postgres@db:5432/propertyflow"),
            "postgresql+asyncpg://postgres:postgres@db:5432/propertyflow",
        )
        self.assertEqual(
            to_async_database_url("postgresql+asyncpg://u:p@h/db"),
            "postgresql+asyncpg://u:p@h/db",
        )

    def test_revenue_query_reads_seeded_rows(self):
        from app.services.reservations import calculate_total_revenue

        result = asyncio.run(calculate_total_revenue("prop-001", "tenant-a"))

        self.assertEqual(Decimal(result["total"]), Decimal("2250.000"))
        self.assertEqual(result["count"], 4)
        self.assertEqual(result["tenant_id"], "tenant-a")
