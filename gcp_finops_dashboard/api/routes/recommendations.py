"""Recommendations API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from ..config import get_cached_dashboard_data

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
async def get_recommendations(
    priority: Optional[str] = Query(None, description="Filter by priority: high, medium, low"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: Optional[int] = Query(None, description="Limit number of results")
):
    """Get optimization recommendations."""
    try:
        data = get_cached_dashboard_data()
        recommendations = data.recommendations
        
        # Apply filters
        if priority:
            recommendations = [r for r in recommendations if r.priority == priority]
        
        if resource_type:
            recommendations = [r for r in recommendations if r.resource_type == resource_type]
        
        # Sort by savings (highest first)
        recommendations.sort(key=lambda x: x.potential_monthly_savings, reverse=True)
        
        # Apply limit
        if limit:
            recommendations = recommendations[:limit]
        
        return [
            {
                "resource_type": rec.resource_type,
                "resource_name": rec.resource_name,
                "region": rec.region,
                "issue": rec.issue,
                "recommendation": rec.recommendation,
                "potential_monthly_savings": rec.potential_monthly_savings,
                "priority": rec.priority,
                "details": rec.details,
            }
            for rec in recommendations
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recommendations: {str(e)}")

