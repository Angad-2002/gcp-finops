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
                show_enhanced_progress("Generating dashboard...")
                # Add dashboard generation logic
            elif choice == "report":
                show_enhanced_progress("Creating PDF report...")
                # Add report generation logic
    
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
