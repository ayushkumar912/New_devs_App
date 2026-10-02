from decimal import Decimal
from typing import Dict, Any, List


class RevenueUnavailable(Exception):
    """Raised when revenue cannot be read from the database."""

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
                "total": "0.00",
                "currency": "USD",
                "count": 0,
                "month": month,
                "year": year,
            }

        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(Decimal(str(row.total_revenue))),
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
