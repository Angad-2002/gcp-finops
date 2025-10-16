"""FastAPI backend for GCP FinOps Dashboard."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import os
from dataclasses import asdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .dashboard_runner import DashboardRunner
from .types import DashboardData, AuditResult, OptimizationRecommendation, ForecastData
from .helpers import get_project_id, calculate_percentage_change
from .pdf_utils import ReportGenerator
from .llm_service import get_llm_service
from .forecast_service import ForecastService
from .gcp_client import get_bigquery_client

app = FastAPI(
    title="GCP FinOps Dashboard API",
    description="API for GCP FinOps cost optimization and resource auditing",
    version="1.0.0"
)

# CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global configuration
_project_id: Optional[str] = None
_billing_dataset: Optional[str] = None
_billing_table_prefix: str = "gcp_billing_export_v1"
_regions: Optional[List[str]] = None
_bigquery_location: Optional[str] = None

# Cache for dashboard data
_cached_dashboard_data: Optional[DashboardData] = None
_cache_timestamp: Optional[datetime] = None
_cache_ttl_seconds = 300  # 5 minutes

# Cache for forecast data
_cached_forecast: Optional[ForecastData] = None
_forecast_cache_timestamp: Optional[datetime] = None
_forecast_cache_ttl_seconds = 900  # 15 minutes (forecasts can be cached longer)

# Reports directory configuration
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def get_dashboard_runner() -> DashboardRunner:
    """Get configured dashboard runner."""
    global _project_id, _billing_dataset, _bigquery_location, _regions
    
    if not _project_id:
        _project_id = os.getenv("GCP_PROJECT_ID") or get_project_id()
    
    if not _billing_dataset:
        _billing_dataset = os.getenv("GCP_BILLING_DATASET")
    
    if not _bigquery_location:
        _bigquery_location = os.getenv("BIGQUERY_LOCATION") or os.getenv("GCP_BIGQUERY_LOCATION") or "US"
    
    if not _regions:
        regions_env = os.getenv("GCP_REGIONS")
        if regions_env:
            _regions = [r.strip() for r in regions_env.split(",")]
        else:
            _regions = ["us-central1", "us-east1", "europe-west1"]
    
    if not _project_id:
        raise HTTPException(
            status_code=400,
            detail="Project ID not configured. Set GCP_PROJECT_ID environment variable or configure via /api/config endpoint."
        )
    
    if not _billing_dataset:
        raise HTTPException(
            status_code=400,
            detail="Billing dataset not configured. Set GCP_BILLING_DATASET environment variable or configure via /api/config endpoint."
        )
    
    return DashboardRunner(
        project_id=_project_id,
        billing_dataset=_billing_dataset,
        billing_table_prefix=_billing_table_prefix,
        regions=_regions,
        location=_bigquery_location
    )


def get_forecast_service() -> ForecastService:
    """Get configured forecast service."""
    global _project_id, _billing_dataset, _bigquery_location
    
    if not _project_id:
        _project_id = os.getenv("GCP_PROJECT_ID") or get_project_id()
    
    if not _billing_dataset:
        _billing_dataset = os.getenv("GCP_BILLING_DATASET")
    
    if not _bigquery_location:
        _bigquery_location = os.getenv("BIGQUERY_LOCATION") or os.getenv("GCP_BIGQUERY_LOCATION") or "US"
    
    if not _project_id:
        raise HTTPException(
            status_code=400,
            detail="Project ID not configured. Set GCP_PROJECT_ID environment variable or configure via /api/config endpoint."
        )
    
    if not _billing_dataset:
        raise HTTPException(
            status_code=400,
            detail="Billing dataset not configured. Set GCP_BILLING_DATASET environment variable or configure via /api/config endpoint."
        )
    
    client = get_bigquery_client(location=_bigquery_location)
    
    return ForecastService(
        client=client,
        billing_dataset=_billing_dataset,
        billing_table_prefix=_billing_table_prefix
    )


def get_cached_dashboard_data(force_refresh: bool = False) -> DashboardData:
    """Get dashboard data with caching."""
    global _cached_dashboard_data, _cache_timestamp
    
    now = datetime.now()
    
    # Check if we need to refresh cache
    if (
        force_refresh
        or _cached_dashboard_data is None
        or _cache_timestamp is None
        or (now - _cache_timestamp).total_seconds() > _cache_ttl_seconds
    ):
        runner = get_dashboard_runner()
        _cached_dashboard_data = runner.run()
        _cache_timestamp = now
    
    return _cached_dashboard_data


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "GCP FinOps Dashboard API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "configured": _project_id is not None and _billing_dataset is not None
    }


@app.post("/api/config")
async def configure(
    project_id: Optional[str] = None,
    billing_dataset: Optional[str] = None,
    billing_table_prefix: Optional[str] = None,
    regions: Optional[List[str]] = None,
    bigquery_location: Optional[str] = None
):
    """Configure API settings."""
    global _project_id, _billing_dataset, _billing_table_prefix, _regions, _bigquery_location, _cached_dashboard_data
    
    if project_id:
        _project_id = project_id
    if billing_dataset:
        _billing_dataset = billing_dataset
    if billing_table_prefix:
        _billing_table_prefix = billing_table_prefix
    if regions:
        _regions = regions
    if bigquery_location:
        _bigquery_location = bigquery_location
    
    # Clear cache when configuration changes
    _cached_dashboard_data = None
    
    return {
        "status": "configured",
        "project_id": _project_id,
        "billing_dataset": _billing_dataset,
        "billing_table_prefix": _billing_table_prefix,
        "regions": _regions,
        "bigquery_location": _bigquery_location
    }


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    return {
        "project_id": _project_id,
        "billing_dataset": _billing_dataset,
        "billing_table_prefix": _billing_table_prefix,
        "regions": _regions,
        "bigquery_location": _bigquery_location
    }


@app.get("/api/dashboard")
async def get_dashboard(refresh: bool = Query(False, description="Force refresh data")):
    """Get complete dashboard data."""
    try:
        data = get_cached_dashboard_data(force_refresh=refresh)
        
        # Convert dataclass to dict
        result = {
            "project_id": data.project_id,
            "billing_month": data.billing_month,
            "current_month_cost": data.current_month_cost,
            "last_month_cost": data.last_month_cost,
            "ytd_cost": data.ytd_cost,
            "service_costs": data.service_costs,
            "total_potential_savings": data.total_potential_savings,
            "audit_results": {
                key: {
                    "resource_type": result.resource_type,
                    "total_count": result.total_count,
                    "untagged_count": result.untagged_count,
                    "idle_count": result.idle_count,
                    "over_provisioned_count": result.over_provisioned_count,
                    "issues": result.issues,
                    "potential_monthly_savings": result.potential_monthly_savings,
                }
                for key, result in data.audit_results.items()
            },
            "recommendations": [
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
                for rec in data.recommendations
            ],
        }
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")


@app.get("/api/summary")
async def get_summary():
    """Get cost summary."""
    try:
        data = get_cached_dashboard_data()
        
        # Use helper function to avoid division by zero
        change_pct = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        
        # Count total resources
        total_resources = sum(
            result.total_count
            for result in data.audit_results.values()
        )
        
        return {
            "current_month": data.current_month_cost,
            "last_month": data.last_month_cost,
            "ytd": data.ytd_cost,
            "change_pct": change_pct,
            "resources_active": total_resources,
            "potential_savings": data.total_potential_savings,
            "project_id": data.project_id,
            "billing_month": data.billing_month,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary: {str(e)}")


@app.get("/api/costs/services")
async def get_service_costs():
    """Get costs by service."""
    try:
        data = get_cached_dashboard_data()
        
        # Convert to array format for frontend
        services = [
            {"name": service, "value": cost}
            for service, cost in data.service_costs.items()
        ]
        
        # Sort by cost descending
        services.sort(key=lambda x: x["value"], reverse=True)
        
        return services
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch service costs: {str(e)}")


@app.get("/api/costs/trend")
async def get_cost_trend():
    """Get cost trend data (6 months)."""
    try:
        # This would need to be implemented in cost_processor to fetch historical data
        # For now, return a simple trend based on current data
        data = get_cached_dashboard_data()
        
        # Generate simple trend (would be replaced with actual historical data)
        current = data.current_month_cost
        last = data.last_month_cost
        
        months = ["May", "Jun", "Jul", "Aug", "Sep", "Oct"]
        trend = []
        
        for i, month in enumerate(months):
            if i == len(months) - 1:
                cost = current
            elif i == len(months) - 2:
                cost = last
            else:
                # Estimate previous months
                cost = last * (0.85 + i * 0.05)
            
            # Calculate change percentage, avoiding division by zero
            if i == 0:
                change = 0
            elif trend[i-1]["cost"] == 0:
                # If previous cost was 0, calculate as 100% increase if current > 0, else 0
                change = 100.0 if cost > 0 else 0
            else:
                change = ((cost - trend[i-1]["cost"]) / trend[i-1]["cost"]) * 100
            
            trend.append({
                "month": month,
                "cost": round(cost, 2),
                "change": round(change, 1)
            })
        
        return trend
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cost trend: {str(e)}")


@app.get("/api/audits")
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


@app.get("/api/audits/{audit_type}")
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


@app.get("/api/recommendations")
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


@app.get("/api/resources/summary")
async def get_resources_summary():
    """Get resources summary."""
    try:
        data = get_cached_dashboard_data()
        
        total = 0
        idle = 0
        untagged = 0
        
        for result in data.audit_results.values():
            total += result.total_count
            idle += result.idle_count
            untagged += result.untagged_count
        
        running = total - idle
        
        return {
            "total": total,
            "running": running,
            "idle": idle,
            "untagged": untagged,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch resources summary: {str(e)}")


@app.post("/api/refresh")
async def refresh_data():
    """Force refresh all dashboard data."""
    try:
        global _cached_dashboard_data, _cache_timestamp
        _cached_dashboard_data = None
        _cache_timestamp = None
        
        data = get_cached_dashboard_data(force_refresh=True)
        
        return {
            "status": "refreshed",
            "timestamp": datetime.now().isoformat(),
            "project_id": data.project_id,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh data: {str(e)}")


# ============================================================================
# REPORTS ENDPOINTS (File-based storage)
# ============================================================================

@app.post("/api/reports/generate")
async def generate_report(
    format: str = Query("pdf", description="Report format (currently only 'pdf' supported)")
):
    """
    Generate a new PDF report and save it to the reports directory.
    
    Returns metadata about the generated report including download URL.
    """
    try:
        # Get dashboard data
        data = get_cached_dashboard_data()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"gcp-finops-report-{timestamp}.pdf"
        output_path = REPORTS_DIR / filename
        
        # Generate the report - pass REPORTS_DIR so temp files are created there
        report_gen = ReportGenerator(output_dir=str(REPORTS_DIR))
        report_gen.generate_report(data, str(output_path))
        
        # Get file size
        file_size = output_path.stat().st_size
        
        return {
            "success": True,
            "filename": filename,
            "size": f"{file_size / 1024:.1f} KB",
            "size_bytes": file_size,
            "created_at": datetime.now().isoformat(),
            "download_url": f"/api/reports/{filename}/download",
            "project_id": data.project_id,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@app.get("/api/reports")
async def list_reports():
    """
    List all generated reports from the reports directory.
    
    Returns list of reports with metadata sorted by creation date (newest first).
    """
    try:
        reports = []
        
        # Scan reports directory for PDF files
        for file_path in REPORTS_DIR.glob("*.pdf"):
            stat = file_path.stat()
            
            # Extract project ID from filename if possible
            # Format: gcp-finops-report-{timestamp}.pdf
            project_id = None
            if file_path.stem.startswith("gcp-finops-report-"):
                parts = file_path.stem.split("-")
                if len(parts) >= 5:
                    project_id = "-".join(parts[3:-2])  # Everything between "report" and timestamp
            
            reports.append({
                "filename": file_path.name,
                "size": f"{stat.st_size / 1024:.1f} KB",
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "download_url": f"/api/reports/{file_path.name}/download",
                "project_id": project_id,
            })
        
        # Sort by creation time (newest first)
        reports.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "reports": reports,
            "total": len(reports),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


@app.get("/api/reports/{filename}/download")
async def download_report(filename: str):
    """
    Download a specific report by filename.
    
    Returns the PDF file for download.
    """
    try:
        file_path = REPORTS_DIR / filename
        
        # Security check: ensure filename doesn't contain path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=filename,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download report: {str(e)}")


@app.delete("/api/reports/{filename}")
async def delete_report(filename: str):
    """
    Delete a specific report by filename.
    
    Returns success message.
    """
    try:
        file_path = REPORTS_DIR / filename
        
        # Security check: ensure filename doesn't contain path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Delete the file
        file_path.unlink()
        
        return {
            "success": True,
            "message": f"Report '{filename}' deleted successfully",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")


# ============================================================================
# AI INSIGHTS ENDPOINTS (Groq LLM)
# ============================================================================

@app.get("/api/ai/status")
async def ai_status():
    """
    Check if AI features are enabled and available.
    
    Returns status of Groq API integration.
    """
    llm_service = get_llm_service()
    
    return {
        "enabled": llm_service is not None,
        "model": llm_service.model if llm_service else None,
        "provider": "Groq",
        "message": "AI features are enabled" if llm_service else "Set GROQ_API_KEY environment variable to enable AI features"
    }


@app.get("/api/ai/models")
async def get_available_models():
    """
    Get list of available Groq AI models.
    
    Returns available models with descriptions and recommendations.
    """
    from .llm_service import LLMService
    
    models = LLMService.get_available_models()
    
    # Convert to list format for frontend
    model_list = [
        {
            "id": model_id,
            "name": info["name"],
            "description": info["description"],
            "context_window": info["context_window"],
            "recommended": info.get("recommended", False)
        }
        for model_id, info in models.items()
    ]
    
    # Get current model
    current_model = os.getenv("GROQ_MODEL") or LLMService.DEFAULT_MODEL
    
    return {
        "models": model_list,
        "current_model": current_model,
        "default_model": LLMService.DEFAULT_MODEL
    }


@app.post("/api/ai/models/set")
async def set_ai_model(model_id: str = Query(..., description="Model ID to use")):
    """
    Set the AI model to use for analysis.
    
    Note: This sets it for the current session only. To persist, set GROQ_MODEL environment variable.
    """
    from .llm_service import LLMService
    
    # Validate model exists
    if model_id not in LLMService.AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model ID. Available models: {', '.join(LLMService.AVAILABLE_MODELS.keys())}"
        )
    
    # Update environment variable for current process
    os.environ["GROQ_MODEL"] = model_id
    
    # Reset LLM service singleton to pick up new model
    global _llm_service
    _llm_service = None
    
    return {
        "success": True,
        "model": model_id,
        "message": f"AI model set to {model_id} (session only - set GROQ_MODEL env var to persist)"
    }


@app.post("/api/ai/analyze")
async def ai_analyze_dashboard(refresh: bool = Query(False)):
    """
    Generate comprehensive AI analysis of dashboard data.
    
    Uses Groq's LLM to provide insights, recommendations, and anomaly detection.
    """
    llm_service = get_llm_service()
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="AI features not available. Set GROQ_API_KEY environment variable."
        )
    
    try:
        data = get_cached_dashboard_data(force_refresh=refresh)
        analysis = llm_service.analyze_dashboard_data(data)
        
        return {
            "success": True,
            "analysis": analysis["analysis"],
            "model": analysis["model_used"],
            "project_id": analysis["project_id"],
            "billing_month": analysis["billing_month"],
            "generated_at": datetime.now().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI analysis: {str(e)}")


@app.post("/api/ai/explain-spike")
async def ai_explain_cost_spike():
    """
    Get AI explanation for cost increases or decreases.
    
    Analyzes why costs changed compared to last month.
    """
    llm_service = get_llm_service()
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="AI features not available. Set GROQ_API_KEY environment variable."
        )
    
    try:
        data = get_cached_dashboard_data()
        explanation = llm_service.explain_cost_spike(data)
        
        return {
            "success": True,
            "explanation": explanation,
            "current_month": data.current_month_cost,
            "last_month": data.last_month_cost,
            "change_pct": calculate_percentage_change(data.current_month_cost, data.last_month_cost),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to explain cost spike: {str(e)}")


@app.post("/api/ai/executive-summary")
async def ai_executive_summary():
    """
    Generate executive summary of FinOps data.
    
    Creates a concise summary suitable for stakeholders.
    """
    llm_service = get_llm_service()
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="AI features not available. Set GROQ_API_KEY environment variable."
        )
    
    try:
        data = get_cached_dashboard_data()
        summary = llm_service.generate_executive_summary(data)
        
        return {
            "success": True,
            "summary": summary,
            "project_id": data.project_id,
            "billing_month": data.billing_month,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@app.post("/api/ai/ask")
async def ai_ask_question(question: str = Query(..., description="Your question about the FinOps data")):
    """
    Ask a natural language question about your GCP costs.
    
    Examples:
    - "Why are my Cloud Run costs so high?"
    - "What are my biggest cost drivers?"
    - "How many idle resources do I have?"
    """
    llm_service = get_llm_service()
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="AI features not available. Set GROQ_API_KEY environment variable."
        )
    
    try:
        data = get_cached_dashboard_data()
        answer = llm_service.answer_question(question, data)
        
        return {
            "success": True,
            "question": question,
            "answer": answer,
            "generated_at": datetime.now().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")


@app.post("/api/ai/prioritize-recommendations")
async def ai_prioritize_recommendations():
    """
    Get AI help prioritizing optimization recommendations.
    
    Suggests which recommendations to implement first based on impact and complexity.
    """
    llm_service = get_llm_service()
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="AI features not available. Set GROQ_API_KEY environment variable."
        )
    
    try:
        data = get_cached_dashboard_data()
        prioritization = llm_service.prioritize_recommendations(data.recommendations)
        
        return {
            "success": True,
            "prioritization": prioritization,
            "total_recommendations": len(data.recommendations),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prioritize recommendations: {str(e)}")


@app.post("/api/ai/suggest-budgets")
async def ai_suggest_budget_alerts():
    """
    Get AI suggestions for budget alert thresholds.
    
    Analyzes spending patterns to recommend appropriate budget limits.
    """
    llm_service = get_llm_service()
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="AI features not available. Set GROQ_API_KEY environment variable."
        )
    
    try:
        data = get_cached_dashboard_data()
        suggestions = llm_service.suggest_budget_alerts(data)
        
        return {
            "success": True,
            "suggestions": suggestions,
            "current_month_cost": data.current_month_cost,
            "ytd_cost": data.ytd_cost,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest budgets: {str(e)}")


@app.post("/api/ai/analyze-utilization")
async def ai_analyze_utilization():
    """
    Analyze resource utilization patterns with AI.
    
    Provides insights on how efficiently resources are being used.
    """
    llm_service = get_llm_service()
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="AI features not available. Set GROQ_API_KEY environment variable."
        )
    
    try:
        data = get_cached_dashboard_data()
        analysis = llm_service.analyze_resource_utilization(data.audit_results)
        
        return {
            "success": True,
            "analysis": analysis,
            "total_resources": sum(r.total_count for r in data.audit_results.values()),
            "idle_resources": sum(r.idle_count for r in data.audit_results.values()),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze utilization: {str(e)}")


# ============================================================================
# FORECASTING ENDPOINTS (Prophet-based)
# ============================================================================

@app.get("/api/forecast")
async def get_cost_forecast(
    days: int = Query(90, description="Number of days to forecast (default: 90)"),
    historical_days: int = Query(180, description="Days of historical data to use (default: 180)"),
    refresh: bool = Query(False, description="Force refresh forecast")
):
    """
    Get cost forecast using Prophet.
    
    Predicts future costs based on historical billing data.
    Returns daily predictions with confidence intervals.
    """
    try:
        global _cached_forecast, _forecast_cache_timestamp
        
        now = datetime.now()
        
        # Check if we need to refresh cache
        if (
            refresh
            or _cached_forecast is None
            or _forecast_cache_timestamp is None
            or (now - _forecast_cache_timestamp).total_seconds() > _forecast_cache_ttl_seconds
        ):
            forecast_service = get_forecast_service()
            _cached_forecast = forecast_service.forecast_costs(
                forecast_days=days,
                historical_days=historical_days,
                project_id=None  # Use None to query all projects in dataset
            )
            _forecast_cache_timestamp = now
        
        # Convert to dict format
        result = {
            "forecast_points": [
                {
                    "date": point.date,
                    "predicted_cost": point.predicted_cost,
                    "lower_bound": point.lower_bound,
                    "upper_bound": point.upper_bound,
                }
                for point in _cached_forecast.forecast_points
            ],
            "total_predicted_cost": _cached_forecast.total_predicted_cost,
            "forecast_days": _cached_forecast.forecast_days,
            "model_confidence": _cached_forecast.model_confidence,
            "trend": _cached_forecast.trend,
            "generated_at": _cached_forecast.generated_at,
        }
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast: {str(e)}")


@app.get("/api/forecast/summary")
async def get_forecast_summary(
    days: int = Query(30, description="Number of days to forecast (default: 30)")
):
    """
    Get summarized forecast information.
    
    Returns key metrics like predicted monthly cost and trend.
    """
    try:
        forecast_service = get_forecast_service()
        forecast = forecast_service.forecast_costs(
            forecast_days=days,
            historical_days=180,
            project_id=None  # Use None to query all projects
        )
        
        # Get current month cost for comparison
        data = get_cached_dashboard_data()
        
        return {
            "predicted_cost_next_30d": forecast.total_predicted_cost,
            "current_month_cost": data.current_month_cost,
            "trend": forecast.trend,
            "confidence": forecast.model_confidence,
            "forecast_days": days,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast summary: {str(e)}")


@app.get("/api/forecast/service/{service_name}")
async def get_service_forecast(
    service_name: str,
    days: int = Query(90, description="Number of days to forecast"),
    historical_days: int = Query(180, description="Days of historical data to use")
):
    """
    Get cost forecast for a specific GCP service.
    
    Examples:
    - /api/forecast/service/Cloud%20Run
    - /api/forecast/service/Compute%20Engine
    """
    try:
        forecast_service = get_forecast_service()
        forecast = forecast_service.forecast_service_cost(
            service_name=service_name,
            forecast_days=days,
            historical_days=historical_days,
            project_id=None  # Use None to query all projects
        )
        
        result = {
            "service_name": service_name,
            "forecast_points": [
                {
                    "date": point.date,
                    "predicted_cost": point.predicted_cost,
                    "lower_bound": point.lower_bound,
                    "upper_bound": point.upper_bound,
                }
                for point in forecast.forecast_points
            ],
            "total_predicted_cost": forecast.total_predicted_cost,
            "forecast_days": forecast.forecast_days,
            "model_confidence": forecast.model_confidence,
            "trend": forecast.trend,
            "generated_at": forecast.generated_at,
        }
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate forecast for service '{service_name}': {str(e)}"
        )


@app.get("/api/forecast/trends")
async def get_forecast_trends():
    """
    Get forecast trends for all major services.
    
    Returns predicted costs and trends for top services.
    """
    try:
        # Get top services from current data
        data = get_cached_dashboard_data()
        top_services = sorted(
            data.service_costs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5 services
        
        forecast_service = get_forecast_service()
        
        trends = []
        for service_name, current_cost in top_services:
            try:
                forecast = forecast_service.forecast_service_cost(
                    service_name=service_name,
                    forecast_days=30,
                    historical_days=90,
                    project_id=None  # Use None to query all projects
                )
                
                trends.append({
                    "service_name": service_name,
                    "current_cost": current_cost,
                    "predicted_cost_30d": forecast.total_predicted_cost,
                    "trend": forecast.trend,
                    "confidence": forecast.model_confidence,
                })
            except Exception:
                # Skip services that fail to forecast
                continue
        
        return {
            "trends": trends,
            "generated_at": datetime.now().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast trends: {str(e)}")


@app.get("/api/forecast/debug")
async def debug_forecast():
    """Debug endpoint to check forecast data retrieval."""
    from datetime import datetime, timedelta
    try:
        forecast_service = get_forecast_service()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        debug_info = {
            "config": {
                "project_id": _project_id,
                "billing_dataset": _billing_dataset,
                "table_prefix": _billing_table_prefix,
            },
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "start_suffix": start_date.strftime("%Y%m%d"),
                "end_suffix": end_date.strftime("%Y%m%d"),
            }
        }
        
        # Try to get data (use None for project_id to get all data in test dataset)
        df = forecast_service.get_historical_daily_costs(180, None)
        
        debug_info.update({
            "result": {
                "rows": len(df),
                "columns": list(df.columns) if not df.empty else [],
                "date_range": {
                    "min": str(df['ds'].min()) if not df.empty else None,
                    "max": str(df['ds'].max()) if not df.empty else None
                },
                "total_cost": float(df['y'].sum()) if not df.empty else 0,
                "sample": df.head(3).to_dict('records') if not df.empty else []
            }
        })
        
        return debug_info
    except Exception as e:
        import traceback
        return {
            "error": str(e), 
            "type": str(type(e).__name__),
            "traceback": traceback.format_exc()
        }


@app.get("/api/forecast/alert-thresholds")
async def get_forecast_alert_thresholds():
    """
    Get recommended alert thresholds based on forecast.
    
    Suggests budget limits and alert thresholds based on predicted spending.
    """
    try:
        forecast_service = get_forecast_service()
        
        # Get 30-day forecast
        forecast = forecast_service.forecast_costs(
            forecast_days=30,
            historical_days=180,
            project_id=None  # Use None to query all projects
        )
        
        # Calculate recommended thresholds
        predicted_30d = forecast.total_predicted_cost
        
        # Conservative threshold (10% above prediction)
        conservative_threshold = predicted_30d * 1.10
        
        # Warning threshold (20% above prediction)
        warning_threshold = predicted_30d * 1.20
        
        # Critical threshold (30% above prediction)
        critical_threshold = predicted_30d * 1.30
        
        return {
            "predicted_monthly_cost": predicted_30d,
            "recommended_thresholds": {
                "conservative": round(conservative_threshold, 2),
                "warning": round(warning_threshold, 2),
                "critical": round(critical_threshold, 2),
            },
            "confidence": forecast.model_confidence,
            "trend": forecast.trend,
            "generated_at": datetime.now().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate alert thresholds: {str(e)}")


def start_api_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the FastAPI server.
    
    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 8000)
    """
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_api_server()

