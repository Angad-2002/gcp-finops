"""Dashboard command module."""

from typing import Optional
import click
from ..utils.display import show_enhanced_progress
from .base import BaseCommand

class DashboardCommand(BaseCommand):
    """Dashboard command implementation."""
    
    def run(self):
        """Run the dashboard command."""
        show_enhanced_progress("Initializing BigQuery client...")
        self.init_bigquery()
        
        show_enhanced_progress("Fetching cost data...")
        # Add your dashboard data fetching logic here
        
        show_enhanced_progress("Generating dashboard...", done=True)
        # Add your dashboard generation logic here

@click.command()
@BaseCommand.common_options
@click.pass_context
def dashboard(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
) -> None:
    """Generate an interactive cost analysis dashboard."""
    cmd = DashboardCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
    )
    cmd.run()
