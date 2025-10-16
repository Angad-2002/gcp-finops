"""Compute Engine auditor."""

from typing import List, Optional
from google.cloud import compute_v1
from google.api_core import exceptions

from .types import ComputeInstance, OptimizationRecommendation, AuditResult


class ComputeAuditor:
    """Audit Compute Engine resources for cost optimization."""
    
    def __init__(
        self,
        instances_client: compute_v1.InstancesClient,
        project_id: str
    ):
        """Initialize Compute Engine auditor.
        
        Args:
            instances_client: Compute Engine instances client
            project_id: GCP project ID
        """
        self.instances_client = instances_client
        self.project_id = project_id
    
    def audit_all_instances(self, zones: Optional[List[str]] = None) -> AuditResult:
        """Audit all Compute Engine instances across zones.
        
        Args:
            zones: List of zones to audit
        
        Returns:
            AuditResult with findings and recommendations
        """
        if zones is None:
            # Use common zones
            zones = [
                "us-central1-a", "us-central1-b", "us-east1-b",
                "us-west1-a", "europe-west1-b", "asia-east1-a"
            ]
        
        all_recommendations = []
        total_count = 0
        untagged_count = 0
        idle_count = 0  # Stopped instances
        over_provisioned_count = 0
        issues = []
        
        for zone in zones:
            try:
                instances = self.list_instances(zone)
                total_count += len(instances)
                
                for instance in instances:
                    # Check for untagged instances
                    if not instance.labels:
                        untagged_count += 1
                    
                    # Check for stopped instances (still costing for attached disks)
                    if instance.status in ["STOPPED", "SUSPENDED", "TERMINATED"]:
                        idle_count += 1
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="compute_instance",
                                resource_name=instance.name,
                                region=zone,
                                issue=f"Instance is {instance.status} but still incurring storage costs",
                                recommendation="Delete instance if no longer needed, or start it if needed",
                                potential_monthly_savings=20.0,  # Estimated disk costs
                                priority="medium",
                                details={"status": instance.status}
                            )
                        )
                    
                    # Check for preemptible recommendation
                    if not instance.preemptible and instance.status == "RUNNING":
                        # For fault-tolerant workloads, recommend preemptible
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="compute_instance",
                                resource_name=instance.name,
                                region=zone,
                                issue="Non-preemptible instance running",
                                recommendation="Consider using preemptible VM for up to 80% savings (if workload allows)",
                                potential_monthly_savings=100.0,  # Estimated
                                priority="low",
                                details={
                                    "machine_type": instance.machine_type,
                                    "preemptible": False
                                }
                            )
                        )
            
            except exceptions.PermissionDenied:
                issues.append(f"Permission denied for zone {zone}")
            except Exception as e:
                issues.append(f"Error auditing zone {zone}: {str(e)}")
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="compute_engine",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=over_provisioned_count,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_instances(self, zone: str) -> List[ComputeInstance]:
        """List all Compute Engine instances in a zone.
        
        Args:
            zone: GCP zone
        
        Returns:
            List of ComputeInstance objects
        """
        instances = []
        
        try:
            for instance in self.instances_client.list(project=self.project_id, zone=zone):
                # Get machine type (last part of URL)
                machine_type = instance.machine_type.split("/")[-1] if instance.machine_type else "unknown"
                
                instances.append(ComputeInstance(
                    name=instance.name,
                    zone=zone,
                    machine_type=machine_type,
                    status=instance.status,
                    labels=dict(instance.labels) if instance.labels else {},
                    preemptible=instance.scheduling.preemptible if instance.scheduling else False,
                    created_time=None  # Parse instance.creation_timestamp if needed
                ))
        
        except exceptions.NotFound:
            pass
        except exceptions.PermissionDenied:
            raise
        
        return instances

