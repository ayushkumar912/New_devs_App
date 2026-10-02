from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List


def to_money(amount) -> str:
    """Round a numeric amount to cents, half away from zero, and keep it a string."""
    value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


class RevenueUnavailable(Exception):
    """Raised when revenue cannot be read from the database."""

async def _db_pool():
    from app.core.database_pool import db_pool

    if not db_pool.session_factory:
        await db_pool.initialize()
    if not db_pool.session_factory:
        raise RevenueUnavailable("Database pool not available")
    return db_pool


async def list_tenant_properties(tenant_id: str) -> List[Dict[str, Any]]:
    """Return only the properties owned by this tenant."""
    from sqlalchemy import text

    pool = await _db_pool()
    query = text("""
        SELECT id, name, timezone
        FROM properties
        WHERE tenant_id = :tenant_id
        ORDER BY name
    """)
    async with pool.get_session() as session:
        result = await session.execute(query, {"tenant_id": tenant_id})
        return [
            {"id": row.id, "name": row.name, "timezone": row.timezone}
            for row in result.fetchall()
        ]


async def get_tenant_property(property_id: str, tenant_id: str):
    """Return the property when it belongs to the tenant, otherwise None."""
    from sqlalchemy import text

    pool = await _db_pool()
    query = text("""
        SELECT id, name, timezone
        FROM properties
        WHERE id = :property_id AND tenant_id = :tenant_id
    """)
    async with pool.get_session() as session:
        result = await session.execute(query, {
            "property_id": property_id,
            "tenant_id": tenant_id,
        })
        row = result.fetchone()
    if row is None:
        return None
    return {"id": row.id, "name": row.name, "timezone": row.timezone}


async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Dict[str, Any]:
    """Sum check-ins whose local property date falls in the requested month."""
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")

    try:
        from app.core.database_pool import db_pool

        if not db_pool.session_factory:
            await db_pool.initialize()
        if not db_pool.session_factory:
            raise RevenueUnavailable("Database pool not available")

        from sqlalchemy import text

        query = text("""
            SELECT
                p.id AS property_id,
                p.tenant_id AS tenant_id,
                COALESCE(SUM(r.total_amount), 0) AS total_revenue,
                COUNT(r.id) AS reservation_count
            FROM properties p
            LEFT JOIN reservations r
                ON r.property_id = p.id
               AND r.tenant_id = p.tenant_id
               AND (r.check_in_date AT TIME ZONE p.timezone) >= make_timestamp(:year, :month, 1, 0, 0, 0)
               AND (r.check_in_date AT TIME ZONE p.timezone) < (make_timestamp(:year, :month, 1, 0, 0, 0) + INTERVAL '1 month')
            WHERE p.id = :property_id
              AND p.tenant_id = :tenant_id
            GROUP BY p.id, p.tenant_id
        """)

        async with db_pool.get_session() as session:
            result = await session.execute(query, {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "month": month,
                "year": year,
            })
            row = result.fetchone()

        if row is None:
            return {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "total": to_money(0),
                "currency": "USD",
                "count": 0,
                "month": month,
                "year": year,
            }

        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": to_money(row.total_revenue),
            "currency": "USD",
            "count": row.reservation_count,
            "month": month,
            "year": year,
        }
    except RevenueUnavailable:
        raise
    except Exception as e:
        raise RevenueUnavailable(
            f"Database error for {property_id} (tenant: {tenant_id}): {e}"
        ) from e

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    try:
        from app.core.database_pool import db_pool

        if not db_pool.session_factory:
            await db_pool.initialize()
        
        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                # Use SQLAlchemy text for raw SQL
                from sqlalchemy import text
                
                query = text("""
                    SELECT 
                        property_id,
                        SUM(total_amount) as total_revenue,
                        COUNT(*) as reservation_count
                    FROM reservations 
                    WHERE property_id = :property_id AND tenant_id = :tenant_id
                    GROUP BY property_id
                """)
                
                result = await session.execute(query, {
                    "property_id": property_id, 
                    "tenant_id": tenant_id
                })
                row = result.fetchone()
                
                if row:
                    total_revenue = Decimal(str(row.total_revenue))
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": str(total_revenue),
                        "currency": "USD", 
                        "count": row.reservation_count
                    }
                else:
                    # No reservations found for this property
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": "0.00",
                        "currency": "USD",
                        "count": 0
                    }
        raise RevenueUnavailable("Database pool not available")

    except RevenueUnavailable:
        raise
    except Exception as e:
        raise RevenueUnavailable(f"Database error for {property_id} (tenant: {tenant_id}): {e}") from e
