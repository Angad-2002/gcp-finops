"""
Cloud Run specific audit example.

This script demonstrates how to audit only Cloud Run services.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gcp_finops_dashboard.gcp_client import GCPClient
from gcp_finops_dashboard.auditors import CloudRunAuditor


def main():
    """Run Cloud Run specific audit."""
    
    # Configuration
    PROJECT_ID = "your-project-id"  # Replace with your project ID
    REGIONS = ["us-central1", "us-east1", "europe-west1"]
    
    print("Cloud Run Audit\n")
    print(f"Project: {PROJECT_ID}")
    print(f"Regions: {', '.join(REGIONS)}\n")
    
    try:
        # Initialize GCP client
        print("Initializing GCP client...")
        gcp_client = GCPClient(project_id=PROJECT_ID)
        
        # Initialize Cloud Run auditor
        auditor = CloudRunAuditor(
            gcp_client.cloud_run,
            gcp_client.monitoring,
            PROJECT_ID
        )
        
        # Run audit
        print("Running Cloud Run audit...")
        result = auditor.audit_all_services(REGIONS)
        
        # Display results
        print("\n" + "="*80)
        print("CLOUD RUN AUDIT RESULTS")
        print("="*80 + "\n")
        
        print(f"Total services found: {result.total_count}")
        print(f"Untagged services: {result.untagged_count}")
        print(f"Idle services: {result.idle_count}")
        print(f"Over-provisioned services: {result.over_provisioned_count}")
        print(f"Potential monthly savings: ${result.potential_monthly_savings:,.2f}\n")
        
        # Display recommendations
        if result.recommendations:
            print("="*80)
            print("RECOMMENDATIONS")
            print("="*80 + "\n")
            
            for i, rec in enumerate(result.recommendations, 1):
                print(f"{i}. {rec.resource_name} ({rec.region})")
                print(f"   Priority: {rec.priority.upper()}")
                print(f"   Issue: {rec.issue}")
                print(f"   Recommendation: {rec.recommendation}")
                print(f"   Potential savings: ${rec.potential_monthly_savings:,.2f}/month")
                if rec.details:
                    print(f"   Details: {rec.details}")
                print()
        else:
            print("No recommendations - all Cloud Run services are optimized! 🎉\n")
        
        # Display issues (if any)
        if result.issues:
            print("="*80)
            print("ISSUES ENCOUNTERED")
            print("="*80 + "\n")
            for issue in result.issues:
                print(f"Warning: {issue}")
            print()
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

