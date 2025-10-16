"""Command-line interface for GCP FinOps Dashboard."""

import sys
import argparse
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import requests
from packaging import version
from rich.console import Console

# Load environment variables from .env file
load_dotenv()

from .dashboard_runner import DashboardRunner
from .visualizations import DashboardVisualizer, print_progress, print_error
from .pdf_utils import ReportGenerator
from .helpers import get_project_id, load_config_file
from .forecast_service import ForecastService
from rich.table import Table

console = Console()
__version__ = "1.0.0"


def display_audit_results_table(audit_name: str, result: Any) -> None:
    """Display audit results in a formatted table.
    
    Args:
        audit_name: Name of the audit (e.g., 'Cloud Run', 'Compute Engine')
        result: AuditResult object with audit findings
    """
    # Create summary table
    table = Table(title=f"[bold cyan]{audit_name} Audit Summary[/]", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=25)
    table.add_column("Count", justify="right", style="green", width=15)
    
    # Add rows
    table.add_row("Total Resources", str(result.total_count))
    table.add_row("Untagged Resources", str(result.untagged_count))
    table.add_row("Idle Resources", str(result.idle_count))
    table.add_row("Over-provisioned", str(result.over_provisioned_count))
    table.add_section()
    table.add_row(
        "[bold]Potential Monthly Savings[/]", 
        f"[bold green]${result.potential_monthly_savings:,.2f}[/]"
    )
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def welcome_banner() -> None:
    """Display welcome banner."""
    # Only show banner if outputting to a real terminal (not piping)
    import sys
    if not sys.stdout.isatty():
        return
    
    banner = rf"""
[bold cyan]
   ██████   ██████ ██████      ███████ ██ ███    ██  ██████  ██████  ███████ 
  ██       ██      ██   ██     ██      ██ ████   ██ ██    ██ ██   ██ ██      
  ██   ███ ██      ██████      █████   ██ ██ ██  ██ ██    ██ ██████  ███████ 
  ██    ██ ██      ██          ██      ██ ██  ██ ██ ██    ██ ██           ██ 
   ██████   ██████ ██          ██      ██ ██   ████  ██████  ██      ███████ 
[/]
[bold bright_blue]GCP FinOps Dashboard CLI (v{__version__})[/]
[dim]Cloud Run, Serverless & Cost Optimization[/]                                                                       
"""
    console.print(banner)


def check_latest_version() -> None:
    """Check for the latest version of GCP FinOps Dashboard."""
    # Only check version if outputting to a real terminal (not piping)
    import sys
    if not sys.stdout.isatty():
        return
    
    try:
        response = requests.get(
            "https://pypi.org/pypi/gcp-finops-dashboard/json", timeout=3
        )
        latest = response.json()["info"]["version"]
        if version.parse(latest) > version.parse(__version__):
            console.print(
                f"[bold yellow]A new version of GCP FinOps Dashboard is available: {latest}[/]"
            )
            console.print(
                "[bold bright_cyan]Please update using:\npipx upgrade gcp-finops-dashboard\nor\npip install --upgrade gcp-finops-dashboard\n[/]"
            )
    except Exception:
        pass


def cli_main() -> int:
    """Command-line interface entry point for argparse-based CLI."""
    welcome_banner()
    check_latest_version()

    parser = argparse.ArgumentParser(
        description="GCP FinOps Dashboard CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete dashboard
  gcp-finops --billing-dataset my-project.billing_export
  
  # Generate PDF report
  gcp-finops --billing-dataset my-project.billing_export --report-type pdf
  
  # Run specific audit
  gcp-finops --billing-dataset my-project.billing_export --audit cloud-run
  
  # Use config file
  gcp-finops --config-file config.toml
        """
    )

    # Configuration
    parser.add_argument(
        "--config-file",
        "-C",
        help="Path to a TOML, YAML, or JSON configuration file",
        type=str,
    )

    # Project and billing options
    parser.add_argument(
        "--project-id",
        "-p",
        help="GCP project ID (defaults to gcloud config or GCP_PROJECT_ID env var)",
        type=str,
    )
    parser.add_argument(
        "--billing-dataset",
        "-b",
        help="BigQuery billing dataset (e.g., 'project.billing_export')",
        type=str,
    )
    parser.add_argument(
        "--billing-table-prefix",
        help="Billing table prefix (default: gcp_billing_export_v1)",
        type=str,
        default="gcp_billing_export_v1",
    )
    parser.add_argument(
        "--location",
        "-l",
        help="BigQuery location (default: US, e.g., 'asia-southeast1', 'europe-west1')",
        type=str,
        default="US",
    )

    # Region options
    parser.add_argument(
        "--regions",
        "-r",
        nargs="+",
        help="Regions to audit (space-separated, e.g., us-central1 us-east1)",
        type=str,
    )

    # Report options
    parser.add_argument(
        "--report-name",
        "-n",
        help="Specify the base name for the report file (without extension)",
        type=str,
        default="gcp-finops-report",
    )
    parser.add_argument(
        "--report-type",
        "-y",
        nargs="+",
        choices=["csv", "json", "pdf", "dashboard"],
        help="Report types: csv, json, pdf, or dashboard (space-separated, default: dashboard)",
        type=str,
        default=["dashboard"],
    )
    parser.add_argument(
        "--dir",
        "-d",
        help="Directory to save the report files (default: current directory)",
        type=str,
    )

    # Time range options
    parser.add_argument(
        "--time-range",
        "-t",
        help="Time range for cost data in days (default: current month). Examples: 7, 30, 90",
        type=int,
    )
    parser.add_argument(
        "--months-back",
        "-m",
        help="Number of months to look back for billing data (default: 2)",
        type=int,
        default=2,
    )

    # Filter options
    parser.add_argument(
        "--label",
        "-g",
        nargs="+",
        help="Filter by labels/tags, e.g., --label env=prod team=devops",
        type=str,
    )
    parser.add_argument(
        "--service",
        "-s",
        nargs="+",
        help="Filter by specific GCP services (e.g., cloud-run compute cloud-sql)",
        type=str,
    )

    # Mode options
    parser.add_argument(
        "--audit",
        "-a",
        help="Run specific audit: cloud-run, cloud-functions, compute, cloud-sql, storage, all",
        type=str,
        choices=["cloud-run", "cloud-functions", "compute", "cloud-sql", "storage", "all"],
    )
    parser.add_argument(
        "--trend",
        action="store_true",
        help="Display a trend report for the past 6 months",
    )
    parser.add_argument(
        "--forecast",
        action="store_true",
        help="Display cost forecast for next 30 days",
    )

    # API mode
    parser.add_argument(
        "--api",
        action="store_true",
        help="Start the API server instead of running CLI",
    )
    parser.add_argument(
        "--api-port",
        help="Port for API server (default: 8000)",
        type=int,
        default=8000,
    )
    
    # Security options
    parser.add_argument(
        "--hide-project-id",
        action="store_true",
        help="Hide project ID in output for security (useful for screenshots/demos)",
    )

    args = parser.parse_args()

    # Load config file if provided
    config_data: Optional[Dict[str, Any]] = None
    if args.config_file:
        config_data = load_config_file(args.config_file)
        if config_data is None:
            console.print("[bold red]Failed to load configuration file[/]")
            return 1

    # Override args with config_data if present and arg is not set via CLI
    if config_data:
        for key, value in config_data.items():
            # Convert kebab-case to snake_case for argument matching
            arg_key = key.replace("-", "_")
            if hasattr(args, arg_key) and getattr(args, arg_key) == parser.get_default(arg_key):
                setattr(args, arg_key, value)

    # Start API server if requested
    if args.api:
        from .api import start_api_server
        console.print(f"[bold green]Starting API server on port {args.api_port}...[/]")
        start_api_server(port=args.api_port)
        return 0

    # Validate required parameters
    if not args.billing_dataset:
        console.print(
            "[bold red]Error: --billing-dataset is required (or specify it in config file)[/]"
        )
        console.print("\nRun 'gcp-finops --help' for usage information")
        return 1

    # Get project ID
    project_id = args.project_id
    if not project_id:
        project_id = get_project_id()
        if not project_id:
            console.print(
                "[bold red]Error: Project ID not found. Please specify --project-id or set GCP_PROJECT_ID environment variable.[/]"
            )
            return 1

    # Parse regions
    region_list = None
    if args.regions:
        region_list = args.regions

    try:
        # Initialize runner
        console.print("[bold cyan]Initializing GCP FinOps Dashboard...[/]")
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=args.billing_dataset,
            billing_table_prefix=args.billing_table_prefix,
            regions=region_list,
            location=args.location,
            hide_project_id=args.hide_project_id,
        )

        # Run specific audit if requested
        if args.audit:
            console.print(f"[bold cyan]Running {args.audit} audit...[/]")
            if args.audit == "all":
                data = runner.run()
                visualizer = DashboardVisualizer()
                visualizer.display_dashboard(data)
            else:
                audit_type_map = {
                    "cloud-run": "cloud_run",
                    "cloud-functions": "cloud_functions",
                    "compute": "compute",
                    "cloud-sql": "cloud_sql",
                    "storage": "storage"
                }
                result = runner.run_specific_audit(audit_type_map[args.audit])
                if result:
                    visualizer = DashboardVisualizer()
                    # Display results in a formatted table
                    audit_display_name = args.audit.replace("-", " ").title()
                    display_audit_results_table(audit_display_name, result)
                    
                    if result.recommendations:
                        console.print("[bold cyan]💡 Optimization Recommendations[/]")
                        console.print()
                        visualizer.display_detailed_recommendations(result.recommendations)
            return 0

        # Handle forecast if requested
        if args.forecast:
            console.print("[bold cyan]Generating cost forecast...[/]")
            try:
                # Initialize forecast service
                forecast_service = ForecastService(
                    client=runner.gcp_client.bigquery,
                    billing_dataset=args.billing_dataset,
                    billing_table_prefix=args.billing_table_prefix
                )
                
                # Generate forecast
                print_progress("Training Prophet model and generating forecast...")
                forecast_data = forecast_service.forecast_costs(
                    forecast_days=90,  # Default to 90 days
                    historical_days=180,  # Use 6 months of historical data
                    project_id=project_id
                )
                print_progress("Forecast generated", done=True)
                
                # Display forecast
                visualizer = DashboardVisualizer()
                visualizer.display_forecast(forecast_data)
                
                return 0
                
            except Exception as e:
                console.print(f"[bold red]Forecast failed: {str(e)}[/]")
                return 1

        # Run analysis
        console.print("[bold cyan]Analyzing GCP resources and costs...[/]")
        data = runner.run()

        # Generate reports based on type
        for report_type in args.report_type:
            if report_type == "dashboard":
                visualizer = DashboardVisualizer()
                visualizer.display_dashboard(data)
            elif report_type == "pdf":
                print_progress("Generating PDF report...")
                report_gen = ReportGenerator()
                # Add .pdf extension to the report name
                pdf_filename = f"{args.report_name}.pdf"
                output_name = pdf_filename if args.dir is None else f"{args.dir}/{pdf_filename}"
                output_path = report_gen.generate_report(data, output_name)
                print_progress(f"Report saved to: {output_path}", done=True)
            elif report_type in ["csv", "json"]:
                console.print(f"[bold yellow]{report_type.upper()} export not yet implemented[/]")

        return 0

    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/]")
        import traceback
        console.print(traceback.format_exc())
        return 1


# Keep the click-based commands for backward compatibility
import click


@click.group()
def main() -> None:
    """GCP FinOps Dashboard - Cloud Run and serverless cost optimization."""
    pass


@main.command()
@click.option(
    "--project-id",
    type=str,
    help="GCP project ID (defaults to gcloud config)"
)
@click.option(
    "--billing-dataset",
    type=str,
    required=True,
    help="BigQuery billing dataset (e.g., 'project.billing_export')"
)
@click.option(
    "--billing-table-prefix",
    type=str,
    default="gcp_billing_export_v1",
    help="Billing table prefix (default: gcp_billing_export_v1)"
)
@click.option(
    "--regions",
    type=str,
    help="Comma-separated list of regions to audit (e.g., 'us-central1,us-east1')"
)
@click.option(
    "--location",
    type=str,
    default="US",
    help="BigQuery location (default: US, e.g., 'asia-southeast1', 'europe-west1')"
)
@click.option(
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)"
)
def dashboard(
    project_id: Optional[str],
    billing_dataset: str,
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    hide_project_id: bool
) -> None:
    """Run the complete FinOps dashboard."""
    # Get project ID
    if not project_id:
        project_id = get_project_id()
        if not project_id:
            print_error(
                "Project ID not found. Please specify --project-id or set GCP_PROJECT_ID environment variable."
            )
            raise click.Abort()
    
    # Parse regions
    region_list = None
    if regions:
        region_list = [r.strip() for r in regions.split(",")]
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix=billing_table_prefix,
            regions=region_list,
            location=location,
            hide_project_id=hide_project_id
        )
        
        # Run analysis
        data = runner.run()
        
        # Display dashboard
        visualizer = DashboardVisualizer()
        visualizer.display_dashboard(data)
    
    except Exception as e:
        print_error(f"Dashboard failed: {str(e)}")
        raise click.Abort()


@main.command()
@click.option(
    "--project-id",
    type=str,
    help="GCP project ID (defaults to gcloud config)"
)
@click.option(
    "--billing-dataset",
    type=str,
    required=True,
    help="BigQuery billing dataset (e.g., 'project.billing_export')"
)
@click.option(
    "--billing-table-prefix",
    type=str,
    default="gcp_billing_export_v1",
    help="Billing table prefix"
)
@click.option(
    "--regions",
    type=str,
    help="Comma-separated list of regions to audit"
)
@click.option(
    "--location",
    type=str,
    default="US",
    help="BigQuery location (default: US, e.g., 'asia-southeast1', 'europe-west1')"
)
@click.option(
    "--output",
    type=str,
    default="gcp-finops-report.pdf",
    help="Output PDF filename (default: gcp-finops-report.pdf)"
)
@click.option(
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)"
)
def report(
    project_id: Optional[str],
    billing_dataset: str,
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    output: str,
    hide_project_id: bool
) -> None:
    """Generate a PDF report."""
    # Get project ID
    if not project_id:
        project_id = get_project_id()
        if not project_id:
            print_error(
                "Project ID not found. Please specify --project-id or set GCP_PROJECT_ID environment variable."
            )
            raise click.Abort()
    
    # Parse regions
    region_list = None
    if regions:
        region_list = [r.strip() for r in regions.split(",")]
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix=billing_table_prefix,
            regions=region_list,
            location=location,
            hide_project_id=hide_project_id
        )
        
        # Run analysis
        data = runner.run()
        
        # Generate report
        print_progress("Generating PDF report...")
        report_gen = ReportGenerator()
        output_path = report_gen.generate_report(data, output)
        print_progress(f"Report saved to: {output_path}", done=True)
    
    except Exception as e:
        print_error(f"Report generation failed: {str(e)}")
        raise click.Abort()


@main.command()
@click.argument(
    "audit_type",
    type=click.Choice([
        "cloud-run",
        "cloud-functions",
        "compute",
        "cloud-sql",
        "disks",
        "ips",
        "all"
    ])
)
@click.option(
    "--project-id",
    type=str,
    help="GCP project ID (defaults to gcloud config)"
)
@click.option(
    "--billing-dataset",
    type=str,
    required=True,
    help="BigQuery billing dataset"
)
@click.option(
    "--regions",
    type=str,
    help="Comma-separated list of regions to audit"
)
@click.option(
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)"
)
def audit(
    audit_type: str,
    project_id: Optional[str],
    billing_dataset: str,
    regions: Optional[str],
    hide_project_id: bool
) -> None:
    """Run a specific resource audit."""
    # Get project ID
    if not project_id:
        project_id = get_project_id()
        if not project_id:
            print_error(
                "Project ID not found. Please specify --project-id or set GCP_PROJECT_ID environment variable."
            )
            raise click.Abort()
    
    # Parse regions
    region_list = None
    if regions:
        region_list = [r.strip() for r in regions.split(",")]
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            regions=region_list,
            hide_project_id=hide_project_id
        )
        
        if audit_type == "all":
            # Run complete dashboard
            data = runner.run()
            visualizer = DashboardVisualizer()
            visualizer.display_dashboard(data)
        else:
            # Run specific audit
            audit_type_map = {
                "cloud-run": "cloud_run",
                "cloud-functions": "cloud_functions",
                "compute": "compute",
                "cloud-sql": "cloud_sql",
                "disks": "disks",
                "ips": "ips"
            }
            
            result = runner.run_specific_audit(audit_type_map[audit_type])
            
            if result:
                # Display results in a formatted table
                visualizer = DashboardVisualizer()
                audit_display_name = audit_type.replace("-", " ").title()
                display_audit_results_table(audit_display_name, result)
                
                if result.recommendations:
                    console.print("[bold cyan]💡 Optimization Recommendations[/]")
                    console.print()
                    visualizer.display_detailed_recommendations(result.recommendations)
    
    except Exception as e:
        print_error(f"Audit failed: {str(e)}")
        raise click.Abort()


@main.command()
def setup() -> None:
    """Show setup instructions."""
    instructions = """
    GCP FinOps Dashboard Setup Instructions
    ========================================
    
    1. Enable Required APIs:
    
       gcloud services enable \\
           cloudbilling.googleapis.com \\
           bigquery.googleapis.com \\
           run.googleapis.com \\
           cloudfunctions.googleapis.com \\
           compute.googleapis.com \\
           sqladmin.googleapis.com \\
           cloudresourcemanager.googleapis.com \\
           monitoring.googleapis.com
    
    2. Set up BigQuery Billing Export:
    
       - Go to: https://console.cloud.google.com/billing/export
       - Enable "BigQuery Export"
       - Note your dataset name (e.g., 'billing_export')
       - Wait 24 hours for data to populate
    
    3. Authenticate:
    
       gcloud auth application-default login
    
    4. Set project (optional):
    
       gcloud config set project YOUR_PROJECT_ID
       # OR set environment variable:
       export GCP_PROJECT_ID=YOUR_PROJECT_ID
    
    5. Run dashboard:
    
       gcp-finops dashboard \\
           --billing-dataset YOUR_PROJECT.billing_export \\
           --regions us-central1,us-east1
    
    For more information, see: https://github.com/your-repo/gcp-finops-dashboard
    """
    
    click.echo(instructions)


if __name__ == "__main__":
    # Use argparse-based CLI as default
    sys.exit(cli_main())

