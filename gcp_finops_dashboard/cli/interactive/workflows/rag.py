"""RAG (Retrieval Augmented Generation) interactive workflows."""

from pathlib import Path
from typing import Optional
from collections import defaultdict
from InquirerPy import inquirer
from rich.console import Console
from rich.table import Table
from ....services.rag.service import RAGService
from ...ai.service import get_llm_service

console = Console()

# Global RAG service instance
_rag_service: Optional[RAGService] = None

def get_rag_service() -> Optional[RAGService]:
    """Get or create RAG service instance."""
    global _rag_service
    if _rag_service is None:
        try:
            _rag_service = RAGService()
        except Exception as e:
            console.print(f"[red]Failed to initialize RAG service: {e}[/]")
            return None
    return _rag_service

def run_rag_chat_interactive() -> None:
    """Run RAG-based chat with uploaded documents."""
    llm_service = get_llm_service()
    if not llm_service:
        console.print("[red]AI service not available. Please configure AI settings first.[/]")
        return
    
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available. Install required packages: pip install sentence-transformers chromadb pypdf[/]")
        return
    
    # Check if any documents are uploaded
    documents = rag_service.get_documents()
    if not documents:
        console.print("[yellow]No documents uploaded yet. Please upload PDFs first.[/]")
        return
    
    console.print("[bold cyan]RAG Chat Mode[/]")
    console.print(f"[dim]Using {len(documents)} uploaded document(s) for context[/]")
    console.print(f"[dim]Provider: {llm_service.provider} | Model: {llm_service.model}[/]")
    console.print()
    
    conversation_history = []
    while True:
        question = inquirer.text(
            message="Ask a question about your documents (or type 'back', 'main', or 'quit'):",
        ).execute()
        
        if not question.strip():
            continue
        
        # Check for navigation commands
        if question.lower().strip() in ['quit', 'exit', 'q']:
            console.print("[yellow]Goodbye![/]")
            break
        elif question.lower().strip() in ['back']:
            console.print("[yellow]Returning to RAG menu...[/]")
            break
        elif question.lower().strip() in ['main']:
            console.print("[yellow]Returning to main menu...[/]")
            break
        
        try:
            # Search for relevant chunks
            console.print("[dim]Searching documents...[/]")
            relevant_chunks = rag_service.search(question, top_k=5)
            
            if not relevant_chunks:
                console.print("[yellow]No relevant information found in documents.[/]")
                answer = "I couldn't find relevant information in your uploaded documents to answer this question."
            else:
                # Group chunks by document_id to avoid duplicate document references
                document_groups = defaultdict(list)
                for chunk in relevant_chunks:
                    metadata = chunk.get('metadata') or {}
                    doc_id = metadata.get('document_id', 'unknown')
                    source = metadata.get('source', 'Unknown')
                    document_groups[(doc_id, source)].append(chunk.get('text', ''))
                
                # Build context from grouped documents
                context_parts = []
                for i, ((doc_id, source), chunks) in enumerate(document_groups.items(), 1):
                    source_name = Path(source).name if source != 'Unknown' else 'Unknown'
                    # Combine all chunks from the same document
                    combined_text = "\n\n".join(chunks)
                    context_parts.append(f"Document {i}: {source_name}\n{combined_text}")
                
                context = "\n\n".join(context_parts)
                
                # Build prompt with context
                prompt = f"""Based on the following context from uploaded documents, please answer the user's question.

Context from documents:
{context}

User question: {question}

Please provide a clear, accurate answer based on the document context. If the context doesn't contain enough information to fully answer the question, say so."""
                
                # Add conversation history
                if conversation_history:
                    history_text = "\n\nPrevious conversation:\n" + "\n".join(conversation_history[-3:])
                    prompt += history_text
                
                # Get answer from LLM
                console.print("[dim]Generating answer...[/]")
                answer = llm_service._call_llm(prompt, max_tokens=800, temperature=0.6, is_chat=True)
            
            # Display results with enhanced formatting (same as AI chat)
            from ...utils.display import format_ai_response
            format_ai_response(question, answer, llm_service.provider, llm_service.model)
            
            # Store in conversation history
            conversation_history.append(f"Q: {question}")
            conversation_history.append(f"A: {answer}")
            
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/]")
            console.print()

def run_upload_document_interactive() -> None:
    """Upload a PDF document interactively."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available. Install required packages: pip install sentence-transformers chromadb pypdf[/]")
        return
    
    console.print("[bold cyan]Upload Document[/]")
    console.print()
    
    # Get file path
    file_path = inquirer.filepath(
        message="Enter path to PDF file:",
    ).execute()
    
    if not file_path:
        return
    
    # Validate file exists
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        console.print(f"[red]Error: File does not exist: {file_path}[/]")
        return
    
    try:
        console.print("[dim]Processing PDF...[/]")
        result = rag_service.upload_pdf(file_path)
        
        if result.get("success"):
            console.print(f"[green]✓[/] Document uploaded successfully!")
            console.print(f"  Filename: {result['filename']}")
            console.print(f"  Chunks: {result['chunks']}")
            console.print(f"  Document ID: {result['document_id']}")
        else:
            error = result.get("error", "Unknown error")
            console.print(f"[red]✗[/] Upload failed: {error}")
    except Exception as e:
        console.print(f"[red]Error uploading document: {str(e)}[/]")

def run_list_documents_interactive() -> None:
    """List uploaded documents."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available.[/]")
        return
    
    documents = rag_service.get_documents()
    
    if not documents:
        console.print("[yellow]No documents uploaded yet.[/]")
        return
    
    console.print(f"[bold cyan]Uploaded Documents ({len(documents)}):[/]")
    console.print()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=15)
    table.add_column("Filename", style="green")
    table.add_column("Chunks", justify="right", width=10)
    table.add_column("Uploaded", style="dim", width=20)
    
    for doc in documents:
        table.add_row(
            doc.get("id", "N/A"),
            doc.get("filename", "N/A"),
            str(doc.get("chunks", 0)),
            doc.get("uploaded_at", "N/A")[:16] if doc.get("uploaded_at") else "N/A"
        )
    
    console.print(table)
    console.print()

def run_delete_document_interactive() -> None:
    """Delete a document interactively."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available.[/]")
        return
    
    documents = rag_service.get_documents()
    
    if not documents:
        console.print("[yellow]No documents to delete.[/]")
        return
    
    # Let user select document to delete
    choices = [
        (f"{doc['filename']} ({doc['id']})", doc['id'])
        for doc in documents
    ]
    choices.append(("Cancel", "cancel"))
    
    choice = inquirer.select(
        message="Select document to delete:",
        choices=choices
    ).execute()
    
    if isinstance(choice, tuple):
        choice = choice[1]
    
    if choice == "cancel":
        return
    
    # Confirm deletion
    confirm = inquirer.confirm(
        message="Are you sure you want to delete this document?",
        default=False
    ).execute()
    
    if confirm:
        if rag_service.delete_document(choice):
            console.print("[green]✓[/] Document deleted successfully.")
        else:
            console.print("[red]✗[/] Failed to delete document.")
    else:
        console.print("[yellow]Deletion cancelled.[/]")

