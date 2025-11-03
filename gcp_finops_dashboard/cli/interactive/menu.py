"""Interactive menu system for CLI."""

from typing import Optional, Dict, Any
from InquirerPy import inquirer
from rich.console import Console
from ..utils.display import show_enhanced_progress
from ..ai.service import get_llm_service
from .workflows import (
    run_forecast_interactive_mode,
    run_config_interactive_mode,
    run_quick_setup,
    show_setup_instructions,
    run_ai_chat_interactive_mode,
    run_ai_analyze_interactive_mode,
    run_ai_summary_interactive_mode,
    run_ai_explain_spike_interactive_mode,
    run_ai_budget_suggestions_interactive_mode,
    run_audit_interactive_mode,
    run_ai_config_interactive,
)
from .workflows.rag import (
    run_rag_chat_interactive,
    run_upload_document_interactive,
    run_list_documents_interactive,
    run_delete_document_interactive,
)
from .utils.context import prompt_common_context
from ...dashboard_runner import DashboardRunner
from ...utils.visualizations import print_progress, print_error, DashboardVisualizer
from ...helpers import get_project_id
from ...pdf_utils import ReportGenerator
from ...api.config import REPORTS_DIR
from ..ai.service import LLMService

console = Console()

class InteractiveMenu:
    """Interactive menu system."""
    
    @staticmethod
    def run_main_menu():
        """Run the main interactive menu."""
        console.print("[bold cyan]GCP FinOps Dashboard - Interactive Mode[/]")
        console.print("[dim]Navigate through different sections and commands[/]")
        console.print()
        
        while True:
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
            
            # Normalize tuple results (match original CLI behavior)
            if isinstance(main_choice, tuple):
                main_choice = main_choice[1]
            
            if main_choice == "exit":
                console.print("[yellow]Goodbye![/]")
                break
            elif main_choice == "dashboard":
                InteractiveMenu.run_dashboard_menu()
            elif main_choice == "audit":
                InteractiveMenu.run_audit_menu()
            elif main_choice == "forecast":
                InteractiveMenu.run_forecast_menu()
            elif main_choice == "ai":
                InteractiveMenu.run_ai_menu()
            elif main_choice == "config":
                InteractiveMenu.run_config_menu()
            elif main_choice == "quick-setup":
                InteractiveMenu.run_quick_setup()
            elif main_choice == "help":
                InteractiveMenu.show_help_menu()
    
    @staticmethod
    def run_dashboard_menu():
        """Run dashboard section menu."""
        while True:
            choice = inquirer.select(
                message="Dashboard & Reports:",
                choices=[
                    ("Generate Interactive Dashboard", "dashboard"),
                    ("Create PDF Report", "report"),
                    ("Back to Main Menu", "back")
                ]
            ).execute()
            
            # Normalize tuple results
            if isinstance(choice, tuple):
                choice = choice[1]
            
            if choice == "back":
                break
            elif choice == "dashboard":
                InteractiveMenu._run_dashboard_interactive()
            elif choice == "report":
                InteractiveMenu._run_report_interactive()
    
    @staticmethod
    def _run_dashboard_interactive():
        """Run interactive dashboard generation."""
        # Collect common parameters
        ctx = prompt_common_context()
        
        # Get project ID if not provided
        if not ctx["project_id"]:
            ctx["project_id"] = get_project_id()
            if not ctx["project_id"]:
                print_error("Project ID is required. Please specify it.")
                return
        
        try:
            # Initialize runner
            runner = DashboardRunner(
                project_id=ctx["project_id"],
                billing_dataset=ctx["billing_dataset"],
                billing_table_prefix="gcp_billing_export_v1",
                regions=ctx["regions"],
                location=ctx["location"],
                hide_project_id=ctx["hide_project_id"]
            )
            
            # Run dashboard
            print_progress("Running dashboard analysis...")
            data = runner.run()
            print_progress("Dashboard complete", done=True)
            
            # Display dashboard
            visualizer = DashboardVisualizer()
            visualizer.display_dashboard(data)
            
            # Add pause before returning to menu
            console.print("\n[dim]Press Enter to continue...[/dim]")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass
                
        except Exception as e:
            print_error(f"Dashboard generation failed: {str(e)}")
            console.print("[yellow]Please check your configuration and try again.[/]")
    
    @staticmethod
    def _run_report_interactive():
        """Run interactive PDF report generation."""
        # Collect common parameters
        ctx = prompt_common_context()
        
        # Get project ID if not provided
        if not ctx["project_id"]:
            ctx["project_id"] = get_project_id()
            if not ctx["project_id"]:
                print_error("Project ID is required. Please specify it.")
                return
        
        try:
            # Initialize runner
            runner = DashboardRunner(
                project_id=ctx["project_id"],
                billing_dataset=ctx["billing_dataset"],
                billing_table_prefix="gcp_billing_export_v1",
                regions=ctx["regions"],
                location=ctx["location"],
                hide_project_id=ctx["hide_project_id"]
            )
            
            # Run dashboard to get data
            print_progress("Generating report data...")
            data = runner.run()
            print_progress("Report data ready", done=True)
            
            # Generate PDF report
            print_progress("Creating PDF report...")
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"gcp-finops-report-{timestamp}.pdf"
            output_path = REPORTS_DIR / filename
            
            report_gen = ReportGenerator(output_dir=str(REPORTS_DIR))
            report_gen.generate_report(data, str(output_path))
            print_progress("PDF report created", done=True)
            
            console.print(f"\n[green]✓[/] Report saved to [cyan]{output_path.resolve()}[/]")
            
            # Add pause before returning to menu
            console.print("\n[dim]Press Enter to continue...[/dim]")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass
                
        except Exception as e:
            print_error(f"Report generation failed: {str(e)}")
            console.print("[yellow]Please check your configuration and try again.[/]")
    
    @staticmethod
    def run_ai_menu():
        """Run AI section menu."""
        # Get LLM service with proper error handling
        llm_service = get_llm_service()
        ai_available = llm_service is not None
        
        if not ai_available:
            console.print("[red]AI features not available. API key not configured.[/]")
            console.print("[yellow]You can configure AI settings from this menu.[/]")
            console.print()
        
        while True:
            choice = inquirer.select(
                message="AI-Powered Insights:",
                choices=[
                    ("Generate Cost Analysis", "analyze"),
                    ("Ask Questions", "ask"),
                    ("Generate Executive Summary", "summary"),
                    ("Explain Cost Spikes", "explain-spike"),
                    ("Get Budget Suggestions", "budget"),
                    ("Document Chat (RAG)", "rag"),
                    ("Configure AI Settings", "config"),
                    ("Back to Main Menu", "back")
                ]
            ).execute()
            
            # Normalize tuple results
            if isinstance(choice, tuple):
                choice = choice[1]
            
            if choice == "back":
                break
            elif choice == "config":
                run_ai_config_interactive()
                # Refresh LLM service after configuration
                llm_service = get_llm_service()
                ai_available = llm_service is not None
            elif choice == "ask":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_chat_interactive_mode(llm_service)
            elif choice == "analyze":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_analyze_interactive_mode(llm_service)
            elif choice == "summary":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_summary_interactive_mode(llm_service)
            elif choice == "explain-spike":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_explain_spike_interactive_mode(llm_service)
            elif choice == "budget":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_budget_suggestions_interactive_mode(llm_service)
            elif choice == "rag":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                InteractiveMenu._run_rag_menu()
    
    @staticmethod
    def _run_rag_menu():
        """Run RAG (Document Chat) menu."""
        while True:
            choice = inquirer.select(
                message="Document Chat (RAG):",
                choices=[
                    ("Chat with Documents", "chat"),
                    ("Upload PDF Document", "upload"),
                    ("List Uploaded Documents", "list"),
                    ("Delete Document", "delete"),
                    ("Back to AI Menu", "back")
                ]
            ).execute()
            
            # Normalize tuple results
            if isinstance(choice, tuple):
                choice = choice[1]
            
            if choice == "back":
                break
            elif choice == "chat":
                run_rag_chat_interactive()
            elif choice == "upload":
                run_upload_document_interactive()
            elif choice == "list":
                run_list_documents_interactive()
            elif choice == "delete":
                run_delete_document_interactive()
    
    @staticmethod
    def run_audit_menu():
        """Run audit section menu."""
        while True:
            choice = inquirer.select(
                message="Audits & Analysis:",
                choices=[
                    ("Cloud Run Audit", "cloudrun"),
                    ("Cloud Functions Audit", "functions"),
                    ("Compute Engine Audit", "compute"),
                    ("Cloud SQL Audit", "sql"),
                    ("Disk Audit", "disk"),
                    ("IP Address Audit", "ip"),
                    ("Run All Audits", "all"),
                    ("Back to Main Menu", "back"),
                ],
            ).execute()
            
            # Normalize tuple results
            if isinstance(choice, tuple):
                choice = choice[1]
            
            if choice == "back":
                break
            else:
                # Execute the selected audit
                run_audit_interactive_mode(choice)
    
    @staticmethod
    def run_forecast_menu():
        """Run forecast & trends section menu (delegates to prompts)."""
        run_forecast_interactive_mode()
    
    @staticmethod
    def run_config_menu():
        """Run configuration & setup menu (delegates to prompts)."""
        run_config_interactive_mode()
    
    @staticmethod
    def run_quick_setup():
        """Run quick setup wizard (delegates to prompts)."""
        run_quick_setup()
    
    @staticmethod
    def show_help_menu():
        """Show help & documentation."""
        show_setup_instructions()
