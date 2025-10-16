"""Cloud Functions auditor."""

from typing import List, Optional
from datetime import datetime, timedelta
from google.cloud import functions_v2
from google.cloud import monitoring_v3
from google.api_core import exceptions

from .types import CloudFunction, CloudFunctionMetrics, OptimizationRecommendation, AuditResult
from .helpers import get_resource_name_from_uri


class CloudFunctionsAuditor:
    """Audit Cloud Functions for cost optimization."""
    
    def __init__(
        self,
        functions_client: functions_v2.FunctionServiceClient,
        monitoring_client: monitoring_v3.MetricServiceClient,
        project_id: str
    ):
        """Initialize Cloud Functions auditor.
        
        Args:
            functions_client: Cloud Functions API client
            monitoring_client: Cloud Monitoring API client
            project_id: GCP project ID
        """
        self.functions_client = functions_client
        self.monitoring_client = monitoring_client
        self.project_id = project_id
    
    def audit_all_functions(self, regions: Optional[List[str]] = None) -> AuditResult:
        """Audit all Cloud Functions across regions.
        
        Args:
            regions: List of regions to audit
        
        Returns:
            AuditResult with findings and recommendations
        """
        if regions is None:
            regions = ["us-central1", "us-east1", "us-west1", "europe-west1"]
        
        all_recommendations = []
        total_count = 0
        untagged_count = 0
        idle_count = 0
        over_provisioned_count = 0
        issues = []
        
        for region in regions:
            try:
                functions = self.list_functions(region)
                total_count += len(functions)
                
                for function in functions:
                    # Check for untagged functions
                    if not function.labels:
                        untagged_count += 1
                    
                    # Get metrics
                    metrics = self.get_function_metrics(function.name, function.region)
                    
                    # Check for idle functions
                    if metrics and metrics.invocations_30d == 0:
                        idle_count += 1
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="cloud_function",
                                resource_name=function.name,
                                region=function.region,
                                issue="Unused function (zero invocations in 30 days)",
                                recommendation="Consider deleting this function",
                                potential_monthly_savings=5.0,  # Estimated
                                priority="medium",
                                details={"invocations_30d": 0}
                            )
                        )
                    
                    # Check for over-provisioned memory
                    if metrics and metrics.avg_memory_usage_mb < function.memory_mb * 0.3:
                        over_provisioned_count += 1
                        recommended_mb = max(128, int(function.memory_mb * 0.5))
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="cloud_function",
                                resource_name=function.name,
                                region=function.region,
                                issue=f"Low memory utilization ({metrics.avg_memory_usage_mb:.0f}MB / {function.memory_mb}MB)",
                                recommendation=f"Reduce memory allocation to {recommended_mb}MB",
                                potential_monthly_savings=8.0,  # Estimated
                                priority="low",
                                details={
                                    "current_memory_mb": function.memory_mb,
                                    "recommended_memory_mb": recommended_mb,
                                    "avg_memory_usage_mb": metrics.avg_memory_usage_mb
                                }
                            )
                        )
                    
                    # Check for high error rates
                    if metrics and metrics.invocations_30d > 0:
                        error_rate = (metrics.error_count / metrics.invocations_30d) * 100
                        if error_rate > 5.0:
                            all_recommendations.append(
                                OptimizationRecommendation(
                                    resource_type="cloud_function",
                                    resource_name=function.name,
                                    region=function.region,
                                    issue=f"High error rate ({error_rate:.1f}%)",
                                    recommendation="Investigate and fix errors to avoid wasted invocations",
                                    potential_monthly_savings=10.0,  # Estimated
                                    priority="high",
                                    details={
                                        "error_rate": error_rate,
                                        "error_count": metrics.error_count,
                                        "total_invocations": metrics.invocations_30d
                                    }
                                )
                            )
            
            except exceptions.PermissionDenied:
                issues.append(f"Permission denied for region {region}")
            except Exception as e:
                issues.append(f"Error auditing region {region}: {str(e)}")
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="cloud_functions",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=over_provisioned_count,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_functions(self, region: str) -> List[CloudFunction]:
        """List all Cloud Functions in a region.
        
        Args:
            region: GCP region
        
        Returns:
            List of CloudFunction objects
        """
        parent = f"projects/{self.project_id}/locations/{region}"
        functions = []
        
        try:
            for function in self.functions_client.list_functions(parent=parent):
                # Parse function details
                build_config = function.build_config
                service_config = function.service_config
                
                runtime = build_config.runtime if build_config else "unknown"
                memory_mb = 256  # Default
                timeout_seconds = 60  # Default
                
                if service_config:
                    # Parse memory (e.g., "256M", "1G")
                    if service_config.available_memory:
                        memory_str = service_config.available_memory.upper()
                        if memory_str.endswith("G"):
                            memory_mb = int(float(memory_str[:-1]) * 1024)
                        elif memory_str.endswith("M"):
                            memory_mb = int(memory_str[:-1])
                    
                    if service_config.timeout_seconds:
                        timeout_seconds = service_config.timeout_seconds
                
                # Determine trigger type
                trigger_type = "unknown"
                if function.event_trigger:
                    trigger_type = "event"
                elif service_config and service_config.uri:
                    trigger_type = "http"
                
                functions.append(CloudFunction(
                    name=get_resource_name_from_uri(function.name),
                    region=region,
                    runtime=runtime,
                    memory_mb=memory_mb,
                    timeout_seconds=timeout_seconds,
                    labels=dict(function.labels) if function.labels else {},
                    trigger_type=trigger_type,
                    created_time=function.create_time,
                    updated_time=function.update_time
                ))
        
        except exceptions.NotFound:
            pass
        except exceptions.PermissionDenied:
            raise
        
        return functions
    
    def get_function_metrics(
        self,
        function_name: str,
        region: str,
        days: int = 30
    ) -> Optional[CloudFunctionMetrics]:
        """Get metrics for a Cloud Function.
        
        Args:
            function_name: Function name
            region: GCP region
            days: Number of days to look back
        
        Returns:
            CloudFunctionMetrics object or None
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
            "invocations_30d": 0,
            "avg_execution_time_ms": 0.0,
            "error_count": 0,
            "avg_memory_usage_mb": 0.0
        }
        
        # Get invocation count
        try:
            invocations = self._query_metric(
                "cloudfunctions.googleapis.com/function/execution_count",
                function_name,
                region,
                interval,
                aggregation="sum"
            )
            metrics_data["invocations_30d"] = int(invocations)
        except Exception:
            pass
        
        # Get execution time
        try:
            exec_time = self._query_metric(
                "cloudfunctions.googleapis.com/function/execution_times",
                function_name,
                region,
                interval,
                aggregation="mean"
            )
            metrics_data["avg_execution_time_ms"] = exec_time
        except Exception:
            pass
        
        # Get error count
        try:
            errors = self._query_metric(
                "cloudfunctions.googleapis.com/function/execution_count",
                function_name,
                region,
                interval,
                aggregation="sum",
                filter_str='metric.label.status!="ok"'
            )
            metrics_data["error_count"] = int(errors)
        except Exception:
            pass
        
        # Get memory usage (if available)
        try:
            memory = self._query_metric(
                "cloudfunctions.googleapis.com/function/user_memory_bytes",
                function_name,
                region,
                interval,
                aggregation="mean"
            )
            metrics_data["avg_memory_usage_mb"] = memory / (1024 * 1024)  # Convert to MB
        except Exception:
            pass
        
        return CloudFunctionMetrics(
            function_name=function_name,
            region=region,
            **metrics_data
        )
    
    def _query_metric(
        self,
        metric_type: str,
        function_name: str,
        region: str,
        interval: monitoring_v3.TimeInterval,
        aggregation: str = "mean",
        filter_str: str = ""
    ) -> float:
        """Query a metric from Cloud Monitoring."""
        filter_parts = [
            f'resource.type="cloud_function"',
            f'resource.labels.function_name="{function_name}"',
            f'resource.labels.region="{region}"',
            f'metric.type="{metric_type}"'
        ]
        
        if filter_str:
            filter_parts.append(filter_str)
        
        filter_query = " AND ".join(filter_parts)
        
        aggregation_obj = monitoring_v3.Aggregation(
            {
                "alignment_period": {"seconds": 3600},
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

