"""Type definitions for GCP FinOps Dashboard."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class CostData:
    """Cost data for a service or resource."""
    service: str
    sku: str
    cost: float
    usage_amount: float
    usage_unit: str
    project_id: str
    region: Optional[str] = None
    labels: Optional[Dict[str, str]] = None


@dataclass
class CloudRunService:
    """Cloud Run service information."""
    name: str
    region: str
    labels: Dict[str, str]
    cpu_allocated: str  # "always" or "request-only"
    memory_limit: str
    min_instances: int
    max_instances: int
    ingress: str
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None


@dataclass
class CloudRunMetrics:
    """Cloud Run service metrics."""
    service_name: str
    region: str
    request_count_30d: int
    avg_cpu_utilization: float  # percentage
    avg_memory_utilization: float  # percentage
    cold_start_count: int
    avg_request_latency_ms: float


@dataclass
class CloudFunction:
    """Cloud Functions information."""
    name: str
    region: str
    runtime: str
    memory_mb: int
    timeout_seconds: int
    labels: Dict[str, str]
    trigger_type: str  # "http", "event", etc.
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None


@dataclass
class CloudFunctionMetrics:
    """Cloud Functions metrics."""
    function_name: str
    region: str
    invocations_30d: int
    avg_execution_time_ms: float
    error_count: int
    avg_memory_usage_mb: float


@dataclass
class ComputeInstance:
    """Compute Engine instance information."""
    name: str
    zone: str
    machine_type: str
    status: str  # "RUNNING", "STOPPED", etc.
    labels: Dict[str, str]
    preemptible: bool
    created_time: Optional[datetime] = None


@dataclass
class CloudSQLInstance:
    """Cloud SQL instance information."""
    name: str
    region: str
    database_version: str
    tier: str
    state: str  # "RUNNABLE", "STOPPED", etc.
    labels: Dict[str, str]
    storage_gb: int
    created_time: Optional[datetime] = None


@dataclass
class CloudSQLMetrics:
    """Cloud SQL instance metrics."""
    instance_name: str
    region: str
    avg_connections_30d: float
    avg_cpu_utilization: float
    avg_memory_utilization: float
    query_count_30d: int


@dataclass
class PersistentDisk:
    """Persistent disk information."""
    name: str
    zone: str
    size_gb: int
    disk_type: str
    status: str
    in_use: bool
    labels: Dict[str, str]
    created_time: Optional[datetime] = None


@dataclass
class StaticIPAddress:
    """Static IP address information."""
    name: str
    region: str
    address: str
    address_type: str  # "EXTERNAL", "INTERNAL"
    status: str
    in_use: bool
    created_time: Optional[datetime] = None


@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation."""
    resource_type: str  # "cloud_run", "cloud_function", etc.
    resource_name: str
    region: str
    issue: str
    recommendation: str
    potential_monthly_savings: float
    priority: str  # "high", "medium", "low"
    details: Optional[Dict[str, Any]] = None


@dataclass
class AuditResult:
    """Resource audit result."""
    resource_type: str
    total_count: int
    untagged_count: int
    idle_count: int
    over_provisioned_count: int
    issues: List[str]
    recommendations: List[OptimizationRecommendation]
    potential_monthly_savings: float


@dataclass
class ForecastPoint:
    """Single forecast data point."""
    date: str  # YYYY-MM-DD format
    predicted_cost: float
    lower_bound: float  # Lower confidence interval
    upper_bound: float  # Upper confidence interval


@dataclass
class ForecastData:
    """Cost forecast data."""
    forecast_points: List[ForecastPoint]
    total_predicted_cost: float  # Total cost for forecast period
    forecast_days: int
    model_confidence: float  # 0-1 score
    trend: str  # "increasing", "decreasing", "stable"
    generated_at: str  # ISO timestamp


@dataclass
class DashboardData:
    """Complete dashboard data."""
    project_id: str
    billing_month: str
    current_month_cost: float
    last_month_cost: float
    ytd_cost: float
    service_costs: Dict[str, float]
    audit_results: Dict[str, AuditResult]
    recommendations: List[OptimizationRecommendation]
    total_potential_savings: float
    hide_project_id: bool = False

