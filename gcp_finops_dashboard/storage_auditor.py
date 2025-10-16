"""Storage and networking auditor."""

from typing import List, Optional
from google.cloud import compute_v1
from google.api_core import exceptions

from .types import PersistentDisk, StaticIPAddress, OptimizationRecommendation, AuditResult


class StorageAuditor:
    """Audit storage and networking resources for cost optimization."""
    
    def __init__(
        self,
        disks_client: compute_v1.DisksClient,
        addresses_client: compute_v1.AddressesClient,
        project_id: str
    ):
        """Initialize storage auditor.
        
        Args:
            disks_client: Compute Engine disks client
            addresses_client: Compute Engine addresses client
            project_id: GCP project ID
        """
        self.disks_client = disks_client
        self.addresses_client = addresses_client
        self.project_id = project_id
    
    def audit_disks(self, zones: Optional[List[str]] = None) -> AuditResult:
        """Audit persistent disks for unattached volumes.
        
        Args:
            zones: List of zones to audit
        
        Returns:
            AuditResult with findings and recommendations
        """
        if zones is None:
            zones = [
                "us-central1-a", "us-central1-b", "us-east1-b",
                "us-west1-a", "europe-west1-b", "asia-east1-a"
            ]
        
        all_recommendations = []
        total_count = 0
        untagged_count = 0
        idle_count = 0  # Unattached disks
        issues = []
        
        for zone in zones:
            try:
                disks = self.list_disks(zone)
                total_count += len(disks)
                
                for disk in disks:
                    # Check for untagged disks
                    if not disk.labels:
                        untagged_count += 1
                    
                    # Check for unattached disks
                    if not disk.in_use:
                        idle_count += 1
                        # Estimate cost: ~$0.04/GB/month for standard disks
                        monthly_cost = disk.size_gb * 0.04
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="persistent_disk",
                                resource_name=disk.name,
                                region=zone,
                                issue="Unattached disk incurring storage costs",
                                recommendation="Delete if no longer needed, or create snapshot and delete",
                                potential_monthly_savings=monthly_cost,
                                priority="high",
                                details={
                                    "size_gb": disk.size_gb,
                                    "disk_type": disk.disk_type,
                                    "in_use": False
                                }
                            )
                        )
            
            except exceptions.PermissionDenied:
                issues.append(f"Permission denied for zone {zone}")
            except Exception as e:
                issues.append(f"Error auditing disks in zone {zone}: {str(e)}")
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="persistent_disks",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=0,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def audit_static_ips(self, regions: Optional[List[str]] = None) -> AuditResult:
        """Audit static IP addresses for unused IPs.
        
        Args:
            regions: List of regions to audit
        
        Returns:
            AuditResult with findings and recommendations
        """
        if regions is None:
            regions = ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]
        
        all_recommendations = []
        total_count = 0
        idle_count = 0  # Unused IPs
        issues = []
        
        for region in regions:
            try:
                addresses = self.list_static_ips(region)
                total_count += len(addresses)
                
                for address in addresses:
                    # Check for unused IPs
                    if not address.in_use:
                        idle_count += 1
                        # Unused external IPs cost ~$7/month
                        monthly_cost = 7.0 if address.address_type == "EXTERNAL" else 0.0
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="static_ip",
                                resource_name=address.name,
                                region=region,
                                issue="Unused static IP incurring charges",
                                recommendation="Release if no longer needed",
                                potential_monthly_savings=monthly_cost,
                                priority="medium",
                                details={
                                    "address": address.address,
                                    "address_type": address.address_type,
                                    "in_use": False
                                }
                            )
                        )
            
            except exceptions.PermissionDenied:
                issues.append(f"Permission denied for region {region}")
            except Exception as e:
                issues.append(f"Error auditing IPs in region {region}: {str(e)}")
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="static_ips",
            total_count=total_count,
            untagged_count=0,
            idle_count=idle_count,
            over_provisioned_count=0,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_disks(self, zone: str) -> List[PersistentDisk]:
        """List all persistent disks in a zone.
        
        Args:
            zone: GCP zone
        
        Returns:
            List of PersistentDisk objects
        """
        disks = []
        
        try:
            for disk in self.disks_client.list(project=self.project_id, zone=zone):
                # Disk type (last part of URL)
                disk_type = disk.type.split("/")[-1] if disk.type else "unknown"
                
                # Check if disk is attached to any instance
                in_use = bool(disk.users)
                
                disks.append(PersistentDisk(
                    name=disk.name,
                    zone=zone,
                    size_gb=disk.size_gb if disk.size_gb else 0,
                    disk_type=disk_type,
                    status=disk.status,
                    in_use=in_use,
                    labels=dict(disk.labels) if disk.labels else {},
                    created_time=None
                ))
        
        except exceptions.NotFound:
            pass
        except exceptions.PermissionDenied:
            raise
        
        return disks
    
    def list_static_ips(self, region: str) -> List[StaticIPAddress]:
        """List all static IP addresses in a region.
        
        Args:
            region: GCP region
        
        Returns:
            List of StaticIPAddress objects
        """
        addresses = []
        
        try:
            for address in self.addresses_client.list(project=self.project_id, region=region):
                # Check if IP is in use (attached to an instance/service)
                in_use = bool(address.users)
                
                addresses.append(StaticIPAddress(
                    name=address.name,
                    region=region,
                    address=address.address if address.address else "unknown",
                    address_type=address.address_type,
                    status=address.status,
                    in_use=in_use,
                    created_time=None
                ))
        
        except exceptions.NotFound:
            pass
        except exceptions.PermissionDenied:
            raise
        
        return addresses

