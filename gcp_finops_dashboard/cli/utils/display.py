"""Display utilities for CLI output."""

from typing import Any, Dict, Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from .formatting import get_ascii_art_config, get_color
try:
    import pyfiglet  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    pyfiglet = None

console = Console()

def show_enhanced_progress(message: str, done: bool = False, spinner: str = "dots") -> None:
    """Show progress with enhanced styling."""
    with Progress(
        SpinnerColumn(spinner_name=spinner),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(message, total=None)
        if done:
            progress.update(task, completed=True)

def format_ai_response(question: str, answer: str, provider: str = "", model: str = "") -> None:
    """Format AI response with rich styling and markdown support in boxed format."""
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

def welcome_banner(config_data: Optional[Dict[str, Any]] = None) -> None:
    """Display welcome banner with ASCII art and configuration.

    Honors ASCII art configuration when available; gracefully falls back to a simple banner.
    """
    subtitle = "Cost optimization and analysis tools for Google Cloud Platform"
    ascii_cfg = get_ascii_art_config(config_data)

    if ascii_cfg.get("enabled", True) and pyfiglet is not None:
        try:
            fig = pyfiglet.Figlet(font=ascii_cfg.get("font", "slant"))
            art = fig.renderText("GCP FinOps Dashboard")
            color = get_color(ascii_cfg.get("color", "blue"))
            console.print(Panel.fit(
                f"[bold {color}]" + art + f"[/bold {color}]\n[dim]{subtitle}[/dim]",
                border_style=color,
                padding=(0, 2),
            ))
            return
        except Exception:
            # Fall through to simple banner if pyfiglet/font fails
            pass

    # Simple banner fallback
    panel = Panel.fit(
        f"[bold blue]GCP FinOps Dashboard[/bold blue]\n{subtitle}",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(panel)

def display_audit_results_table(audit_name: str, result: Any) -> None:
    """Display audit results in a formatted table."""
    console.print(f"\n[bold]Results for {audit_name}:[/bold]")
    console.print(result)
