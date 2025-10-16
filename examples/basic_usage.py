"""
Basic usage example for GCP FinOps Dashboard.

This script demonstrates how to use the GCP FinOps Dashboard programmatically.
"""

import os
import sys

# Add parent directory to path to import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gcp_finops_dashboard.dashboard_runner import DashboardRunner
from gcp_finops_dashboard.visualizations import DashboardVisualizer
from gcp_finops_dashboard.pdf_utils import ReportGenerator


def main():
    """Run basic dashboard example."""
    
    # Configuration
    PROJECT_ID = "your-project-id"  # Replace with your project ID
    BILLING_DATASET = "your-project.billing_export"  # Replace with your billing dataset
    REGIONS = ["us-central1", "us-east1"]
    
    print("🚀 Starting GCP FinOps Dashboard...\n")
    
    try:
        # Initialize dashboard runner
        runner = DashboardRunner(
            project_id=PROJECT_ID,
            billing_dataset=BILLING_DATASET,
            billing_table_prefix="gcp_billing_export_v1",
            regions=REGIONS
        )
        
        # Run complete analysis
        print("📊 Running cost and resource analysis...")
        data = runner.run()
        
        # Display dashboard in terminal
        print("\n" + "="*80)
        print("DASHBOARD RESULTS")
        print("="*80 + "\n")
        
        visualizer = DashboardVisualizer()
        visualizer.display_dashboard(data)
        
        # Generate PDF report
        print("\n📄 Generating PDF report...")
        report_gen = ReportGenerator(output_dir="./reports")
        report_path = report_gen.generate_report(data, "finops-report.pdf")
        print(f"✅ Report saved to: {report_path}")
        
        # Print summary statistics
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total monthly cost: ${data.current_month_cost:,.2f}")
        print(f"Total resources audited: {sum(r.total_count for r in data.audit_results.values())}")
        print(f"Total recommendations: {len(data.recommendations)}")
        print(f"Potential monthly savings: ${data.total_potential_savings:,.2f}")
        print(f"Potential yearly savings: ${data.total_potential_savings * 12:,.2f}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

