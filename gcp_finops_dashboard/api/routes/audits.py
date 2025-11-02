"""Audit API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict

from ..config import get_cached_dashboard_data, get_dashboard_runner

router = APIRouter(prefix="/api/audits", tags=["audits"])


@router.get("")
async def get_all_audits():
    """Get all audit results."""
    try:
        data = get_cached_dashboard_data()
        
        results = {}
        for key, result in data.audit_results.items():
            results[key] = {
                "resource_type": result.resource_type,
                "total_count": result.total_count,
                "untagged_count": result.untagged_count,
                "idle_count": result.idle_count,
                "over_provisioned_count": result.over_provisioned_count,
                "issues": result.issues,
                "potential_monthly_savings": result.potential_monthly_savings,
            }
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audits: {str(e)}")


@router.get("/{audit_type}")
async def get_specific_audit(audit_type: str, refresh: bool = Query(False)):
    """Get specific audit result."""
    try:
        if refresh:
            runner = get_dashboard_runner()
            result = runner.run_specific_audit(audit_type)
            if not result:
                raise HTTPException(status_code=404, detail=f"Audit type '{audit_type}' not found")
        else:
            data = get_cached_dashboard_data()
            result = data.audit_results.get(audit_type)
            if not result:
                raise HTTPException(status_code=404, detail=f"Audit type '{audit_type}' not found")
        
        return {
            "resource_type": result.resource_type,
            "total_count": result.total_count,
            "untagged_count": result.untagged_count,
            "idle_count": result.idle_count,
            "over_provisioned_count": result.over_provisioned_count,
            "issues": result.issues,
            "potential_monthly_savings": result.potential_monthly_savings,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit: {str(e)}")

