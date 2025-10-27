"""Command-line interface for GCP FinOps Dashboard."""

import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import requests
from packaging import version
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
import click
import pyfiglet
import toml

# Load environment variables from .env file
load_dotenv()

from .dashboard_runner import DashboardRunner
from .visualizations import DashboardVisualizer, print_progress, print_error


def format_ai_response(question: str, answer: str, provider: str = "", model: str = "") -> None:
    """Format AI response with rich styling and markdown support."""
    from datetime import datetime
    
    # Create timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Create question panel using color scheme
    question_panel = Panel(
        Text(question, style="bold white"),
        title=f"[bold {get_color('secondary')}]🤔 Your Question[/]",
        title_align="left",
        border_style=get_color('secondary'),
        padding=(0, 1)
    )
    
    # Create answer panel with markdown support using color scheme
    try:
        # Try to render as markdown first
        markdown_content = Markdown(answer)
        answer_panel = Panel(
            markdown_content,
            title=f"[bold {get_color('success')}]🤖 AI Assistant[/]",
            title_align="left",
            border_style=get_color('success'),
            padding=(0, 1)
        )
    except Exception:
        # Fallback to plain text if markdown fails
        answer_panel = Panel(
            Text(answer, style="white"),
            title=f"[bold {get_color('success')}]🤖 AI Assistant[/]",
            title_align="left",
            border_style=get_color('success'),
            padding=(0, 1)
        )
    
    # Create metadata panel
    metadata_text = f"Time: {timestamp}"
    if provider:
        metadata_text += f" | Provider: {provider}"
    if model:
        metadata_text += f" | Model: {model}"
    
    metadata_panel = Panel(
        Text(metadata_text, style=get_color('muted')),
        border_style=get_color('muted'),
        padding=(0, 1)
    )
    
    # Display all panels
    console.print()
    console.print(question_panel)
    console.print()
    console.print(answer_panel)
    console.print()
    console.print(metadata_panel)
    console.print()


def show_enhanced_progress(message: str, done: bool = False, spinner: str = "dots") -> None:
    """Show enhanced progress with spinner and better styling using color scheme."""
    if done:
        console.print(f"[{get_color('success')}]✓[/] [bold]{message}[/]")
    else:
        # Create a simple spinner effect
        spinner_chars = {
            "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
            "line": ["|", "/", "-", "\\"],
            "bounce": ["⠁", "⠂", "⠄", "⠂"]
        }
        
        import time
        import threading
        
        def spinner_animation():
            chars = spinner_chars.get(spinner, spinner_chars["dots"])
            i = 0
            while not getattr(spinner_animation, 'stop', False):
                console.print(f"\r[{get_color('info')}]{chars[i % len(chars)]}[/] {message}", end="")
                i += 1
                time.sleep(0.1)
        
        # For now, just show a simple progress message
        console.print(f"[{get_color('info')}]⋯[/] {message}")


def create_chat_header() -> None:
    """Create a styled chat header using color scheme."""
    header_panel = Panel(
        Align.center(
            Text.assemble(
                f"[bold {get_color('secondary')}]💬 AI Chat Mode[/]", "\n",
                f"[{get_color('muted')}]Ask questions about your GCP costs and resources[/]"
            )
        ),
        border_style=get_color('primary'),
        padding=(0, 1),
        title="[bold white]GCP FinOps AI Assistant[/]",
        title_align="center"
    )
    console.print(header_panel)
    console.print()


from .pdf_utils import ReportGenerator
from .helpers import get_project_id, load_config_file
from .forecast_service import ForecastService
from .llm_service import LLMService, get_llm_service


# Color scheme configuration
COLOR_SCHEME = {
    "primary": "bright_blue",
    "secondary": "cyan", 
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
    "muted": "dim",
    "accent": "bright_cyan",
    "highlight": "bright_green"
}

def get_color(color_name: str) -> str:
    """Get color from the color scheme."""
    return COLOR_SCHEME.get(color_name, "white")

# Import InquirerPy for interactive CLI
try:
    from InquirerPy import inquirer
    from InquirerPy.validator import EmptyInputValidator
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False
from rich.table import Table

console = Console()
__version__ = "1.0.0"


def get_ascii_art_config(config_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Get ASCII art configuration with defaults."""
    ascii_config = {}
    if config_data and "ascii-art" in config_data:
        ascii_config = config_data["ascii-art"]
    
    return {
        "font": ascii_config.get("font", "slant"),
        "enable_animations": ascii_config.get("enable-animations", False),
        "animation_speed": ascii_config.get("animation-speed", "normal"),
        "animation_width": ascii_config.get("animation-width", 100),
        "animation_loops": ascii_config.get("animation-loops", 3)
    }

# Reports directory configuration - same as API
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


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


# Click-based CLI implementation

def welcome_banner(config_data: Optional[Dict[str, Any]] = None) -> None:
    """Display enhanced welcome banner with ASCII art and rich styling."""
    # Only show banner if outputting to a real terminal (not piping)
    import sys
    if not sys.stdout.isatty():
        return
    
    # Get ASCII art configuration
    ascii_config = get_ascii_art_config(config_data)
    font = ascii_config["font"]
    enable_animations = ascii_config["enable_animations"]
    
    try:
        # Create ASCII art with pyfiglet
        f = pyfiglet.Figlet(font=font)
        ascii_art = f.renderText('Google FinOps')
        
        # Create enhanced banner with panels using color scheme
        banner_text = Text(ascii_art, style=f"bold {get_color('highlight')}")
        version_text = Text(f"Google FinOps Dashboard CLI (v{__version__})", style=f"bold {get_color('accent')}")
        tagline_text = Text("Cloud Run, Serverless & Cost Optimization", style=f"{get_color('muted')} italic")
        
        # Create a panel with the banner
        banner_panel = Panel(
            Align.center(
                Text.assemble(
                    banner_text, "\n",
                    version_text, "\n",
                    tagline_text
                )
            ),
            border_style=get_color('primary'),
            padding=(1, 2),
            title="[bold white]Welcome to Google FinOps Dashboard[/]",
            title_align="center"
        )
        
        console.print(banner_panel)
        console.print()
        
        # Show ASCII animation if enabled
        if enable_animations:
            try:
                import subprocess
                animation_speed = ascii_config.get("animation-speed", "normal")
                animation_width = ascii_config.get("animation-width", 100)
                animation_loops = ascii_config.get("animation-loops", 3)
                
                # Check if ascii-animator is available
                result = subprocess.run(['ascii-art-animator', '--help'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    console.print("[dim]ASCII Animation available (install ascii-animator for animations)[/]")
            except (ImportError, FileNotFoundError):
                console.print("[dim]Install 'ascii-animator' for ASCII animations[/]")
                
    except Exception as e:
        # Fallback to simple text if pyfiglet fails
        fallback_panel = Panel(
            Align.center(
                Text.assemble(
                    f"Google FinOps Dashboard CLI (v{__version__})", "\n",
                    "Cloud Run, Serverless & Cost Optimization"
                )
            ),
            border_style=get_color('primary'),
            padding=(1, 2),
            title="[bold white]Welcome to Google FinOps Dashboard[/]",
            title_align="center"
        )
        console.print(fallback_panel)
        console.print(f"[dim]ASCII art disabled: {str(e)}[/]")


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


def _ensure_banner_displayed(ctx: click.Context) -> None:
    """Ensure banner is displayed only once per command execution."""
    if not hasattr(ctx, '_banner_displayed'):
        config_data = ctx.obj.get('config_data') if ctx.obj else None
        welcome_banner(config_data)
        check_latest_version()
        ctx._banner_displayed = True


def with_heading(func):
    """Decorator to ensure ASCII art heading is displayed for all commands."""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Find the click context in the arguments
        ctx = None
        for arg in args:
            if hasattr(arg, 'obj') and hasattr(arg, 'invoked_subcommand'):
                ctx = arg
                break
        
        # Display banner if context is available
        if ctx:
            _ensure_banner_displayed(ctx)
        else:
            # Fallback: display banner without context
            welcome_banner()
            check_latest_version()
        
        return func(*args, **kwargs)
    return wrapper


@click.group(invoke_without_command=True)
@click.option(
    "--config-file",
    "-C",
    type=str,
    help="Path to a TOML, YAML, or JSON configuration file"
)
@click.pass_context
def main(ctx: click.Context, config_file: Optional[str]) -> None:
    """GCP FinOps Dashboard - Cloud Run and serverless cost optimization."""
    # Load config file if provided
    config_data: Optional[Dict[str, Any]] = None
    if config_file:
        config_data = load_config_file(config_file)
        if config_data is None:
            print_error("Failed to load configuration file")
            raise click.Abort()
    
    # Store config in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['config_data'] = config_data
    
    # If no subcommand was invoked, show help
    if ctx.invoked_subcommand is None:
        # Show banner and version check only when no subcommand is invoked
        welcome_banner(config_data)
        check_latest_version()
        click.echo(ctx.get_help())


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
@click.pass_context
@with_heading
def dashboard(
    ctx: click.Context,
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
@click.pass_context
@with_heading
def report(
    ctx: click.Context,
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
        # Use reports directory by default, but allow override with --output
        if output == "gcp-finops-report.pdf":
            # Default filename - use reports directory with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            pdf_filename = f"gcp-finops-report-{timestamp}.pdf"
            output_path = REPORTS_DIR / pdf_filename
            report_gen = ReportGenerator(output_dir=str(REPORTS_DIR))
        else:
            # Custom filename - use current directory or specified path
            output_path = Path(output)
            report_gen = ReportGenerator(output_dir=str(output_path.parent))
        
        report_gen.generate_report(data, str(output_path))
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
@click.pass_context
@with_heading
def audit(
    ctx: click.Context,
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
                    console.print("[bold cyan]Optimization Recommendations[/]")
                    console.print()
                    visualizer.display_detailed_recommendations(result.recommendations)
    
    except Exception as e:
        print_error(f"Audit failed: {str(e)}")
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
    help="Billing table prefix (default: gcp_billing_export_v1)"
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
    "--forecast-days",
    type=int,
    default=90,
    help="Number of days to forecast (default: 90)"
)
@click.option(
    "--historical-days",
    type=int,
    default=180,
    help="Number of days of historical data to use (default: 180)"
)
@click.option(
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)"
)
@with_heading
def forecast(
    project_id: Optional[str],
    billing_dataset: str,
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    forecast_days: int,
    historical_days: int,
    hide_project_id: bool
) -> None:
    """Generate cost forecast for the next N days."""
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
        # Initialize runner to get GCP client
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix=billing_table_prefix,
            regions=region_list,
            location=location,
            hide_project_id=hide_project_id
        )
        
        # Initialize forecast service
        forecast_service = ForecastService(
            client=runner.gcp_client.bigquery,
            billing_dataset=billing_dataset,
            billing_table_prefix=billing_table_prefix
        )
        
        # Generate forecast
        print_progress("Training Prophet model and generating forecast...")
        forecast_data = forecast_service.forecast_costs(
            forecast_days=forecast_days,
            historical_days=historical_days,
            project_id=project_id
        )
        print_progress("Forecast generated", done=True)
        
        # Display forecast
        visualizer = DashboardVisualizer()
        visualizer.display_forecast(forecast_data)
    
    except Exception as e:
        print_error(f"Forecast failed: {str(e)}")
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
    help="Billing table prefix (default: gcp_billing_export_v1)"
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
    "--time-range",
    type=int,
    help="Time range for cost data in days (default: current month). Examples: 7, 30, 90"
)
@click.option(
    "--months-back",
    type=int,
    default=2,
    help="Number of months to look back for billing data (default: 2)"
)
@click.option(
    "--label",
    multiple=True,
    help="Filter by labels/tags, e.g., --label env=prod --label team=devops"
)
@click.option(
    "--service",
    multiple=True,
    help="Filter by specific GCP services (e.g., --service cloud-run --service compute)"
)
@click.option(
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)"
)
@with_heading
def trend(
    project_id: Optional[str],
    billing_dataset: str,
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    time_range: Optional[int],
    months_back: int,
    label: tuple,
    service: tuple,
    hide_project_id: bool
) -> None:
    """Display a trend report for the past 6 months."""
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
    
    # Parse labels
    label_filters = None
    if label:
        label_filters = list(label)
    
    # Parse services
    service_filters = None
    if service:
        service_filters = list(service)
    
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
        
        # Run trend analysis
        console.print("[bold cyan]Generating trend report for the past 6 months...[/]")
        data = runner.run()
        
        # Display trend dashboard
        visualizer = DashboardVisualizer()
        visualizer.display_dashboard(data)
    
    except Exception as e:
        print_error(f"Trend analysis failed: {str(e)}")
        raise click.Abort()


@main.command()
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port for API server (default: 8000)"
)
def api(port: int) -> None:
    """Start the API server."""
    try:
        from .api import start_api_server
        console.print(f"[bold green]Starting API server on port {port}...[/]")
        start_api_server(port=port)
    except Exception as e:
        print_error(f"API server failed to start: {str(e)}")
        raise click.Abort()


@main.command()
@click.option(
    "--project-id",
    "-p",
    type=str,
    help="GCP project ID (defaults to gcloud config or GCP_PROJECT_ID env var)"
)
@click.option(
    "--billing-dataset",
    "-b",
    type=str,
    help="BigQuery billing dataset (e.g., 'project.billing_export')"
)
@click.option(
    "--billing-table-prefix",
    type=str,
    default="gcp_billing_export_v1",
    help="Billing table prefix (default: gcp_billing_export_v1)"
)
@click.option(
    "--location",
    "-l",
    type=str,
    default="US",
    help="BigQuery location (default: US, e.g., 'asia-southeast1', 'europe-west1')"
)
@click.option(
    "--regions",
    "-r",
    type=str,
    help="Regions to audit (comma-separated, e.g., us-central1,us-east1)"
)
@click.option(
    "--report-name",
    "-n",
    type=str,
    default="gcp-finops-report",
    help="Specify the base name for the report file (without extension)"
)
@click.option(
    "--report-type",
    "-y",
    multiple=True,
    type=click.Choice(["csv", "json", "pdf", "dashboard"]),
    default=["dashboard"],
    help="Report types: csv, json, pdf, or dashboard (can be specified multiple times)"
)
@click.option(
    "--dir",
    "-d",
    type=str,
    help="Directory to save the report files (default: reports directory)"
)
@click.option(
    "--time-range",
    "-t",
    type=int,
    help="Time range for cost data in days (default: current month). Examples: 7, 30, 90"
)
@click.option(
    "--months-back",
    "-m",
    type=int,
    default=2,
    help="Number of months to look back for billing data (default: 2)"
)
@click.option(
    "--label",
    "-g",
    multiple=True,
    help="Filter by labels/tags, e.g., --label env=prod --label team=devops"
)
@click.option(
    "--service",
    "-s",
    multiple=True,
    help="Filter by specific GCP services (e.g., --service cloud-run --service compute)"
)
@click.option(
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)"
)
@click.pass_context
def run(
    ctx: click.Context,
    project_id: Optional[str],
    billing_dataset: Optional[str],
    billing_table_prefix: str,
    location: str,
    regions: Optional[str],
    report_name: str,
    report_type: tuple,
    dir: Optional[str],
    time_range: Optional[int],
    months_back: int,
    label: tuple,
    service: tuple,
    hide_project_id: bool
) -> None:
    """Run the complete FinOps analysis with config file support and multiple report types."""
    # Get config data from context
    config_data = ctx.obj.get('config_data')
    
    # Override CLI args with config data if not provided via CLI
    if config_data:
        if not project_id and "project_id" in config_data:
            project_id = config_data["project_id"]
        if not billing_dataset and "billing_dataset" in config_data:
            billing_dataset = config_data["billing_dataset"]
        if not regions and "regions" in config_data:
            regions = ",".join(config_data["regions"]) if isinstance(config_data["regions"], list) else config_data["regions"]
        if not dir and "dir" in config_data:
            dir = config_data["dir"]
        if not time_range and "time_range" in config_data:
            time_range = config_data["time_range"]
        if months_back == 2 and "months_back" in config_data:
            months_back = config_data["months_back"]
        if not hide_project_id and "hide_project_id" in config_data:
            hide_project_id = config_data["hide_project_id"]
    
    # Validate required parameters
    if not billing_dataset:
        print_error("--billing-dataset is required (or specify it in config file)")
        raise click.Abort()
    
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
    
    # Parse labels
    label_filters = None
    if label:
        label_filters = list(label)
    
    # Parse services
    service_filters = None
    if service:
        service_filters = list(service)
    
    try:
        # Initialize runner
        console.print("[bold cyan]Initializing GCP FinOps Dashboard...[/]")
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix=billing_table_prefix,
            regions=region_list,
            location=location,
            hide_project_id=hide_project_id
        )
        
        # Run analysis
        console.print("[bold cyan]Analyzing GCP resources and costs...[/]")
        data = runner.run()
        
        # Generate reports based on type
        for report_type_item in report_type:
            if report_type_item == "dashboard":
                visualizer = DashboardVisualizer()
                visualizer.display_dashboard(data)
            elif report_type_item == "pdf":
                print_progress("Generating PDF report...")
                # Use reports directory by default, but allow override with --dir
                if dir is None:
                    # Use the reports directory and generate filename with timestamp
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    pdf_filename = f"{report_name}-{timestamp}.pdf"
                    output_path = REPORTS_DIR / pdf_filename
                    report_gen = ReportGenerator(output_dir=str(REPORTS_DIR))
                else:
                    # Use custom directory if specified
                    pdf_filename = f"{report_name}.pdf"
                    output_path = Path(dir) / pdf_filename
                    report_gen = ReportGenerator(output_dir=dir)
                
                report_gen.generate_report(data, str(output_path))
                print_progress(f"Report saved to: {output_path}", done=True)
            elif report_type_item in ["csv", "json"]:
                console.print(f"[bold yellow]{report_type_item.upper()} export not yet implemented[/]")
    
    except Exception as e:
        print_error(f"Analysis failed: {str(e)}")
        raise click.Abort()


# ============================================================================
# AI CONFIGURATION COMMANDS
# ============================================================================

@main.group()
def config() -> None:
    """Configuration management for GCP FinOps Dashboard."""
    pass


@config.command()
@click.option(
    "--provider",
    type=click.Choice(["groq", "openai", "anthropic"]),
    help="AI provider to use"
)
@click.option(
    "--api-key",
    type=str,
    help="API key for the selected AI provider"
)
@click.option(
    "--model",
    type=str,
    help="AI model to use"
)
@click.option(
    "--show",
    is_flag=True,
    help="Show current configuration"
)
@click.option(
    "--interactive",
    is_flag=True,
    help="Use interactive mode with dropdowns"
)
def ai(provider: Optional[str], api_key: Optional[str], model: Optional[str], show: bool, interactive: bool) -> None:
    """Configure AI settings for GCP FinOps Dashboard."""
    
    if show:
        # Show current configuration
        current_provider = os.getenv("AI_PROVIDER") or LLMService.DEFAULT_PROVIDER
        current_model = os.getenv("AI_MODEL") or LLMService.DEFAULT_MODEL
        
        # Get current API key based on provider
        current_api_key = None
        if current_provider == "groq":
            current_api_key = os.getenv("GROQ_API_KEY")
        elif current_provider == "openai":
            current_api_key = os.getenv("OPENAI_API_KEY")
        elif current_provider == "anthropic":
            current_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        console.print("[bold cyan]Current AI Configuration:[/]")
        console.print(f"Provider: [green]{current_provider}[/]")
        console.print(f"API Key: {'***' + current_api_key[-4:] if current_api_key else '[red]Not set[/]'}")
        console.print(f"Model: [green]{current_model}[/]")
        
        # Show available providers and models
        console.print("\n[bold cyan]Available Providers:[/]")
        providers = LLMService.get_available_providers()
        for prov_id, prov_info in providers.items():
            status = "[green][OK] Available[/]" if prov_info["available"] else "[red][X] Not installed[/]"
            console.print(f"  [cyan]{prov_id}[/]: {prov_info['name']} - {prov_info['description']} {status}")
            
            if prov_info["available"]:
                console.print("    Models:")
                for model_id, model_info in prov_info["models"].items():
                    recommended = " [bold green](recommended)[/]" if model_info.get("recommended") else ""
                    console.print(f"      [dim]{model_id}[/]: {model_info['name']}{recommended}")
        
        return
    
    if interactive and INQUIRER_AVAILABLE:
        # Interactive mode with dropdowns
        console.print("[bold cyan]Interactive AI Configuration[/]")
        console.print()
        
        # Select provider
        available_providers = []
        providers = LLMService.get_available_providers()
        for prov_id, prov_info in providers.items():
            if prov_info["available"]:
                available_providers.append({
                    "name": f"{prov_info['name']} - {prov_info['description']}",
                    "value": prov_id
                })
        
        if not available_providers:
            console.print("[red]No AI providers are available. Please install required packages.[/]")
            return
        
        selected_provider = inquirer.select(
            message="Select AI provider:",
            choices=available_providers,
            validate=EmptyInputValidator(),
        ).execute()
        
        # Get API key
        api_key = inquirer.text(
            message=f"Enter API key for {providers[selected_provider]['name']}:",
            validate=EmptyInputValidator(),
            is_password=True,
        ).execute()
        
        # Select model
        available_models = []
        models = LLMService.get_available_models(selected_provider)
        for model_id, model_info in models.items():
            recommended = " (recommended)" if model_info.get("recommended") else ""
            available_models.append({
                "name": f"{model_info['name']}{recommended} - {model_info['description']}",
                "value": model_id
            })
        
        selected_model = inquirer.select(
            message="Select AI model:",
            choices=available_models,
            validate=EmptyInputValidator(),
        ).execute()
        
        # Set configuration
        provider = selected_provider
        model = selected_model
        
    elif interactive and not INQUIRER_AVAILABLE:
        console.print("[red]Interactive mode requires InquirerPy. Install with: pip install inquirerpy[/]")
        console.print("[yellow]Falling back to manual configuration...[/]")
    
    if provider:
        # Validate provider
        providers = LLMService.get_available_providers()
        if provider not in providers:
            console.print(f"[red]Error:[/] Invalid provider '{provider}'. Available: {', '.join(providers.keys())}")
            raise click.Abort()
        
        if not providers[provider]["available"]:
            console.print(f"[red]Error:[/] Provider '{provider}' is not available. Install required package.")
            raise click.Abort()
        
        # Set provider in environment
        os.environ["AI_PROVIDER"] = provider
        console.print(f"[green][OK][/] AI provider set to '{provider}'")
    
    if api_key:
        # Set API key based on provider
        if provider == "groq":
            os.environ["GROQ_API_KEY"] = api_key
        elif provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
        else:
            # Use current provider if not specified
            current_provider = os.getenv("AI_PROVIDER") or LLMService.DEFAULT_PROVIDER
            if current_provider == "groq":
                os.environ["GROQ_API_KEY"] = api_key
            elif current_provider == "openai":
                os.environ["OPENAI_API_KEY"] = api_key
            elif current_provider == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = api_key
        
        console.print("[green][OK][/] API key set successfully")
        console.print("[yellow]Note:[/] This sets the API key for the current session only.")
        console.print("[yellow]To persist:[/] Set the appropriate environment variable or add to .env file")
    
    if model:
        # Validate model for the provider
        current_provider = provider or os.getenv("AI_PROVIDER") or LLMService.DEFAULT_PROVIDER
        models = LLMService.get_available_models(current_provider)
        if model not in models:
            console.print(f"[red]Error:[/] Invalid model '{model}' for provider '{current_provider}'")
            console.print(f"Available models: {', '.join(models.keys())}")
            raise click.Abort()
        
        # Set model in environment
        os.environ["AI_MODEL"] = model
        console.print(f"[green][OK][/] AI model set to '{model}'")
        console.print("[yellow]Note:[/] This sets the model for the current session only.")
        console.print("[yellow]To persist:[/] Set AI_MODEL environment variable or add to .env file")
    
    if not provider and not api_key and not model and not interactive:
        console.print("[yellow]No configuration changes specified.[/]")
        console.print("Use --show to view current configuration or specify --provider/--api-key/--model")
        console.print("Use --interactive for guided setup with dropdowns")


# ============================================================================
# AI CLI COMMANDS
# ============================================================================

@main.group()
def ai() -> None:
    """AI-powered FinOps insights and analysis."""
    pass


def _run_interactive_analyze_mode(
    llm_service: LLMService,
    project_id: Optional[str],
    billing_dataset: Optional[str],
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    refresh: bool,
    hide_project_id: bool
) -> None:
    """Run interactive analyze mode with guided setup."""
    console.print("[bold cyan]Interactive AI Analysis Mode[/]")
    console.print()
    
    # Get project ID if not provided
    if not project_id:
        project_id = get_project_id()
        if not project_id:
            project_id = inquirer.text(
                message="Enter GCP project ID:",
                validate=EmptyInputValidator(),
            ).execute()
    
    # Get billing dataset if not provided
    if not billing_dataset:
        billing_dataset = inquirer.text(
            message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
            validate=EmptyInputValidator(),
        ).execute()
    
    # Get regions if not provided
    region_list = None
    if not regions:
        regions_input = inquirer.text(
            message="Enter regions to analyze (comma-separated, or press Enter for all):",
        ).execute()
        if regions_input.strip():
            region_list = [r.strip() for r in regions_input.split(",")]
    else:
        region_list = [r.strip() for r in regions.split(",")]
    
    # Ask about refresh
    if not refresh:
        refresh = inquirer.confirm(
            message="Force refresh data before analysis?",
            default=False,
        ).execute()
    
    # Ask about hiding project ID
    if not hide_project_id:
        hide_project_id = inquirer.confirm(
            message="Hide project ID in output for security?",
            default=False,
        ).execute()
    
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
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Generate AI analysis
        print_progress("Generating AI analysis...")
        analysis = llm_service.generate_analysis(data)
        print_progress("AI analysis ready", done=True)
        
        # Display results
        console.print("\n[bold cyan]AI Analysis Results[/]")
        console.print(f"[dim]Provider: {llm_service.provider} | Model: {llm_service.model}[/]")
        console.print()
        
        # Display the AI analysis (it's already in markdown format)
        console.print(analysis['analysis'])
        
    except Exception as e:
        print_error(f"AI analysis failed: {str(e)}")
        raise click.Abort()


@ai.command()
@click.option(
    "--project-id",
    type=str,
    help="GCP project ID (defaults to gcloud config)"
)
@click.option(
    "--billing-dataset",
    type=str,
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
    help="Comma-separated list of regions to audit"
)
@click.option(
    "--location",
    type=str,
    default="US",
    help="BigQuery location (default: US, e.g., 'asia-southeast1', 'europe-west1')"
)
@click.option(
    "--refresh",
    is_flag=True,
    help="Force refresh data before analysis"
)
@click.option(
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)"
)
@click.option(
    "--interactive",
    is_flag=True,
    help="Use interactive mode for guided analysis setup"
)
def analyze(
    project_id: Optional[str],
    billing_dataset: Optional[str],
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    refresh: bool,
    hide_project_id: bool,
    interactive: bool
) -> None:
    """Generate comprehensive AI analysis of your GCP costs and resources."""
    
    # Check if AI is available
    llm_service = get_llm_service()
    if not llm_service:
        print_error("AI features not available. Set GROQ_API_KEY environment variable.")
        console.print("\n[yellow]To enable AI features:[/]")
        console.print("1. Get a free API key from: https://console.groq.com/")
        console.print("2. Set it: gcp-finops config ai --api-key YOUR_API_KEY")
        console.print("3. Or set environment variable: export GROQ_API_KEY=YOUR_API_KEY")
        raise click.Abort()
    
    # Interactive mode
    if interactive:
        if not INQUIRER_AVAILABLE:
            console.print("[red]Interactive mode requires InquirerPy. Install with: pip install inquirerpy[/]")
            console.print("[yellow]Falling back to manual configuration...[/]")
            interactive = False
        else:
            _run_interactive_analyze_mode(
                llm_service, project_id, billing_dataset, billing_table_prefix, 
                regions, location, refresh, hide_project_id
            )
            return
    
    # Non-interactive mode - require billing_dataset
    if not billing_dataset:
        print_error("Billing dataset is required when not using interactive mode.")
        console.print("Use --interactive for guided setup, or specify --billing-dataset.")
        raise click.Abort()
    
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
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Generate AI analysis
        print_progress("Generating AI insights...")
        analysis = llm_service.analyze_dashboard_data(data)
        print_progress("AI analysis complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]AI Analysis Results[/]")
        console.print(f"[dim]Provider: {analysis['provider']}[/]")
        console.print(f"[dim]Model: {analysis['model_used']}[/]")
        console.print(f"[dim]Project: {analysis['project_id']}[/]")
        console.print(f"[dim]Billing Month: {analysis['billing_month']}[/]")
        console.print()
        
        # Display the AI analysis (it's already in markdown format)
        console.print(analysis['analysis'])
        
    except Exception as e:
        print_error(f"AI analysis failed: {str(e)}")
        raise click.Abort()


def _run_interactive_ask_mode(
    llm_service: LLMService,
    project_id: Optional[str],
    billing_dataset: Optional[str],
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    hide_project_id: bool
) -> None:
    """Run interactive ask mode with guided setup and conversation."""
    console.print("[bold cyan]Interactive AI Question Mode[/]")
    console.print()
    
    # Get project ID if not provided
    if not project_id:
        project_id = get_project_id()
        if not project_id:
            project_id = inquirer.text(
                message="Enter GCP project ID:",
                validate=EmptyInputValidator(),
            ).execute()
    
    # Get billing dataset if not provided
    if not billing_dataset:
        billing_dataset = inquirer.text(
            message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
            validate=EmptyInputValidator(),
        ).execute()
    
    # Get regions if not provided
    region_list = None
    if not regions:
        regions_input = inquirer.text(
            message="Enter regions to analyze (comma-separated, or press Enter for all):",
        ).execute()
        if regions_input.strip():
            region_list = [r.strip() for r in regions_input.split(",")]
    else:
        region_list = [r.strip() for r in regions.split(",")]
    
    # Initialize runner once
    console.print("\n[bold yellow]Initializing analysis...[/]")
    try:
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix=billing_table_prefix,
            regions=region_list,
            location=location,
            hide_project_id=hide_project_id
        )
        
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        console.print(f"[green]✓[/] Analysis complete! You can now ask questions about your GCP costs and resources.")
        console.print(f"[dim]Provider: {llm_service.provider} | Model: {llm_service.model}[/]")
        console.print()
        
    except Exception as e:
        print_error(f"Failed to initialize analysis: {str(e)}")
        raise click.Abort()
    
    # Conversation loop
    conversation_history = []
    while True:
        # Get question from user
        question = inquirer.text(
            message="Ask a question about your GCP costs (or type 'quit' to exit):",
            validate=EmptyInputValidator(),
        ).execute()
        
        if question.lower() in ['quit', 'exit', 'q']:
            console.print("[yellow]Goodbye![/]")
            break
        
        try:
            # Add context from conversation history
            context = ""
            if conversation_history:
                context = "\n\nPrevious conversation:\n" + "\n".join(conversation_history[-3:])  # Last 3 exchanges
            
            # Get AI answer
            print_progress("Getting AI answer...")
            answer = llm_service.answer_question(question, data, context=context)
            print_progress("AI answer ready", done=True)
            
            # Display results with enhanced formatting
            format_ai_response(question, answer, llm_service.provider, llm_service.model)
            
            # Store in conversation history
            conversation_history.append(f"Q: {question}")
            conversation_history.append(f"A: {answer}")
            
        except Exception as e:
            print_error(f"Failed to get AI answer: {str(e)}")
            console.print("[yellow]Please try a different question.[/]")
            console.print()


@ai.command()
@click.argument("question", type=str, required=False)
@click.option(
    "--project-id",
    type=str,
    help="GCP project ID (defaults to gcloud config)"
)
@click.option(
    "--billing-dataset",
    type=str,
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
    help="Comma-separated list of regions to audit"
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
@click.option(
    "--interactive",
    is_flag=True,
    help="Start interactive conversation mode"
)
def ask(
    question: Optional[str],
    project_id: Optional[str],
    billing_dataset: Optional[str],
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    hide_project_id: bool,
    interactive: bool
) -> None:
    """Ask a natural language question about your GCP costs and resources.
    
    Examples:
    - "Why are my Cloud Run costs so high?"
    - "What are my biggest cost drivers?"
    - "How many idle resources do I have?"
    - "Which services are consuming the most budget?"
    
    Use --interactive for a conversational mode where you can ask multiple questions.
    """
    
    # Check if AI is available
    llm_service = get_llm_service()
    if not llm_service:
        print_error("AI features not available. Set GROQ_API_KEY environment variable.")
        console.print("\n[yellow]To enable AI features:[/]")
        console.print("1. Get a free API key from: https://console.groq.com/")
        console.print("2. Set it: gcp-finops config ai --api-key YOUR_API_KEY")
        console.print("3. Or set environment variable: export GROQ_API_KEY=YOUR_API_KEY")
        raise click.Abort()
    
    # Interactive mode
    if interactive:
        if not INQUIRER_AVAILABLE:
            console.print("[red]Interactive mode requires InquirerPy. Install with: pip install inquirerpy[/]")
            console.print("[yellow]Falling back to manual configuration...[/]")
            interactive = False
        else:
            _run_interactive_ask_mode(
                llm_service, project_id, billing_dataset, billing_table_prefix, 
                regions, location, hide_project_id
            )
            return
    
    # Non-interactive mode - require question and billing_dataset
    if not question:
        print_error("Question is required when not using interactive mode.")
        console.print("Use --interactive for guided question mode, or provide a question as argument.")
        raise click.Abort()
    
    if not billing_dataset:
        print_error("Billing dataset is required when not using interactive mode.")
        console.print("Use --interactive for guided setup, or specify --billing-dataset.")
        raise click.Abort()
    
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
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Ask AI question
        print_progress("Getting AI answer...")
        answer = llm_service.answer_question(question, data)
        print_progress("AI answer ready", done=True)
        
        # Display results with enhanced formatting
        format_ai_response(question, answer, llm_service.provider, llm_service.model)
        
    except Exception as e:
        print_error(f"AI question failed: {str(e)}")
        raise click.Abort()


@ai.command()
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
    help="Comma-separated list of regions to audit"
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
def summary(
    project_id: Optional[str],
    billing_dataset: str,
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    hide_project_id: bool
) -> None:
    """Generate an executive summary of your GCP FinOps data."""
    
    # Check if AI is available
    llm_service = get_llm_service()
    if not llm_service:
        print_error("AI features not available. Set GROQ_API_KEY environment variable.")
        console.print("\n[yellow]To enable AI features:[/]")
        console.print("1. Get a free API key from: https://console.groq.com/")
        console.print("2. Set it: gcp-finops config ai --api-key YOUR_API_KEY")
        console.print("3. Or set environment variable: export GROQ_API_KEY=YOUR_API_KEY")
        raise click.Abort()
    
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
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Generate executive summary
        print_progress("Generating executive summary...")
        summary = llm_service.generate_executive_summary(data)
        print_progress("Executive summary ready", done=True)
        
        # Display results
        console.print("\n[bold cyan]Executive Summary[/]")
        console.print(f"[dim]Provider: {llm_service.provider}[/]")
        console.print(f"[dim]Model: {llm_service.model}[/]")
        console.print(f"[dim]Project: {data.project_id}[/]")
        console.print(f"[dim]Billing Month: {data.billing_month}[/]")
        console.print()
        
        # Display the summary (it's already in markdown format)
        console.print(summary)
        
    except Exception as e:
        print_error(f"Executive summary failed: {str(e)}")
        raise click.Abort()


@ai.command()
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
    help="Comma-separated list of regions to audit"
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
def explain_spike(
    project_id: Optional[str],
    billing_dataset: str,
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    hide_project_id: bool
) -> None:
    """Explain why your costs increased or decreased compared to last month."""
    
    # Check if AI is available
    llm_service = get_llm_service()
    if not llm_service:
        print_error("AI features not available. Set GROQ_API_KEY environment variable.")
        console.print("\n[yellow]To enable AI features:[/]")
        console.print("1. Get a free API key from: https://console.groq.com/")
        console.print("2. Set it: gcp-finops config ai --api-key YOUR_API_KEY")
        console.print("3. Or set environment variable: export GROQ_API_KEY=YOUR_API_KEY")
        raise click.Abort()
    
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
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Explain cost spike
        print_progress("Analyzing cost changes...")
        explanation = llm_service.explain_cost_spike(data)
        print_progress("Cost analysis complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]Cost Change Analysis[/]")
        console.print(f"[dim]Provider: {llm_service.provider}[/]")
        console.print(f"[dim]Model: {llm_service.model}[/]")
        console.print(f"[dim]Project: {data.project_id}[/]")
        console.print(f"[dim]Billing Month: {data.billing_month}[/]")
        console.print()
        console.print(explanation)
        
    except Exception as e:
        print_error(f"Cost spike analysis failed: {str(e)}")
        raise click.Abort()


@ai.command()
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
    help="Comma-separated list of regions to audit"
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
def prioritize(
    project_id: Optional[str],
    billing_dataset: str,
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    hide_project_id: bool
) -> None:
    """Get AI help prioritizing optimization recommendations."""
    
    # Check if AI is available
    llm_service = get_llm_service()
    if not llm_service:
        print_error("AI features not available. Set GROQ_API_KEY environment variable.")
        console.print("\n[yellow]To enable AI features:[/]")
        console.print("1. Get a free API key from: https://console.groq.com/")
        console.print("2. Set it: gcp-finops config ai --api-key YOUR_API_KEY")
        console.print("3. Or set environment variable: export GROQ_API_KEY=YOUR_API_KEY")
        raise click.Abort()
    
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
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Prioritize recommendations
        print_progress("Prioritizing recommendations...")
        prioritization = llm_service.prioritize_recommendations(data.recommendations)
        print_progress("Prioritization complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]Recommendation Prioritization[/]")
        console.print(f"[dim]Provider: {llm_service.provider}[/]")
        console.print(f"[dim]Model: {llm_service.model}[/]")
        console.print(f"[dim]Project: {data.project_id}[/]")
        console.print(f"[dim]Total Recommendations: {len(data.recommendations)}[/]")
        console.print()
        
        # Display the prioritization (it's already in markdown format)
        console.print(prioritization)
        
    except Exception as e:
        print_error(f"Recommendation prioritization failed: {str(e)}")
        raise click.Abort()


@ai.command()
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
    help="Comma-separated list of regions to audit"
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
def budget_suggestions(
    project_id: Optional[str],
    billing_dataset: str,
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    hide_project_id: bool
) -> None:
    """Get AI suggestions for budget alert thresholds based on spending patterns."""
    
    # Check if AI is available
    llm_service = get_llm_service()
    if not llm_service:
        print_error("AI features not available. Set GROQ_API_KEY environment variable.")
        console.print("\n[yellow]To enable AI features:[/]")
        console.print("1. Get a free API key from: https://console.groq.com/")
        console.print("2. Set it: gcp-finops config ai --api-key YOUR_API_KEY")
        console.print("3. Or set environment variable: export GROQ_API_KEY=YOUR_API_KEY")
        raise click.Abort()
    
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
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Suggest budget alerts
        print_progress("Analyzing spending patterns...")
        suggestions = llm_service.suggest_budget_alerts(data)
        print_progress("Budget analysis complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]Budget Alert Suggestions[/]")
        console.print(f"[dim]Provider: {llm_service.provider}[/]")
        console.print(f"[dim]Model: {llm_service.model}[/]")
        console.print(f"[dim]Project: {data.project_id}[/]")
        console.print(f"[dim]Billing Month: {data.billing_month}[/]")
        console.print()
        console.print(suggestions)
        
    except Exception as e:
        print_error(f"Budget suggestions failed: {str(e)}")
        raise click.Abort()


@ai.command()
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
    help="Comma-separated list of regions to audit"
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
def utilization(
    project_id: Optional[str],
    billing_dataset: str,
    billing_table_prefix: str,
    regions: Optional[str],
    location: str,
    hide_project_id: bool
) -> None:
    """Analyze resource utilization patterns with AI insights."""
    
    # Check if AI is available
    llm_service = get_llm_service()
    if not llm_service:
        print_error("AI features not available. Set GROQ_API_KEY environment variable.")
        console.print("\n[yellow]To enable AI features:[/]")
        console.print("1. Get a free API key from: https://console.groq.com/")
        console.print("2. Set it: gcp-finops config ai --api-key YOUR_API_KEY")
        console.print("3. Or set environment variable: export GROQ_API_KEY=YOUR_API_KEY")
        raise click.Abort()
    
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
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Analyze utilization
        print_progress("Analyzing resource utilization...")
        analysis = llm_service.analyze_resource_utilization(data.audit_results)
        print_progress("Utilization analysis complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]Resource Utilization Analysis[/]")
        console.print(f"[dim]Provider: {llm_service.provider}[/]")
        console.print(f"[dim]Model: {llm_service.model}[/]")
        console.print(f"[dim]Project: {data.project_id}[/]")
        console.print(f"[dim]Total Resources: {sum(r.total_count for r in data.audit_results.values())}[/]")
        console.print(f"[dim]Idle Resources: {sum(r.idle_count for r in data.audit_results.values())}[/]")
        console.print()
        console.print(analysis)
        
    except Exception as e:
        print_error(f"Utilization analysis failed: {str(e)}")
        raise click.Abort()


@main.command()
@click.option(
    "--font",
    type=str,
    help="Show preview of specific font"
)
@click.option(
    "--list",
    "list_fonts",
    is_flag=True,
    help="List all available fonts"
)
@with_heading
def fonts(font: Optional[str], list_fonts: bool) -> None:
    """Show available ASCII art fonts and previews."""
    try:
        available_fonts = pyfiglet.FigletFont.getFonts()
        
        if list_fonts:
            console.print(f"[bold cyan]Available ASCII Art Fonts ({len(available_fonts)} total):[/]")
            console.print()
            
            # Group fonts by category
            popular_fonts = ["slant", "block", "banner", "big", "standard", "small", "mini", "script", "digital", "isometric1"]
            other_fonts = [f for f in available_fonts if f not in popular_fonts]
            
            console.print("[bold green]Popular Fonts:[/]")
            for f in popular_fonts:
                if f in available_fonts:
                    console.print(f"  [cyan]{f}[/]")
            
            console.print(f"\n[bold yellow]All Fonts ({len(other_fonts)}):[/]")
            # Display in columns
            for i in range(0, len(other_fonts), 4):
                row_fonts = other_fonts[i:i+4]
                console.print("  " + "  ".join(f"[dim]{f:15}[/]" for f in row_fonts))
            
            console.print(f"\n[dim]Use --font FONT_NAME to preview a specific font[/]")
            return
        
        if font:
            if font not in available_fonts:
                console.print(f"[red]Error:[/] Font '{font}' not found.")
                console.print(f"[yellow]Available fonts:[/] {', '.join(available_fonts[:10])}...")
                console.print(f"[yellow]Use --list to see all {len(available_fonts)} fonts[/]")
                return
            
            # Show preview
            f = pyfiglet.Figlet(font=font)
            ascii_art = f.renderText('GCP FinOps')
            
            console.print(f"[bold cyan]Font Preview: {font}[/]")
            console.print(f"[bold bright_green]{ascii_art}[/]")
            console.print(f"[dim]To use this font, add to your config.toml:[/]")
            console.print(f"[dim][ascii-art][/]")
            console.print(f"[dim]font = \"{font}\"[/]")
        else:
            # Show default preview
            console.print("[bold cyan]Default Font Preview (slant):[/]")
            f = pyfiglet.Figlet(font="slant")
            ascii_art = f.renderText('GCP FinOps')
            console.print(f"[bold bright_green]{ascii_art}[/]")
            console.print()
            console.print("[yellow]Usage:[/]")
            console.print("  gcp-finops fonts --list                    # List all fonts")
            console.print("  gcp-finops fonts --font block              # Preview specific font")
            console.print("  gcp-finops fonts --font banner             # Preview banner font")
            
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")
        console.print("[yellow]Make sure pyfiglet is installed: pip install pyfiglet[/]")


def _run_main_interactive_mode() -> None:
    """Run the main interactive mode with menu navigation."""
    console.print("[bold cyan]GCP FinOps Dashboard - Interactive Mode[/]")
    console.print("[dim]Navigate through different sections and commands[/]")
    console.print()
    
    while True:
        # Main menu options
        main_choice = inquirer.select(
            message="Select a section:",
            choices=[
                ("Dashboard & Reports", "dashboard"),
                ("Audits & Analysis", "audit"),
                ("Forecasting & Trends", "forecast"),
                ("AI-Powered Insights", "ai"),
                ("Configuration & Setup", "config"),
                ("Quick Setup (First Time)", "quick-setup"),
                ("Help & Documentation", "help"),
                ("Exit", "exit")
            ]
        ).execute()
        
        # Extract the value from the tuple
        if isinstance(main_choice, tuple):
            main_choice = main_choice[1]
        
        if main_choice == "exit":
            console.print("[yellow]Goodbye![/]")
            break
        elif main_choice == "dashboard":
            _run_dashboard_interactive_mode()
        elif main_choice == "audit":
            _run_audit_interactive_mode()
        elif main_choice == "forecast":
            _run_forecast_interactive_mode()
        elif main_choice == "ai":
            _run_ai_interactive_mode()
        elif main_choice == "config":
            _run_config_interactive_mode()
        elif main_choice == "quick-setup":
            _run_quick_setup()
        elif main_choice == "help":
            _show_help_menu()


def _run_dashboard_interactive_mode() -> None:
    """Run dashboard interactive mode."""
    console.print("\n[bold cyan]Dashboard & Reports Section[/]")
    
    while True:
        choice = inquirer.select(
            message="Choose an option:",
            choices=[
                ("Run Complete Dashboard", "dashboard"),
                ("Generate PDF Report", "report"),
                ("Back to Main Menu", "back")
            ]
        ).execute()
        
        # Extract the value from the tuple
        if isinstance(choice, tuple):
            choice = choice[1]
        
        if choice == "back":
            break
        elif choice == "dashboard":
            _run_dashboard_command()
        elif choice == "report":
            _run_report_command()


def _run_audit_interactive_mode() -> None:
    """Run audit interactive mode."""
    console.print("\n[bold cyan]Audits & Analysis Section[/]")
    
    while True:
        choice = inquirer.select(
            message="Choose an option:",
            choices=[
                ("Run Cloud Run Audit", "cloudrun"),
                ("Run Cloud Functions Audit", "functions"),
                ("Run Compute Engine Audit", "compute"),
                ("Run Cloud SQL Audit", "sql"),
                ("Run Disk Audit", "disk"),
                ("Run IP Audit", "ip"),
                ("Run All Audits", "all"),
                ("Back to Main Menu", "back")
            ]
        ).execute()
        
        # Extract the value from the tuple
        if isinstance(choice, tuple):
            choice = choice[1]
        
        if choice == "back":
            break
        elif choice == "cloudrun":
            _run_audit_command("cloudrun")
        elif choice == "functions":
            _run_audit_command("functions")
        elif choice == "compute":
            _run_audit_command("compute")
        elif choice == "sql":
            _run_audit_command("sql")
        elif choice == "disk":
            _run_audit_command("disk")
        elif choice == "ip":
            _run_audit_command("ip")
        elif choice == "all":
            _run_audit_command("all")


def _run_forecast_interactive_mode() -> None:
    """Run forecast interactive mode."""
    console.print("\n[bold cyan]Forecasting & Trends Section[/]")
    
    while True:
        choice = inquirer.select(
            message="Choose an option:",
            choices=[
                ("Generate Cost Forecast", "forecast"),
                ("Display Trend Report", "trend"),
                ("Back to Main Menu", "back")
            ]
        ).execute()
        
        # Extract the value from the tuple
        if isinstance(choice, tuple):
            choice = choice[1]
        
        if choice == "back":
            break
        elif choice == "forecast":
            _run_forecast_command()
        elif choice == "trend":
            _run_trend_command()


def _run_ai_interactive_mode() -> None:
    """Run AI interactive mode with enhanced navigation."""
    console.print("\n[bold cyan]AI-Powered Insights Section[/]")
    
    # Check if AI is available
    llm_service = get_llm_service()
    if not llm_service:
        console.print("[red]AI features not available. Set GROQ_API_KEY environment variable.[/]")
        console.print("\n[yellow]To enable AI features:[/]")
        console.print("1. Get a free API key from: https://console.groq.com/")
        console.print("2. Set it: gcp-finops config ai --api-key YOUR_API_KEY")
        console.print("3. Or set environment variable: export GROQ_API_KEY=YOUR_API_KEY")
        console.print()
        return
    
    while True:
        choice = inquirer.select(
            message="Choose an AI option:",
            choices=[
                ("AI Chat (Ask Questions)", "chat"),
                ("AI Analysis", "analyze"),
                ("Executive Summary", "summary"),
                ("Explain Cost Spike", "explain-spike"),
                ("Prioritize Recommendations", "prioritize"),
                ("Budget Suggestions", "budget"),
                ("Utilization Analysis", "utilization"),
                ("Back to Main Menu", "back")
            ]
        ).execute()
        
        # Extract the value from the tuple
        if isinstance(choice, tuple):
            choice = choice[1]
        
        if choice == "back":
            break
        elif choice == "chat":
            _run_ai_chat_interactive_mode(llm_service)
        elif choice == "analyze":
            _run_ai_analyze_command(llm_service)
        elif choice == "summary":
            _run_ai_summary_command(llm_service)
        elif choice == "explain-spike":
            _run_ai_explain_spike_command(llm_service)
        elif choice == "prioritize":
            _run_ai_prioritize_command(llm_service)
        elif choice == "budget":
            _run_ai_budget_command(llm_service)
        elif choice == "utilization":
            _run_ai_utilization_command(llm_service)


def _run_ai_chat_interactive_mode(llm_service: LLMService) -> None:
    """Run enhanced AI chat interactive mode with navigation options."""
    create_chat_header()
    console.print("[dim]Type 'back' to return to AI menu, 'main' to return to main menu, or 'quit' to exit[/]")
    console.print()
    
    # Get configuration for analysis
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner and get data
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        show_enhanced_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        show_enhanced_progress("Analysis complete", done=True)
        
        # Show completion message with styling using color scheme
        completion_panel = Panel(
            Align.center(
                Text.assemble(
                    f"[bold {get_color('success')}]✓ Analysis complete![/]", "\n",
                    f"[{get_color('muted')}]You can now ask questions about your GCP costs and resources.[/]", "\n",
                    f"[{get_color('muted')}]Provider: {llm_service.provider} | Model: {llm_service.model}[/]"
                )
            ),
            border_style=get_color('success'),
            padding=(0, 1),
            title=f"[bold {get_color('success')}]🎉 Ready for AI Chat[/]",
            title_align="center"
        )
        console.print(completion_panel)
        console.print()
        console.print()
        
        # Conversation loop
        conversation_history = []
        while True:
            # Get question from user
            question = inquirer.text(
                message="Ask a question about your GCP costs (or type 'back', 'main', or 'quit'):",
                validate=EmptyInputValidator(),
            ).execute()
            
            # Check for navigation commands
            if question.lower().strip() in ['quit', 'exit', 'q']:
                console.print("[yellow]Goodbye![/]")
                return
            elif question.lower().strip() in ['back']:
                console.print("[yellow]Returning to AI menu...[/]")
                return
            elif question.lower().strip() in ['main']:
                console.print("[yellow]Returning to main menu...[/]")
                return
            
            try:
                # Add context from conversation history
                context = ""
                if conversation_history:
                    context = "\n\nPrevious conversation:\n" + "\n".join(conversation_history[-3:])  # Last 3 exchanges
                
                # Get AI answer
                show_enhanced_progress("Getting AI answer...")
                answer = llm_service.answer_question(question, data, context=context)
                show_enhanced_progress("AI answer ready", done=True)
                
                # Display results with enhanced formatting
                format_ai_response(question, answer, llm_service.provider, llm_service.model)
                
                # Store in conversation history
                conversation_history.append(f"Q: {question}")
                conversation_history.append(f"A: {answer}")
                
            except Exception as e:
                print_error(f"Failed to get AI answer: {str(e)}")
                console.print("[yellow]Please try a different question.[/]")
                console.print()
                
    except Exception as e:
        print_error(f"Failed to initialize analysis: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()


def _run_config_interactive_mode() -> None:
    """Run configuration interactive mode."""
    console.print("\n[bold cyan]Configuration & Setup Section[/]")
    
    while True:
        choice = inquirer.select(
            message="Choose an option:",
            choices=[
                ("Configure AI Settings", "ai-config"),
                ("Show Setup Instructions", "setup-instructions"),
                ("Back to Main Menu", "back")
            ]
        ).execute()
        
        # Extract the value from the tuple
        if isinstance(choice, tuple):
            choice = choice[1]
        
        if choice == "back":
            break
        elif choice == "ai-config":
            _run_ai_config_interactive()
        elif choice == "setup-instructions":
            _show_setup_instructions()


def _show_help_menu() -> None:
    """Show help menu."""
    console.print("\n[bold cyan]Help & Documentation[/]")
    console.print()
    console.print("[bold]Available Commands:[/]")
    console.print("• [cyan]gcp-finops dashboard[/] - Run complete dashboard")
    console.print("• [cyan]gcp-finops report[/] - Generate PDF report")
    console.print("• [cyan]gcp-finops audit[/] - Run specific audit")
    console.print("• [cyan]gcp-finops forecast[/] - Generate cost forecast")
    console.print("• [cyan]gcp-finops trend[/] - Display trend report")
    console.print("• [cyan]gcp-finops api[/] - Start API server")
    console.print("• [cyan]gcp-finops setup[/] - Show setup instructions")
    console.print()
    console.print("[bold]AI Commands:[/]")
    console.print("• [cyan]gcp-finops ai analyze[/] - Generate AI analysis")
    console.print("• [cyan]gcp-finops ai ask[/] - Ask questions")
    console.print("• [cyan]gcp-finops ai summary[/] - Generate executive summary")
    console.print("• [cyan]gcp-finops config ai[/] - Configure AI settings")
    console.print()
    console.print("[bold]For more information:[/] https://github.com/your-repo/gcp-finops-dashboard")
    console.print()


def _run_ai_config_interactive() -> None:
    """Run AI configuration interactive mode."""
    console.print("\n[bold cyan]AI Configuration[/]")
    
    # Get current AI configuration
    llm_service = get_llm_service()
    if llm_service:
        console.print(f"[green]Current AI Provider:[/] {llm_service.provider}")
        console.print(f"[green]Current Model:[/] {llm_service.model}")
        console.print()
    
    # Configuration options
    while True:
        choice = inquirer.select(
            message="Choose a configuration option:",
            choices=[
                ("Set API Key", "api-key"),
                ("Change AI Provider", "provider"),
                ("Change Model", "model"),
                ("View Current Configuration", "view"),
                ("Back to Config Menu", "back")
            ]
        ).execute()
        
        # Extract the value from the tuple
        if isinstance(choice, tuple):
            choice = choice[1]
        
        if choice == "back":
            break
        elif choice == "api-key":
            _configure_api_key()
        elif choice == "provider":
            _configure_ai_provider()
        elif choice == "model":
            _configure_ai_model()
        elif choice == "view":
            _view_ai_configuration()


def _configure_api_key():
    """Configure AI API key."""
    console.print("\n[bold cyan]Configure API Key[/]")
    
    # Get provider first
    provider = inquirer.select(
        message="Select AI provider:",
        choices=[
            ("Groq (Recommended - Fast & Free)", "groq"),
            ("OpenAI", "openai"),
            ("Anthropic (Claude)", "anthropic")
        ]
    ).execute()
    
    if isinstance(provider, tuple):
        provider = provider[1]
    
    # Get API key
    api_key = inquirer.text(
        message=f"Enter {provider.title()} API key:",
        validate=EmptyInputValidator(),
    ).execute()
    
    # Save configuration
    try:
        # Set provider in environment
        os.environ["AI_PROVIDER"] = provider
        
        # Set API key based on provider
        if provider == "groq":
            os.environ["GROQ_API_KEY"] = api_key
        elif provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
        
        # Refresh the LLM service to use the new API key
        from .llm_service import refresh_llm_service
        refresh_llm_service()
        
        console.print(f"[green]✓ {provider.title()} API key configured successfully![/]")
        console.print("[yellow]Note:[/] This sets the configuration for the current session only.")
        console.print("[yellow]To persist:[/] Set the appropriate environment variables or add to .env file")
    except Exception as e:
        console.print(f"[red]Error saving configuration: {str(e)}[/]")
    console.print()


def _configure_ai_provider():
    """Configure AI provider."""
    console.print("\n[bold cyan]Configure AI Provider[/]")
    
    provider = inquirer.select(
        message="Select AI provider:",
        choices=[
            ("Groq (Recommended - Fast & Free)", "groq"),
            ("OpenAI", "openai"),
            ("Anthropic (Claude)", "anthropic")
        ]
    ).execute()
    
    if isinstance(provider, tuple):
        provider = provider[1]
    
    # Get API key for the provider
    api_key = inquirer.text(
        message=f"Enter {provider.title()} API key:",
        validate=EmptyInputValidator(),
    ).execute()
    
    # Save configuration
    try:
        # Set provider in environment
        os.environ["AI_PROVIDER"] = provider
        
        # Set API key based on provider
        if provider == "groq":
            os.environ["GROQ_API_KEY"] = api_key
        elif provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
        
        # Refresh the LLM service to use the new configuration
        from .llm_service import refresh_llm_service
        refresh_llm_service()
        
        console.print(f"[green]✓ AI provider set to {provider.title()}![/]")
        console.print("[yellow]Note:[/] This sets the configuration for the current session only.")
        console.print("[yellow]To persist:[/] Set the appropriate environment variables or add to .env file")
    except Exception as e:
        console.print(f"[red]Error saving configuration: {str(e)}[/]")
    console.print()


def _configure_ai_model():
    """Configure AI model."""
    console.print("\n[bold cyan]Configure AI Model[/]")
    
    # Get current provider
    llm_service = get_llm_service()
    if not llm_service:
        console.print("[red]Please configure an AI provider first![/]")
        return
    
    # Get available models for the provider
    if llm_service.provider == "groq":
        models = [
            ("llama-3.3-70b-versatile (Recommended)", "llama-3.3-70b-versatile"),
            ("llama-3.1-70b-versatile", "llama-3.1-70b-versatile"),
            ("llama-3.1-8b-instant", "llama-3.1-8b-instant"),
            ("mixtral-8x7b-32768", "mixtral-8x7b-32768")
        ]
    elif llm_service.provider == "openai":
        models = [
            ("gpt-4o (Recommended)", "gpt-4o"),
            ("gpt-4o-mini", "gpt-4o-mini"),
            ("gpt-4-turbo", "gpt-4-turbo"),
            ("gpt-3.5-turbo", "gpt-3.5-turbo")
        ]
    elif llm_service.provider == "anthropic":
        models = [
            ("claude-3-5-sonnet-20241022 (Recommended)", "claude-3-5-sonnet-20241022"),
            ("claude-3-5-haiku-20241022", "claude-3-5-haiku-20241022"),
            ("claude-3-opus-20240229", "claude-3-opus-20240229")
        ]
    else:
        console.print(f"[red]Unknown provider: {llm_service.provider}[/]")
        return
    
    model = inquirer.select(
        message=f"Select model for {llm_service.provider.title()}:",
        choices=models
    ).execute()
    
    if isinstance(model, tuple):
        model = model[1]
    
    # Save configuration
    try:
        # Set model in environment
        os.environ["AI_MODEL"] = model
        # Refresh the LLM service to use the new model
        from .llm_service import refresh_llm_service
        refresh_llm_service()
        
        console.print(f"[green]✓ Model set to {model}![/]")
        console.print("[yellow]Note:[/] This sets the model for the current session only.")
        console.print("[yellow]To persist:[/] Set AI_MODEL environment variable or add to .env file")
    except Exception as e:
        console.print(f"[red]Error saving configuration: {str(e)}[/]")
    console.print()


def _view_ai_configuration():
    """View current AI configuration."""
    console.print("\n[bold cyan]Current AI Configuration[/]")
    
    # Get current configuration from environment
    current_provider = os.getenv("AI_PROVIDER") or LLMService.DEFAULT_PROVIDER
    current_model = os.getenv("AI_MODEL") or LLMService.DEFAULT_MODEL
    
    # Get current API key based on provider
    current_api_key = None
    if current_provider == "groq":
        current_api_key = os.getenv("GROQ_API_KEY")
    elif current_provider == "openai":
        current_api_key = os.getenv("OPENAI_API_KEY")
    elif current_provider == "anthropic":
        current_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    console.print(f"[bold]Provider:[/] {current_provider}")
    console.print(f"[bold]Model:[/] {current_model}")
    console.print(f"[bold]API Key:[/] {'*' * 20}...{current_api_key[-4:] if current_api_key else '[red]Not set[/]'}")
    
    if not current_api_key:
        console.print("\n[yellow]No API key found. Please configure an API key first.[/]")
    console.print()


def _run_quick_setup():
    """Run quick setup for first-time users."""
    console.print("\n[bold cyan]Quick Setup - First Time Configuration[/]")
    console.print("[dim]This will guide you through the essential setup steps[/]")
    console.print()
    
    # Step 1: AI Configuration
    console.print("[bold]Step 1: Configure AI (Optional but Recommended)[/]")
    ai_setup = inquirer.confirm(
        message="Would you like to set up AI features now?",
        default=True,
    ).execute()
    
    if ai_setup:
        _configure_api_key()
    
    # Step 2: GCP Project Setup
    console.print("[bold]Step 2: GCP Project Information[/]")
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter your GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
        console.print(f"[green]✓ Project ID set to: {project_id}[/]")
    else:
        console.print(f"[green]✓ Project ID detected: {project_id}[/]")
    
    # Step 3: Billing Dataset
    console.print("\n[bold]Step 3: Billing Dataset[/]")
    billing_dataset = inquirer.text(
        message="Enter your BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    console.print(f"[green]✓ Billing dataset set to: {billing_dataset}[/]")
    
    # Step 4: Test Configuration
    console.print("\n[bold]Step 4: Test Configuration[/]")
    test_config = inquirer.confirm(
        message="Would you like to test your configuration by running a quick analysis?",
        default=True,
    ).execute()
    
    if test_config:
        try:
            console.print("\n[yellow]Running quick test analysis...[/]")
            runner = DashboardRunner(
                project_id=project_id,
                billing_dataset=billing_dataset,
                billing_table_prefix="gcp_billing_export_v1",
                regions=None,
                location="US",
                hide_project_id=False
            )
            
            print_progress("Testing configuration...")
            data = runner.run()
            print_progress("Test complete", done=True)
            
            console.print("[green]✓ Configuration test successful![/]")
            console.print(f"[green]✓ Found {len(data.audit_results)} resource types[/]")
            console.print(f"[green]✓ Current month cost: ${data.current_month_cost:,.2f}[/]")
            
        except Exception as e:
            console.print(f"[red]✗ Configuration test failed: {str(e)}[/]")
            console.print("[yellow]Please check your project ID and billing dataset.[/]")
    
    console.print("\n[bold green]Setup Complete![/]")
    console.print("[green]You can now use all the features of the GCP FinOps Dashboard.[/]")
    console.print()


def _show_setup_instructions() -> None:
    """Show setup instructions."""
    console.print("\n[bold cyan]Setup Instructions[/]")
    console.print()
    console.print("[bold]1. Enable Required APIs:[/]")
    console.print("   gcloud services enable compute.googleapis.com")
    console.print("   gcloud services enable run.googleapis.com")
    console.print("   gcloud services enable cloudfunctions.googleapis.com")
    console.print("   gcloud services enable sqladmin.googleapis.com")
    console.print("   gcloud services enable bigquery.googleapis.com")
    console.print()
    console.print("[bold]2. Set up billing export to BigQuery[/]")
    console.print("[bold]3. Configure authentication[/]")
    console.print("[bold]4. Run your first analysis![/]")
    console.print()


# Command execution functions
def _run_dashboard_command():
    """Run the dashboard command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Running dashboard analysis...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Display results
        _display_dashboard_results(data)
        
    except Exception as e:
        print_error(f"Failed to run dashboard: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_report_command():
    """Run the report command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Generating PDF report...")
        data = runner.run()
        _generate_pdf_report(data)
        print_progress("Report generated", done=True)
        
    except Exception as e:
        print_error(f"Failed to generate report: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_audit_command(audit_type: str):
    """Run a specific audit command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress(f"Running {audit_type} audit...")
        data = runner.run_audit(audit_type)
        print_progress("Audit complete", done=True)
        
        # Display results
        _display_audit_results(data, audit_type)
        
    except Exception as e:
        print_error(f"Failed to run {audit_type} audit: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_forecast_command():
    """Run the forecast command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Generating cost forecast...")
        data = runner.run_forecast()
        print_progress("Forecast complete", done=True)
        
        # Display results
        _display_forecast_results(data)
        
    except Exception as e:
        print_error(f"Failed to generate forecast: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_trend_command():
    """Run the trend command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Analyzing cost trends...")
        data = runner.run_trend()
        print_progress("Analysis complete", done=True)
        
        # Display results
        _display_trend_results(data)
        
    except Exception as e:
        print_error(f"Failed to analyze trends: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_ai_analyze_command(llm_service):
    """Run AI analysis command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Running AI analysis...")
        data = runner.run()
        analysis = llm_service.analyze(data)
        print_progress("Analysis complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]AI Analysis[/]")
        console.print(analysis)
        console.print()
        
    except Exception as e:
        print_error(f"Failed to run AI analysis: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_ai_summary_command(llm_service):
    """Run AI summary command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Generating executive summary...")
        data = runner.run()
        summary = llm_service.generate_executive_summary(data)
        print_progress("Summary complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]Executive Summary[/]")
        console.print(summary)
        console.print()
        
    except Exception as e:
        print_error(f"Failed to generate summary: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_ai_explain_spike_command(llm_service):
    """Run AI explain spike command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Analyzing cost spikes...")
        data = runner.run()
        explanation = llm_service.explain_cost_spike(data)
        print_progress("Analysis complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]Cost Spike Analysis[/]")
        console.print(explanation)
        console.print()
        
    except Exception as e:
        print_error(f"Failed to analyze cost spike: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_ai_prioritize_command(llm_service):
    """Run AI prioritize command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Analyzing recommendations...")
        data = runner.run()
        recommendations = llm_service.prioritize_recommendations(data.recommendations)
        print_progress("Analysis complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]Prioritized Recommendations[/]")
        console.print(recommendations)
        console.print()
        
    except Exception as e:
        print_error(f"Failed to prioritize recommendations: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_ai_budget_command(llm_service):
    """Run AI budget suggestions command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Analyzing budget data...")
        data = runner.run()
        suggestions = llm_service.suggest_budgets(data)
        print_progress("Analysis complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]Budget Suggestions[/]")
        console.print(suggestions)
        console.print()
        
    except Exception as e:
        print_error(f"Failed to generate budget suggestions: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()

def _run_ai_utilization_command(llm_service):
    """Run AI utilization analysis command interactively."""
    # Get configuration
    project_id = get_project_id()
    if not project_id:
        project_id = inquirer.text(
            message="Enter GCP project ID:",
            validate=EmptyInputValidator(),
        ).execute()
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., 'project.billing_export'):",
        validate=EmptyInputValidator(),
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions to analyze (comma-separated, or press Enter for all):",
    ).execute()
    
    region_list = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output for security?",
        default=False,
    ).execute()
    
    try:
        # Initialize runner
        runner = DashboardRunner(
            project_id=project_id,
            billing_dataset=billing_dataset,
            billing_table_prefix="gcp_billing_export_v1",
            regions=region_list,
            location="US",
            hide_project_id=hide_project_id
        )
        
        print_progress("Analyzing resource utilization...")
        data = runner.run()
        analysis = llm_service.analyze_utilization(data)
        print_progress("Analysis complete", done=True)
        
        # Display results
        console.print("\n[bold cyan]Resource Utilization Analysis[/]")
        console.print(analysis)
        console.print()
        
    except Exception as e:
        print_error(f"Failed to analyze utilization: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        console.print()


# Helper functions for displaying results
def _display_dashboard_results(data):
    """Display dashboard results in a formatted way."""
    console.print("\n[bold cyan]Dashboard Results[/]")
    console.print()
    
    # Display costs
    console.print("[bold]Costs:[/]")
    console.print(f"• Current Month: ${data.current_month_cost:,.2f}")
    console.print(f"• Last Month: ${data.last_month_cost:,.2f}")
    console.print(f"• YTD: ${data.ytd_cost:,.2f}")
    console.print()
    
    # Display service costs
    console.print("[bold]Service Costs:[/]")
    for service, cost in sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True):
        console.print(f"• {service}: ${cost:,.2f}")
    console.print()
    
    # Display resource counts
    console.print("[bold]Resources:[/]")
    for result in data.audit_results.values():
        if result.total_count > 0:
            console.print(f"• {result.resource_type}:")
            console.print(f"  - Total: {result.total_count}")
            console.print(f"  - Idle: {result.idle_count}")
            console.print(f"  - Untagged: {result.untagged_count}")
    console.print()
    
    # Display potential savings
    console.print("[bold]Potential Savings:[/]")
    console.print(f"• Monthly: ${data.total_potential_savings:,.2f}")
    console.print()

def _display_audit_results(data, audit_type):
    """Display audit results in a formatted way."""
    console.print(f"\n[bold cyan]{audit_type.title()} Audit Results[/]")
    console.print()
    
    if audit_type in data.audit_results:
        result = data.audit_results[audit_type]
        console.print(f"[bold]{result.resource_type}:[/]")
        console.print(f"• Total Resources: {result.total_count}")
        console.print(f"• Idle Resources: {result.idle_count}")
        console.print(f"• Untagged Resources: {result.untagged_count}")
        console.print()
        
        if result.details:
            console.print("[bold]Details:[/]")
            for detail in result.details:
                console.print(f"• {detail}")
            console.print()

def _display_forecast_results(data):
    """Display forecast results in a formatted way."""
    console.print("\n[bold cyan]Cost Forecast[/]")
    console.print()
    
    # Display current trends
    console.print("[bold]Current Trends:[/]")
    console.print(f"• Monthly Growth Rate: {data.monthly_growth_rate:.1%}")
    console.print(f"• YoY Growth Rate: {data.yoy_growth_rate:.1%}")
    console.print()
    
    # Display projections
    console.print("[bold]Projections:[/]")
    console.print(f"• Next Month: ${data.next_month_forecast:,.2f}")
    console.print(f"• Next Quarter: ${data.next_quarter_forecast:,.2f}")
    console.print(f"• Next Year: ${data.next_year_forecast:,.2f}")
    console.print()
    
    # Display confidence intervals
    console.print("[bold]Confidence Intervals:[/]")
    console.print(f"• Next Month: ${data.next_month_low:,.2f} - ${data.next_month_high:,.2f}")
    console.print(f"• Next Quarter: ${data.next_quarter_low:,.2f} - ${data.next_quarter_high:,.2f}")
    console.print()

def _display_trend_results(data):
    """Display trend results in a formatted way."""
    console.print("\n[bold cyan]Cost Trends[/]")
    console.print()
    
    # Display month-over-month changes
    console.print("[bold]Month-over-Month Changes:[/]")
    for service, change in data.mom_changes.items():
        console.print(f"• {service}: {change:+.1%}")
    console.print()
    
    # Display year-over-year changes
    console.print("[bold]Year-over-Year Changes:[/]")
    for service, change in data.yoy_changes.items():
        console.print(f"• {service}: {change:+.1%}")
    console.print()
    
    # Display anomalies
    if data.anomalies:
        console.print("[bold]Detected Anomalies:[/]")
        for anomaly in data.anomalies:
            console.print(f"• {anomaly}")
        console.print()

def _generate_pdf_report(data):
    """Generate a PDF report from the dashboard data."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        
        # Create the PDF document
        doc = SimpleDocTemplate("finops_report.pdf", pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Add title
        title = Paragraph("GCP FinOps Dashboard Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Add costs section
        story.append(Paragraph("Costs", styles['Heading1']))
        cost_data = [
            ["Period", "Amount"],
            ["Current Month", f"${data.current_month_cost:,.2f}"],
            ["Last Month", f"${data.last_month_cost:,.2f}"],
            ["YTD", f"${data.ytd_cost:,.2f}"]
        ]
        cost_table = Table(cost_data)
        cost_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(cost_table)
        story.append(Spacer(1, 12))
        
        # Add service costs section
        story.append(Paragraph("Service Costs", styles['Heading1']))
        service_data = [["Service", "Cost"]]
        for service, cost in sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True):
            service_data.append([service, f"${cost:,.2f}"])
        service_table = Table(service_data)
        service_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(service_table)
        story.append(Spacer(1, 12))
        
        # Add resources section
        story.append(Paragraph("Resources", styles['Heading1']))
        for result in data.audit_results.values():
            if result.total_count > 0:
                resource_data = [
                    ["Metric", "Count"],
                    ["Total", str(result.total_count)],
                    ["Idle", str(result.idle_count)],
                    ["Untagged", str(result.untagged_count)]
                ]
                resource_table = Table(resource_data)
                resource_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(Paragraph(result.resource_type, styles['Heading2']))
                story.append(resource_table)
                story.append(Spacer(1, 12))
        
        # Add potential savings section
        story.append(Paragraph("Potential Savings", styles['Heading1']))
        savings_data = [
            ["Period", "Amount"],
            ["Monthly", f"${data.total_potential_savings:,.2f}"]
        ]
        savings_table = Table(savings_data)
        savings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(savings_table)
        
        # Build the PDF
        doc.build(story)
        console.print("[green]✓ PDF report generated: finops_report.pdf[/]")
        
    except ImportError:
        console.print("[red]Error: reportlab package is required for PDF generation.[/]")
        console.print("[yellow]Install with: pip install reportlab[/]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error generating PDF: {str(e)}[/]")
        raise click.Abort()


@main.command()
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Start interactive mode with menu navigation"
)
@with_heading
def setup(interactive: bool) -> None:
    """Show setup instructions or start interactive mode."""
    if interactive:
        _run_main_interactive_mode()
        return
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
    
    6. Available commands:
    
       gcp-finops dashboard     # Run complete dashboard
       gcp-finops report        # Generate PDF report
       gcp-finops audit         # Run specific audit
       gcp-finops forecast      # Generate cost forecast
       gcp-finops trend         # Display trend report
       gcp-finops run           # Run with config file support
       gcp-finops api           # Start API server
       gcp-finops setup         # Show setup instructions
       gcp-finops fonts         # Show ASCII art fonts and previews
       
       # AI-powered commands (supports Groq, OpenAI, Claude):
       gcp-finops config ai --show                    # Show AI configuration
       gcp-finops config ai --interactive             # Interactive setup with dropdowns
       gcp-finops config ai --provider groq --api-key KEY --model MODEL  # Manual setup
       gcp-finops ai analyze                          # Generate AI analysis
       gcp-finops ai ask "Why are costs high?"        # Ask questions
       gcp-finops ai summary                          # Generate executive summary
       gcp-finops ai explain-spike                    # Explain cost changes
       gcp-finops ai prioritize                       # Prioritize recommendations
       gcp-finops ai budget-suggestions               # Get budget recommendations
       gcp-finops ai utilization                      # Analyze resource utilization

    ASCII Art Configuration:
       gcp-finops fonts --list                        # List all available fonts
       gcp-finops fonts --font block                  # Preview specific font
       gcp-finops --config-file config.toml run       # Use TOML config with ASCII art settings

    For more information, see: https://github.com/your-repo/gcp-finops-dashboard
    """
    
    click.echo(instructions)


def _intercept_help_and_show_banner():
    """Intercept help requests and show banner first."""
    import sys
    
    # Check if this is a top-level help request
    if len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h']:
        # Force show banner first (bypass isatty check)
        try:
            f = pyfiglet.Figlet(font="slant")
            ascii_art = f.renderText('GCP FinOps')
            
            # Color the ASCII art with dollar-themed colors
            banner = f"""[bold bright_green]{ascii_art}[/]
[bold bright_blue]GCP FinOps Dashboard CLI (v{__version__})[/]
[dim]Cloud Run, Serverless & Cost Optimization[/]"""
            
            console.print(banner)
            check_latest_version()
        except Exception as e:
            # Fallback to simple text if pyfiglet fails
            console.print(f"[bold bright_green]GCP FinOps Dashboard CLI (v{__version__})[/]")
            console.print("[dim]Cloud Run, Serverless & Cost Optimization[/]")
            console.print(f"[dim]ASCII art disabled: {str(e)}[/]")
    
    # Call the original main function
    return main()


if __name__ == "__main__":
    _intercept_help_and_show_banner()

