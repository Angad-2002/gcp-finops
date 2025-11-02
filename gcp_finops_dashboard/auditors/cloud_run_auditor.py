"""Cloud Run resource auditor."""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from google.cloud import run_v2
from google.cloud import monitoring_v3
from google.api_core import exceptions

from ..types import (
    CloudRunService,
    CloudRunMetrics,
    OptimizationRecommendation,
    AuditResult
)
from ..helpers import parse_memory_string, format_memory_mb, get_resource_name_from_uri


class CloudRunAuditor:
    """Audit Cloud Run services for cost optimization."""
    
    def __init__(
        self,
        cloud_run_client: run_v2.ServicesClient,
        monitoring_client: monitoring_v3.MetricServiceClient,
        project_id: str
    ):
        """Initialize Cloud Run auditor.
        
        Args:
            cloud_run_client: Cloud Run API client
            monitoring_client: Cloud Monitoring API client
            project_id: GCP project ID
        """
        self.cloud_run_client = cloud_run_client
        self.monitoring_client = monitoring_client
        self.project_id = project_id
    
    def audit_all_services(self, regions: Optional[List[str]] = None) -> AuditResult:
        """Audit all Cloud Run services across regions.
        
        Args:
            regions: List of regions to audit (default: all common regions)
        
        Returns:
            AuditResult with findings and recommendations
        """
        if regions is None:
            regions = ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]
        
        all_services = []
        all_recommendations = []
        total_count = 0
        untagged_count = 0
        idle_count = 0
        over_provisioned_count = 0
        issues = []
        
        for region in regions:
            try:
                services = self.list_services(region)
                total_count += len(services)
                
                for service in services:
                    # Check for untagged services
                    if not service.labels:
                        untagged_count += 1
                    
                    # Get metrics
                    metrics = self.get_service_metrics(service.name, service.region)
                    
                    # Check for idle services
                    if metrics and metrics.request_count_30d == 0:
                        idle_count += 1
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="cloud_run",
                                resource_name=service.name,
                                region=service.region,
                                issue="Idle service (zero requests in 30 days)",
                                recommendation="Consider deleting or archiving this service",
                                potential_monthly_savings=10.0,  # Estimated
                                priority="medium",
                                details={"request_count_30d": 0}
                            )
                        )
                    
                    # Check for over-provisioned resources
                    if metrics:
                        # Check CPU allocation
                        if (service.cpu_allocated == "1" and  # "always" allocated
                            metrics.avg_cpu_utilization < 10.0):
                            over_provisioned_count += 1
                            all_recommendations.append(
                                OptimizationRecommendation(
                                    resource_type="cloud_run",
                                    resource_name=service.name,
                                    region=service.region,
                                    issue=f"CPU allocated 'always' but usage only {metrics.avg_cpu_utilization:.1f}%",
                                    recommendation="Change CPU allocation to 'request-only' (CPU throttling)",
                                    potential_monthly_savings=30.0,  # Estimated
                                    priority="high",
                                    details={
                                        "current_allocation": "always",
                                        "avg_cpu_utilization": metrics.avg_cpu_utilization
                                    }
                                )
                            )
                        
                        # Check memory allocation
                        if metrics.avg_memory_utilization < 20.0:
                            memory_mb = parse_memory_string(service.memory_limit)
                            recommended_mb = max(128, int(memory_mb * 0.5))
                            all_recommendations.append(
                                OptimizationRecommendation(
                                    resource_type="cloud_run",
                                    resource_name=service.name,
                                    region=service.region,
                                    issue=f"Low memory utilization ({metrics.avg_memory_utilization:.1f}%)",
                                    recommendation=f"Reduce memory from {service.memory_limit} to {format_memory_mb(recommended_mb)}",
                                    potential_monthly_savings=15.0,  # Estimated
                                    priority="medium",
                                    details={
                                        "current_memory": service.memory_limit,
                                        "recommended_memory": format_memory_mb(recommended_mb),
                                        "avg_memory_utilization": metrics.avg_memory_utilization
                                    }
                                )
                            )
                    
                    # Check for unnecessary min instances
                    if service.min_instances > 0:
                        savings = service.min_instances * 40.0  # Rough estimate per instance
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="cloud_run",
                                resource_name=service.name,
                                region=service.region,
                                issue=f"Min instances set to {service.min_instances} (always-on cost)",
                                recommendation="Set min instances to 0 unless cold starts are critical",
                                potential_monthly_savings=savings,
                                priority="high",
                                details={
                                    "current_min_instances": service.min_instances,
                                    "cold_start_count": metrics.cold_start_count if metrics else 0
                                }
                            )
                        )
                    
                    all_services.append(service)
            
            except exceptions.PermissionDenied:
                issues.append(f"Permission denied for region {region}")
            except Exception as e:
                issues.append(f"Error auditing region {region}: {str(e)}")
        
        # Calculate total potential savings
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="cloud_run",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=over_provisioned_count,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_services(self, region: str) -> List[CloudRunService]:
        """List all Cloud Run services in a region.
        
        Args:
            region: GCP region (e.g., 'us-central1')
        
        Returns:
            List of CloudRunService objects
        """
        parent = f"projects/{self.project_id}/locations/{region}"
        services = []
        
        try:
            for service in self.cloud_run_client.list_services(parent=parent):
                # Parse service details
                template = service.template
                container = template.containers[0] if template.containers else None
                
                # Get resource limits
                memory_limit = "256Mi"  # Default
                if container and container.resources and container.resources.limits:
                    memory_limit = container.resources.limits.get("memory", "256Mi")
                
                # Get scaling settings
                min_instances = 0
                max_instances = 100
                if template.scaling:
                    min_instances = template.scaling.min_instance_count
                    max_instances = template.scaling.max_instance_count
                
                # Get CPU allocation - check for CPU throttling annotation
                # Default to throttled (CPU allocated = "0") unless explicitly set to always
                cpu_allocated = "0"  # Default to throttled
                
                # Check if CPU throttling is disabled (CPU always allocated)
                if hasattr(template, 'metadata') and template.metadata and hasattr(template.metadata, 'annotations'):
                    annotations = template.metadata.annotations
                    if annotations and "run.googleapis.com/cpu-throttling" in annotations:
                        cpu_throttling = annotations["run.googleapis.com/cpu-throttling"]
                        if cpu_throttling.lower() == "false":
                            cpu_allocated = "1"  # Always allocated
                
                services.append(CloudRunService(
                    name=get_resource_name_from_uri(service.name),
                    region=region,
                    labels=dict(service.labels) if service.labels else {},
                    cpu_allocated=cpu_allocated,
                    memory_limit=memory_limit,
                    min_instances=min_instances,
                    max_instances=max_instances,
                    ingress=str(service.ingress),
                    created_time=service.create_time,
                    updated_time=service.update_time
                ))
        
        except exceptions.NotFound:
            # Region doesn't have Cloud Run services
            pass
        except exceptions.PermissionDenied:
            # No permission for this region
            raise
        
        return services
    
    def get_service_metrics(
        self,
        service_name: str,
        region: str,
        days: int = 30
    ) -> Optional[CloudRunMetrics]:
        """Get metrics for a Cloud Run service.
        
        Args:
            service_name: Service name
            region: GCP region
            days: Number of days to look back (default: 30)
        
        Returns:
            CloudRunMetrics object or None if no data
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        interval = monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": int(end_time.timestamp())},
                "start_time": {"seconds": int(start_time.timestamp())},
            }
        )
        
        metrics_data = {
            "request_count_30d": 0,
            "avg_cpu_utilization": 0.0,
            "avg_memory_utilization": 0.0,
            "cold_start_count": 0,
            "avg_request_latency_ms": 0.0
        }
        
        # Get request count
        try:
            request_count = self._query_metric(
                "run.googleapis.com/request_count",
                service_name,
                region,
                interval,
                aggregation="sum"
            )
            metrics_data["request_count_30d"] = int(request_count)
        except Exception:
            pass
        
        # Get CPU utilization
        try:
            cpu_util = self._query_metric(
                "run.googleapis.com/container/cpu/utilizations",
                service_name,
                region,
                interval,
                aggregation="mean"
            )
            metrics_data["avg_cpu_utilization"] = cpu_util * 100  # Convert to percentage
        except Exception:
            pass
        
        # Get memory utilization
        try:
            memory_util = self._query_metric(
                "run.googleapis.com/container/memory/utilizations",
                service_name,
                region,
                interval,
                aggregation="mean"
            )
            metrics_data["avg_memory_utilization"] = memory_util * 100  # Convert to percentage
        except Exception:
            pass
        
        # Get cold start count
        try:
            cold_starts = self._query_metric(
                "run.googleapis.com/request_count",
                service_name,
                region,
                interval,
                aggregation="sum",
                filter_str='metric.label.response_code_class="startup"'
            )
            metrics_data["cold_start_count"] = int(cold_starts)
        except Exception:
            pass
        
        # Get request latency
        try:
            latency = self._query_metric(
                "run.googleapis.com/request_latencies",
                service_name,
                region,
                interval,
                aggregation="mean"
            )
            metrics_data["avg_request_latency_ms"] = latency
        except Exception:
            pass
        
        return CloudRunMetrics(
            service_name=service_name,
            region=region,
            **metrics_data
        )
    
    def _query_metric(
        self,
        metric_type: str,
        service_name: str,
        region: str,
        interval: monitoring_v3.TimeInterval,
        aggregation: str = "mean",
        filter_str: str = ""
    ) -> float:
        """Query a metric from Cloud Monitoring.
        
        Args:
            metric_type: Metric type (e.g., 'run.googleapis.com/request_count')
            service_name: Service name
            region: GCP region
            interval: Time interval
            aggregation: Aggregation method ('mean', 'sum', etc.)
            filter_str: Additional filter string
        
        Returns:
            Aggregated metric value
        """
        filter_parts = [
            f'resource.type="cloud_run_revision"',
            f'resource.labels.service_name="{service_name}"',
            f'resource.labels.location="{region}"',
            f'metric.type="{metric_type}"'
        ]
        
        if filter_str:
            filter_parts.append(filter_str)
        
        filter_query = " AND ".join(filter_parts)
        
        aggregation_obj = monitoring_v3.Aggregation(
            {
                "alignment_period": {"seconds": 3600},  # 1 hour
                "per_series_aligner": getattr(
                    monitoring_v3.Aggregation.Aligner,
                    f"ALIGN_{aggregation.upper()}"
                ),
            }
        )
        
        request = monitoring_v3.ListTimeSeriesRequest(
            {
                "name": f"projects/{self.project_id}",
                "filter": filter_query,
                "interval": interval,
                "aggregation": aggregation_obj,
            }
        )
        
        results = self.monitoring_client.list_time_series(request=request)
        
        # Calculate aggregate across all points
        total = 0.0
        count = 0
        
        for result in results:
            for point in result.points:
                if hasattr(point.value, 'double_value'):
                    total += point.value.double_value
                elif hasattr(point.value, 'int64_value'):
                    total += point.value.int64_value
                count += 1
        
        return total / count if count > 0 else 0.0

