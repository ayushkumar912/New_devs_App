from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.cache import get_revenue_summary
from app.services.reservations import RevenueUnavailable, get_tenant_property, list_tenant_properties
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/properties")
async def get_dashboard_properties(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"
    try:
        properties = await list_tenant_properties(tenant_id)
    except RevenueUnavailable as exc:
        raise HTTPException(status_code=503, detail="Property data is temporarily unavailable") from exc
    return {"properties": properties}

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: int,
    year: int,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="month must be between 1 and 12")

    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"

    try:
        property_row = await get_tenant_property(property_id, tenant_id)
    except RevenueUnavailable as exc:
        raise HTTPException(status_code=503, detail="Revenue data is temporarily unavailable") from exc
    if property_row is None:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        revenue_data = await get_revenue_summary(property_id, tenant_id, month, year)
    except RevenueUnavailable as exc:
        raise HTTPException(status_code=503, detail="Revenue data is temporarily unavailable") from exc
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": revenue_data['total'],
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count'],
        "month": month,
        "year": year,
    }
