"""Visualization module for dashboard display."""

from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich import box
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .types import DashboardData, AuditResult, OptimizationRecommendation, ForecastData, ForecastPoint
from .helpers import format_currency, format_percentage, calculate_percentage_change


console = Console()


class DashboardVisualizer:
    """Create rich terminal visualizations for the dashboard."""
    
    def __init__(self):
        """Initialize visualizer."""
        self.console = Console()
    
    def display_dashboard(self, data: DashboardData) -> None:
        """Display complete dashboard in terminal.
        
        Args:
            data: Dashboard data
        """
        # Add spacing and show header (don't clear screen to preserve banner)
        self.console.print("\n" * 2)
        self._display_header(data)
        self.console.print()
        
        # Cost summary
        self._display_cost_summary(data)
        self.console.print()
        
        # Service breakdown
        self._display_service_costs(data.service_costs)
        self.console.print()
        
        # Audit results
        self._display_audit_summary(data.audit_results)
        self.console.print()
        
        # Top recommendations
        self._display_top_recommendations(data.recommendations)
        self.console.print()
        
        # Savings summary
        self._display_savings_summary(data.total_potential_savings)
    
    def _display_header(self, data: DashboardData) -> None:
        """Display dashboard header."""
        header_text = Text()
        header_text.append("GCP FinOps Dashboard\n", style="bold cyan")
        if not data.hide_project_id:
            header_text.append(f"Project: {data.project_id}\n", style="white")
        else:
            header_text.append("Project: [HIDDEN]\n", style="dim white")
        header_text.append(f"Billing Period: {data.billing_month}", style="dim white")
        
        panel = Panel(
            header_text,
            title="💰 Cost Optimization Dashboard",
            border_style="cyan",
            box=box.DOUBLE
        )
        self.console.print(panel)
    
    def _display_cost_summary(self, data: DashboardData) -> None:
        """Display cost summary."""
        # Calculate change
        change = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        change_symbol = "↑" if change > 0 else "↓" if change < 0 else "→"
        change_color = "red" if change > 0 else "green" if change < 0 else "yellow"
        
        table = Table(title="💰 Cost Summary", box=box.ROUNDED, show_header=False)
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="white", width=30)
        
        table.add_row(
            "Current Month",
            f"[bold]{format_currency(data.current_month_cost)}[/bold] "
            f"[{change_color}]{change_symbol} {format_percentage(abs(change))}[/{change_color}]"
        )
        table.add_row("Last Month", format_currency(data.last_month_cost))
        table.add_row("Year-to-Date", f"[bold]{format_currency(data.ytd_cost)}[/bold]")
        
        self.console.print(table)
    
    def _display_service_costs(self, service_costs: Dict[str, float]) -> None:
        """Display service cost breakdown."""
        if not service_costs:
            return
        
        total = sum(service_costs.values())
        
        table = Table(title="📊 Top Services by Cost", box=box.ROUNDED)
        table.add_column("Rank", style="dim", width=6)
        table.add_column("Service", style="cyan", width=30)
        table.add_column("Cost", style="white", justify="right", width=15)
        table.add_column("% of Total", style="yellow", justify="right", width=12)
        
        for i, (service, cost) in enumerate(sorted(service_costs.items(), key=lambda x: x[1], reverse=True), 1):
            percentage = (cost / total) * 100 if total > 0 else 0
            table.add_row(
                f"{i}.",
                service,
                format_currency(cost),
                format_percentage(percentage)
            )
        
        self.console.print(table)
    
    def _display_audit_summary(self, audit_results: Dict[str, AuditResult]) -> None:
        """Display audit summary."""
        if not audit_results:
            return
        
        table = Table(title="🔍 Resource Audit Summary", box=box.ROUNDED)
        table.add_column("Resource Type", style="cyan", width=20)
        table.add_column("Total", style="white", justify="center", width=8)
        table.add_column("Untagged", style="yellow", justify="center", width=10)
        table.add_column("Idle", style="red", justify="center", width=8)
        table.add_column("Over-provisioned", style="orange1", justify="center", width=16)
        table.add_column("Potential Savings", style="green", justify="right", width=16)
        
        for resource_type, result in audit_results.items():
            table.add_row(
                resource_type.replace("_", " ").title(),
                str(result.total_count),
                f"[yellow]{result.untagged_count}[/yellow]" if result.untagged_count > 0 else "0",
                f"[red]{result.idle_count}[/red]" if result.idle_count > 0 else "0",
                f"[orange1]{result.over_provisioned_count}[/orange1]" if result.over_provisioned_count > 0 else "0",
                format_currency(result.potential_monthly_savings)
            )
        
        self.console.print(table)
    
    def _display_top_recommendations(self, recommendations: List[OptimizationRecommendation], top_n: int = 10) -> None:
        """Display top optimization recommendations."""
        if not recommendations:
            self.console.print("[dim]No optimization recommendations at this time.[/dim]")
            return
        
        # Sort by potential savings
        sorted_recs = sorted(recommendations, key=lambda r: r.potential_monthly_savings, reverse=True)[:top_n]
        
        table = Table(title="💡 Top Optimization Opportunities", box=box.ROUNDED)
        table.add_column("Priority", style="white", width=8)
        table.add_column("Resource", style="cyan", width=25)
        table.add_column("Issue", style="yellow", width=35)
        table.add_column("Monthly Savings", style="green", justify="right", width=15)
        
        for rec in sorted_recs:
            # Priority color
            priority_color = {
                "high": "red",
                "medium": "yellow",
                "low": "blue"
            }.get(rec.priority, "white")
            
            table.add_row(
                f"[{priority_color}]{rec.priority.upper()}[/{priority_color}]",
                f"{rec.resource_name}\n[dim]{rec.region}[/dim]",
                rec.issue,
                format_currency(rec.potential_monthly_savings)
            )
        
        self.console.print(table)
    
    def _display_savings_summary(self, total_savings: float) -> None:
        """Display total potential savings."""
        text = Text()
        text.append("💸 Total Potential Monthly Savings: ", style="bold white")
        text.append(format_currency(total_savings), style="bold green")
        
        if total_savings > 100:
            text.append(f"\n   (", style="dim")
            text.append(f"~{format_currency(total_savings * 12)}/year", style="bold green")
            text.append(")", style="dim")
        
        panel = Panel(
            text,
            border_style="green",
            box=box.DOUBLE
        )
        self.console.print(panel)
    
    def display_detailed_recommendations(self, recommendations: List[OptimizationRecommendation]) -> None:
        """Display detailed recommendations with actions.
        
        Args:
            recommendations: List of recommendations
        """
        if not recommendations:
            self.console.print("[dim]No recommendations available.[/dim]")
            return
        
        # Group by resource type
        by_type: Dict[str, List[OptimizationRecommendation]] = {}
        for rec in recommendations:
            if rec.resource_type not in by_type:
                by_type[rec.resource_type] = []
            by_type[rec.resource_type].append(rec)
        
        for resource_type, recs in by_type.items():
            self.console.print(f"\n[bold cyan]{resource_type.replace('_', ' ').title()}[/bold cyan]")
            self.console.print("─" * 80)
            
            for rec in sorted(recs, key=lambda r: r.potential_monthly_savings, reverse=True):
                self.console.print(f"\n[yellow]●[/yellow] {rec.resource_name} ({rec.region})")
                self.console.print(f"  Issue: {rec.issue}")
                self.console.print(f"  [green]→[/green] {rec.recommendation}")
                self.console.print(f"  [bold green]Savings: {format_currency(rec.potential_monthly_savings)}/month[/bold green]")
    
    def display_forecast(self, forecast_data: ForecastData) -> None:
        """Display cost forecast in terminal.
        
        Args:
            forecast_data: Forecast data from ForecastService
        """
        if not forecast_data.forecast_points:
            self.console.print("[yellow]⚠ No forecast data available. Insufficient historical data.[/yellow]")
            return
        
        # Add spacing
        self.console.print("\n" * 2)
        
        # Display forecast header
        header_text = Text()
        header_text.append("🔮 GCP Cost Forecast\n", style="bold cyan")
        header_text.append(f"Forecast Period: {forecast_data.forecast_days} days\n", style="white")
        header_text.append(f"Generated: {forecast_data.generated_at[:19]}", style="dim white")
        
        panel = Panel(
            header_text,
            title="💰 Cost Forecasting Dashboard",
            border_style="cyan",
            box=box.DOUBLE
        )
        self.console.print(panel)
        self.console.print()
        
        # Display forecast summary
        self._display_forecast_summary(forecast_data)
        self.console.print()
        
        # Display forecast chart (similar to AWS trend bars)
        self._display_forecast_chart(forecast_data)
        self.console.print()
        
        # Display confidence and trend info
        self._display_forecast_metadata(forecast_data)
    
    def _display_forecast_summary(self, forecast_data: ForecastData) -> None:
        """Display forecast summary table."""
        table = Table(title="📊 Forecast Summary", box=box.ROUNDED, show_header=False)
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="white", width=30)
        
        # Trend color
        trend_color = {
            "increasing": "red",
            "decreasing": "green", 
            "stable": "yellow",
            "unknown": "dim"
        }.get(forecast_data.trend, "white")
        
        table.add_row(
            "Total Predicted Cost",
            f"[bold]{format_currency(forecast_data.total_predicted_cost)}[/bold]"
        )
        table.add_row(
            "Trend",
            f"[{trend_color}]{forecast_data.trend.upper()}[/{trend_color}]"
        )
        table.add_row(
            "Model Confidence",
            f"[bold]{forecast_data.model_confidence:.1%}[/bold]"
        )
        table.add_row(
            "Daily Average",
            f"[bold]{format_currency(forecast_data.total_predicted_cost / forecast_data.forecast_days)}[/bold]"
        )
        
        self.console.print(table)
    
    def _display_forecast_chart(self, forecast_data: ForecastData) -> None:
        """Display forecast chart with bars (similar to AWS trend visualization)."""
        if not forecast_data.forecast_points:
            return
        
        # Group forecast points by week for better visualization
        weekly_data = self._group_forecast_by_week(forecast_data.forecast_points)
        
        table = Table(box=None, padding=(1, 1), collapse_padding=True)
        table.add_column("Week", style="bright_magenta", width=12)
        table.add_column("Predicted Cost", style="bright_cyan", justify="right", width=18)
        table.add_column("", width=50)
        table.add_column("Confidence", style="bright_yellow", width=12)
        
        max_cost = max(week_cost for _, week_cost, _ in weekly_data)
        if max_cost == 0:
            self.console.print("[yellow]All predicted costs are $0.00[/yellow]")
            return
        
        for week_label, week_cost, avg_confidence in weekly_data:
            bar_length = int((week_cost / max_cost) * 40) if max_cost > 0 else 0
            bar = "█" * bar_length
            
            # Color based on cost level
            if week_cost > max_cost * 0.8:
                bar_color = "bright_red"
            elif week_cost > max_cost * 0.6:
                bar_color = "yellow"
            else:
                bar_color = "bright_green"
            
            confidence_color = "green" if avg_confidence > 0.8 else "yellow" if avg_confidence > 0.6 else "red"
            
            table.add_row(
                week_label,
                f"${week_cost:,.2f}",
                f"[{bar_color}]{bar}[/]",
                f"[{confidence_color}]{avg_confidence:.1%}[/{confidence_color}]"
            )
        
        self.console.print(
            Panel(
                table,
                title="[cyan]GCP Cost Forecast Chart[/]",
                border_style="bright_blue",
                padding=(1, 1),
            )
        )
    
    def _display_forecast_metadata(self, forecast_data: ForecastData) -> None:
        """Display forecast metadata and recommendations."""
        # Confidence interpretation
        confidence_level = "High" if forecast_data.model_confidence > 0.8 else "Medium" if forecast_data.model_confidence > 0.6 else "Low"
        confidence_color = "green" if forecast_data.model_confidence > 0.8 else "yellow" if forecast_data.model_confidence > 0.6 else "red"
        
        # Trend interpretation
        trend_emoji = {
            "increasing": "📈",
            "decreasing": "📉", 
            "stable": "➡️",
            "unknown": "❓"
        }.get(forecast_data.trend, "❓")
        
        metadata_text = Text()
        metadata_text.append(f"Model Confidence: ", style="white")
        metadata_text.append(f"{confidence_level} ({forecast_data.model_confidence:.1%})", style=confidence_color)
        metadata_text.append(f"\nTrend: ", style="white")
        metadata_text.append(f"{trend_emoji} {forecast_data.trend.upper()}", style="cyan")
        
        if forecast_data.trend == "increasing":
            metadata_text.append(f"\n\n💡 Recommendation: Consider setting budget alerts at ", style="yellow")
            metadata_text.append(f"${forecast_data.total_predicted_cost * 1.1:,.2f}", style="bold yellow")
            metadata_text.append(f" (+10% buffer)", style="yellow")
        elif forecast_data.trend == "decreasing":
            metadata_text.append(f"\n\n✅ Good news: Costs are trending downward!", style="green")
        else:
            metadata_text.append(f"\n\n📊 Costs appear stable. Monitor for any changes.", style="blue")
        
        panel = Panel(
            metadata_text,
            title="🔍 Forecast Analysis",
            border_style="blue",
            box=box.ROUNDED
        )
        self.console.print(panel)
    
    def _group_forecast_by_week(self, forecast_points: List[ForecastPoint]) -> List[tuple]:
        """Group forecast points by week for better visualization."""
        from datetime import datetime
        
        weekly_data = []
        current_week = []
        current_week_start = None
        
        for point in forecast_points:
            date = datetime.strptime(point.date, '%Y-%m-%d')
            week_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if current_week_start is None:
                current_week_start = week_start
                current_week = [point]
            elif (week_start - current_week_start).days >= 7:
                # Process current week
                week_cost = sum(p.predicted_cost for p in current_week)
                week_confidence = sum(p.predicted_cost for p in current_week) / len(current_week) if current_week else 0
                week_label = f"Week {len(weekly_data) + 1}"
                weekly_data.append((week_label, week_cost, 0.8))  # Simplified confidence
                
                # Start new week
                current_week_start = week_start
                current_week = [point]
            else:
                current_week.append(point)
        
        # Process last week
        if current_week:
            week_cost = sum(p.predicted_cost for p in current_week)
            week_label = f"Week {len(weekly_data) + 1}"
            weekly_data.append((week_label, week_cost, 0.8))  # Simplified confidence
        
        return weekly_data


class ChartGenerator:
    """Generate Plotly charts for reports."""
    
    @staticmethod
    def create_cost_trend_chart(monthly_data: List[tuple], service_name: str = "Total") -> go.Figure:
        """Create cost trend chart.
        
        Args:
            monthly_data: List of (month, cost) tuples
            service_name: Service name for chart title
        
        Returns:
            Plotly figure
        """
        if not monthly_data:
            return go.Figure()
        
        months = [m[0] for m in monthly_data]
        costs = [m[1] for m in monthly_data]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=months,
            y=costs,
            mode='lines+markers',
            name=service_name,
            line=dict(color='#00bfff', width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title=f"{service_name} - Monthly Cost Trend",
            xaxis_title="Month",
            yaxis_title="Cost (USD)",
            template="plotly_white",
            hovermode='x unified'
        )
        
        return fig
    
    @staticmethod
    def create_service_breakdown_chart(service_costs: Dict[str, float]) -> go.Figure:
        """Create service cost breakdown pie chart.
        
        Args:
            service_costs: Dictionary of service names to costs
        
        Returns:
            Plotly figure
        """
        if not service_costs:
            return go.Figure()
        
        labels = list(service_costs.keys())
        values = list(service_costs.values())
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.3,
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig.update_layout(
            title="Cost Breakdown by Service",
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_savings_chart(audit_results: Dict[str, AuditResult]) -> go.Figure:
        """Create potential savings bar chart.
        
        Args:
            audit_results: Dictionary of audit results
        
        Returns:
            Plotly figure
        """
        if not audit_results:
            return go.Figure()
        
        resources = [r.replace("_", " ").title() for r in audit_results.keys()]
        savings = [result.potential_monthly_savings for result in audit_results.values()]
        
        fig = go.Figure(data=[go.Bar(
            x=resources,
            y=savings,
            marker_color='lightgreen'
        )])
        
        fig.update_layout(
            title="Potential Monthly Savings by Resource Type",
            xaxis_title="Resource Type",
            yaxis_title="Potential Savings (USD/month)",
            template="plotly_white"
        )
        
        return fig


def print_progress(message: str, done: bool = False) -> None:
    """Print progress message.
    
    Args:
        message: Progress message
        done: Whether the task is complete
    """
    if done:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[cyan]⋯[/cyan] {message}")


def print_error(message: str) -> None:
    """Print error message.
    
    Args:
        message: Error message
    """
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print warning message.
    
    Args:
        message: Warning message
    """
    console.print(f"[yellow]⚠[/yellow] {message}")

