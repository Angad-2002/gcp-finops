"""Core CLI module for GCP FinOps Dashboard."""

import sys
from pathlib import Path
from typing import Optional
import click
from rich.console import Console

from .commands.dashboard import dashboard
from .commands.report import report
from .commands.audit import audit
from .commands.forecast import forecast
from .commands.trend import trend
from .commands.api import api
from .commands.fonts import fonts
from .commands.run import run
from .ai.commands import ai
from .config.manager import ConfigManager
from .utils.display import welcome_banner
from .interactive.menu import InteractiveMenu

# Initialize console for rich output
console = Console()

def init_cli():
    """Initialize CLI environment and dependencies."""
    # Add parent directory to sys.path for imports
    parent_dir = str(Path(__file__).resolve().parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

@click.group(invoke_without_command=True)
@click.option(
    "--config-file",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to configuration file",
)
@click.pass_context
def cli(ctx: click.Context, config_file: Optional[str]) -> None:
    """GCP FinOps Dashboard - Cost optimization and analysis tools for Google Cloud Platform.

    Run 'gcp-finops --help' to see all available commands.
    """
    # Initialize context object
    ctx.ensure_object(dict)
    
    # Load config if provided
    if config_file:
        config_manager = ConfigManager(config_file)
        config_data = config_manager.load_config()
        ctx.obj["config_data"] = config_data
    
    # Initialize CLI environment
    init_cli()
    
    # Always display banner at startup (matches original CLI behavior)
    try:
        config_data = ctx.obj.get("config_data") if isinstance(ctx.obj, dict) else None
        welcome_banner(config_data)
    except Exception:
        # Banner is non-critical; ignore failures to avoid blocking CLI usage
        pass
    
    # If no subcommand was invoked, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# Register commands
cli.add_command(dashboard)
cli.add_command(report)
cli.add_command(audit)
cli.add_command(forecast)
cli.add_command(trend)
cli.add_command(api)
cli.add_command(fonts)
cli.add_command(run)
cli.add_command(ai)

@cli.command()
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Start interactive mode with menu navigation",
)
def setup(interactive: bool) -> None:
    """Show setup instructions or start interactive mode."""
    if interactive:
        InteractiveMenu.run_main_menu()
    else:
        from .config.setup import show_setup_instructions
        show_setup_instructions()

def main():
    """Main entry point for the CLI."""
    try:
        cli(prog_name="gcp-finops")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()