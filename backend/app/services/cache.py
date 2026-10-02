import json
import os
from typing import Any, Dict

import redis.asyncio as redis

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def revenue_cache_key(tenant_id: str, property_id: str) -> str:
    """Property ids are unique per tenant, so the tenant has to be part of the key."""
    return f"revenue:{tenant_id}:{property_id}"


async def get_revenue_summary(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    """
    cache_key = revenue_cache_key(tenant_id, property_id)

    cached = await redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        if (
            isinstance(data, dict)
            and data.get("tenant_id") == tenant_id
            and data.get("property_id") == property_id
        ):
            return data

    from app.services.reservations import calculate_total_revenue

    result = await calculate_total_revenue(property_id, tenant_id)

    await redis_client.set(cache_key, json.dumps(result), ex=300)

    return result
