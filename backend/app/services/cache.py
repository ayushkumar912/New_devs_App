import json
import os
from typing import Any, Dict

import redis.asyncio as redis

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def revenue_cache_key(tenant_id: str, property_id: str, year: int, month: int) -> str:
    """Property ids are unique per tenant, and totals differ by local month."""
    return f"revenue:{tenant_id}:{property_id}:{year:04d}-{month:02d}"


async def get_revenue_summary(property_id: str, tenant_id: str, month: int, year: int) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    """
    cache_key = revenue_cache_key(tenant_id, property_id, year, month)

    cached = await redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        if (
            isinstance(data, dict)
            and data.get("tenant_id") == tenant_id
            and data.get("property_id") == property_id
            and data.get("month") == month
            and data.get("year") == year
        ):
            return data

    from app.services.reservations import calculate_monthly_revenue

    result = await calculate_monthly_revenue(property_id, tenant_id, month, year)

    await redis_client.set(cache_key, json.dumps(result), ex=300)

    return result
