"""API server command module."""

import click
from rich.console import Console
import uvicorn
from ..utils.display import show_enhanced_progress

# Import the modular API app
from ...api.main import app, start_api_server

console = Console()

# CLI Command
@click.command()
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port for API server (default: 8000)",
)
def api(port: int) -> None:
    """Start the API server for programmatic access."""
    show_enhanced_progress("Starting API server...")
    try:
        start_api_server(host="0.0.0.0", port=port)
    except Exception as e:
        console.print(f"[red]Error starting API server: {str(e)}[/]")
        raise click.Abort()
