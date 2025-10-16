"""Cloud SQL auditor."""

from typing import List, Optional, Any
from datetime import datetime, timedelta
from google.cloud import monitoring_v3
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from .types import CloudSQLInstance, CloudSQLMetrics, OptimizationRecommendation, AuditResult


class CloudSQLAuditor:
    """Audit Cloud SQL instances for cost optimization."""
    
    def __init__(
        self,
        cloud_sql_client: Resource,
        monitoring_client: monitoring_v3.MetricServiceClient,
        project_id: str
    ):
        """Initialize Cloud SQL auditor.
        
        Args:
            cloud_sql_client: Cloud SQL Admin API client (Discovery API)
            monitoring_client: Cloud Monitoring API client
            project_id: GCP project ID
        """
        self.cloud_sql_client = cloud_sql_client
        self.monitoring_client = monitoring_client
        self.project_id = project_id
    
    def audit_all_instances(self) -> AuditResult:
        """Audit all Cloud SQL instances.
        
        Returns:
            AuditResult with findings and recommendations
        """
        all_recommendations = []
        total_count = 0
        untagged_count = 0
        idle_count = 0
        over_provisioned_count = 0
        issues = []
        
        try:
            instances = self.list_instances()
            total_count = len(instances)
            
            for instance in instances:
                # Check for untagged instances
                if not instance.labels:
                    untagged_count += 1
                
                # Check for stopped instances
                if instance.state != "RUNNABLE":
                    idle_count += 1
                    all_recommendations.append(
                        OptimizationRecommendation(
                            resource_type="cloud_sql",
                            resource_name=instance.name,
                            region=instance.region,
                            issue=f"Instance is in {instance.state} state",
                            recommendation="Delete if no longer needed",
                            potential_monthly_savings=50.0,  # Estimated
                            priority="medium",
                            details={"state": instance.state}
                        )
                    )
                
                # Get metrics
                metrics = self.get_instance_metrics(instance.name)
                
                # Check for low connection count
                if metrics and metrics.avg_connections_30d < 1.0:
                    idle_count += 1
                    all_recommendations.append(
                        OptimizationRecommendation(
                            resource_type="cloud_sql",
                            resource_name=instance.name,
                            region=instance.region,
                            issue="Very low connection count (avg < 1)",
                            recommendation="Consider deleting or stopping this instance",
                            potential_monthly_savings=100.0,  # Estimated
                            priority="high",
                            details={"avg_connections_30d": metrics.avg_connections_30d}
                        )
                    )
                
                # Check for low CPU utilization
                if metrics and metrics.avg_cpu_utilization < 10.0:
                    over_provisioned_count += 1
                    all_recommendations.append(
                        OptimizationRecommendation(
                            resource_type="cloud_sql",
                            resource_name=instance.name,
                            region=instance.region,
                            issue=f"Low CPU utilization ({metrics.avg_cpu_utilization:.1f}%)",
                            recommendation="Consider downsizing to a smaller machine type",
                            potential_monthly_savings=50.0,  # Estimated
                            priority="medium",
                            details={
                                "current_tier": instance.tier,
                                "avg_cpu_utilization": metrics.avg_cpu_utilization
                            }
                        )
                    )
        
        except HttpError as e:
            if e.resp.status == 403:
                issues.append("Permission denied to list Cloud SQL instances")
            else:
                issues.append(f"HTTP Error auditing Cloud SQL: {str(e)}")
        except Exception as e:
            issues.append(f"Error auditing Cloud SQL: {str(e)}")
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="cloud_sql",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=over_provisioned_count,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_instances(self) -> List[CloudSQLInstance]:
        """List all Cloud SQL instances in the project.
        
        Returns:
            List of CloudSQLInstance objects
        """
        instances = []
        
        try:
            # Use Discovery API to list instances
            request = self.cloud_sql_client.instances().list(project=self.project_id)
            response = request.execute()
            
            if 'items' in response:
                for instance in response['items']:
                    # Get storage size
                    storage_gb = 10  # Default
                    if 'settings' in instance and 'dataDiskSizeGb' in instance['settings']:
                        storage_gb = int(instance['settings']['dataDiskSizeGb'])
                    
                    # Get tier/machine type
                    tier = "unknown"
                    if 'settings' in instance and 'tier' in instance['settings']:
                        tier = instance['settings']['tier']
                    
                    # Get labels
                    labels = {}
                    if 'settings' in instance and 'userLabels' in instance['settings']:
                        labels = instance['settings']['userLabels']
                    
                    instances.append(CloudSQLInstance(
                        name=instance.get('name', 'unknown'),
                        region=instance.get('region', 'unknown'),
                        database_version=instance.get('databaseVersion', 'unknown'),
                        tier=tier,
                        state=instance.get('state', 'UNKNOWN'),
                        labels=labels,
                        storage_gb=storage_gb,
                        created_time=None
                    ))
        
        except HttpError as e:
            if e.resp.status == 403:
                raise
        
        return instances
    
    def get_instance_metrics(
        self,
        instance_name: str,
        days: int = 30
    ) -> Optional[CloudSQLMetrics]:
        """Get metrics for a Cloud SQL instance.
        
        Args:
            instance_name: Instance name
            days: Number of days to look back
        
        Returns:
            CloudSQLMetrics object or None
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
            "avg_connections_30d": 0.0,
            "avg_cpu_utilization": 0.0,
            "avg_memory_utilization": 0.0,
            "query_count_30d": 0
        }
        
        # Get connection count
        try:
            connections = self._query_metric(
                "cloudsql.googleapis.com/database/network/connections",
                instance_name,
                interval,
                aggregation="mean"
            )
            metrics_data["avg_connections_30d"] = connections
        except Exception:
            pass
        
        # Get CPU utilization
        try:
            cpu = self._query_metric(
                "cloudsql.googleapis.com/database/cpu/utilization",
                instance_name,
                interval,
                aggregation="mean"
            )
            metrics_data["avg_cpu_utilization"] = cpu * 100  # Convert to percentage
        except Exception:
            pass
        
        # Get memory utilization
        try:
            memory = self._query_metric(
                "cloudsql.googleapis.com/database/memory/utilization",
                instance_name,
                interval,
                aggregation="mean"
            )
            metrics_data["avg_memory_utilization"] = memory * 100  # Convert to percentage
        except Exception:
            pass
        
        return CloudSQLMetrics(
            instance_name=instance_name,
            region="unknown",
            **metrics_data
        )
    
    def _query_metric(
        self,
        metric_type: str,
        instance_name: str,
        interval: monitoring_v3.TimeInterval,
        aggregation: str = "mean"
    ) -> float:
        """Query a metric from Cloud Monitoring."""
        filter_query = (
            f'resource.type="cloudsql_database" '
            f'AND resource.labels.database_id="{self.project_id}:{instance_name}" '
            f'AND metric.type="{metric_type}"'
        )
        
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

