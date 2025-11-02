"""AI-powered interactive workflows."""

from typing import Optional
from InquirerPy import inquirer
from rich.console import Console
from ...ai.service import LLMService
from ....dashboard_runner import DashboardRunner
from ....utils.visualizations import print_progress, print_error, DashboardVisualizer
from ..utils.context import prompt_common_context
from ..utils.export import prompt_save_and_export
from ...utils.formatting import format_ai_output

console = Console()

def run_ai_chat_interactive_mode(llm_service: LLMService) -> None:
    """Run AI chat interactive mode with dashboard data context."""
    console.print("[bold cyan]Interactive AI Question Mode[/]")
    console.print()
    
    # Collect billing dataset and context
    ctx = prompt_common_context()
    
    try:
        # Initialize runner with the collected parameters
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Run analysis to collect data
        print_progress("Analyzing GCP resources and costs...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        console.print(f"[green]✓[/] Analysis complete! You can now ask questions about your GCP costs and resources.")
        console.print(f"[dim]Provider: {llm_service.provider} | Model: {llm_service.model}[/]")
        console.print()
        
        # Conversation loop
        conversation_history = []
        while True:
            # Get question from user
            question = inquirer.text(
                message="Ask a question about your GCP costs (or type 'back', 'main', or 'quit'):",
            ).execute()
            
            if not question.strip():
                continue
            
            # Check for navigation commands
            if question.lower().strip() in ['quit', 'exit', 'q']:
                console.print("[yellow]Goodbye![/]")
                break
            elif question.lower().strip() in ['back']:
                console.print("[yellow]Returning to AI menu...[/]")
                break
            elif question.lower().strip() in ['main']:
                console.print("[yellow]Returning to main menu...[/]")
                break
            
            try:
                # Add context from conversation history
                context = ""
                if conversation_history:
                    context = "\n\nPrevious conversation:\n" + "\n".join(conversation_history[-3:])  # Last 3 exchanges
                
                # Get AI answer using answer_question with dashboard data
                print_progress("Getting AI answer...")
                answer = llm_service.answer_question(question, data, context=context)
                print_progress("AI answer ready", done=True)
                
                # Display results with enhanced formatting
                from ...utils.display import format_ai_response
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

def run_ai_analyze_interactive_mode(llm_service: LLMService) -> None:
    """Run interactive AI analyze workflow (collects billing dataset, etc.)."""
    ctx = prompt_common_context()
    try:
        # Initialize runner with the collected parameters
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Run analysis to collect data
        print_progress("Running dashboard analysis...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Generate AI analysis
        print_progress("Generating AI insights...")
        analysis_result = llm_service.analyze_dashboard_data(data)
        print_progress("AI analysis ready", done=True)
        
        # Display AI analysis
        format_ai_output("🔍 AI Analysis", analysis_result['analysis'], llm_service.provider, llm_service.model)
        
        # Prompt to save
        prompt_save_and_export(data, analysis_result['analysis'], default_base="gcp-finops-analysis")
        
    except Exception as e:
        print_error(f"Failed to run analysis: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

def run_ai_summary_interactive_mode(llm_service: LLMService) -> None:
    """Run interactive AI executive summary workflow."""
    ctx = prompt_common_context()
    try:
        # Initialize runner with the collected parameters
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Run analysis to collect data
        print_progress("Running dashboard analysis...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Generate executive summary
        print_progress("Generating executive summary...")
        summary = llm_service.generate_executive_summary(data)
        print_progress("Executive summary ready", done=True)
        
        # Display AI summary
        format_ai_output("📋 Executive Summary", summary, llm_service.provider, llm_service.model)
        
        # Prompt to save
        prompt_save_and_export(data, summary, default_base="gcp-finops-summary")
        
    except Exception as e:
        print_error(f"Failed to generate summary: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

def run_ai_explain_spike_interactive_mode(llm_service: LLMService) -> None:
    """Run interactive AI explain-spike workflow."""
    ctx = prompt_common_context()
    try:
        # Initialize runner with the collected parameters
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Run analysis to collect data
        print_progress("Running dashboard analysis...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Explain cost spike
        print_progress("Analyzing cost changes...")
        explanation = llm_service.explain_cost_spike(data)
        print_progress("Cost analysis complete", done=True)
        
        # Display AI explanation
        format_ai_output("📈 Cost Spike Analysis", explanation, llm_service.provider, llm_service.model)
        
        # Prompt to save
        prompt_save_and_export(data, explanation, default_base="gcp-finops-explain-spike")
        
    except Exception as e:
        print_error(f"Failed to explain cost spike: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

def run_ai_budget_suggestions_interactive_mode(llm_service: LLMService) -> None:
    """Run interactive AI budget suggestions workflow."""
    ctx = prompt_common_context()
    try:
        # Initialize runner with the collected parameters
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Run analysis to collect data
        print_progress("Running dashboard analysis...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Generate budget suggestions
        print_progress("Analyzing spending patterns...")
        suggestions = llm_service.suggest_budget_alerts(data)
        print_progress("Budget analysis complete", done=True)
        
        # Display AI suggestions
        format_ai_output("💰 Budget Suggestions", suggestions, llm_service.provider, llm_service.model)
        
        # Prompt to save
        prompt_save_and_export(data, suggestions, default_base="gcp-finops-budget")
        
    except Exception as e:
        print_error(f"Failed to generate budget suggestions: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

