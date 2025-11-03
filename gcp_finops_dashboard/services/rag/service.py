"""RAG (Retrieval Augmented Generation) service for document-based chat."""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from rich.console import Console

console = Console()

# Try to import optional dependencies
try:
    import pypdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

# Fallback to FAISS if ChromaDB not available
if not CHROMA_AVAILABLE:
    try:
        import faiss
        import numpy as np
        FAISS_AVAILABLE = True
    except ImportError:
        FAISS_AVAILABLE = False
else:
    FAISS_AVAILABLE = False


class RAGService:
    """Service for RAG-based document Q&A."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize RAG service.
        
        Args:
            storage_dir: Directory to store vector database and documents
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".gcp-finops" / "rag"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir = self.storage_dir / "documents"
        self.documents_dir.mkdir(exist_ok=True)
        
        self.embedding_model = None
        self.vector_store = None
        self.collection = None
        self.faiss_index = None
        self.faiss_metadata = []
        self.documents_metadata = []
        
        self._initialize_embeddings()
        self._initialize_vector_store()
        self._load_metadata()
    
    def _initialize_embeddings(self):
        """Initialize embedding model."""
        if not EMBEDDINGS_AVAILABLE:
            console.print("[yellow]Warning: sentence-transformers not installed. Install it for RAG features: pip install sentence-transformers[/]")
            return
        
        try:
            # Use a lightweight, fast model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            console.print("[dim]Loaded embedding model: all-MiniLM-L6-v2[/]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load embedding model: {e}[/]")
            self.embedding_model = None
    
    def _initialize_vector_store(self):
        """Initialize vector store."""
        if CHROMA_AVAILABLE:
            try:
                chroma_path = str(self.storage_dir / "chroma_db")
                self.vector_store = chromadb.PersistentClient(
                    path=chroma_path,
                    settings=Settings(anonymized_telemetry=False)
                )
                self.collection = self.vector_store.get_or_create_collection(
                    name="gcp_finops_documents",
                    metadata={"description": "GCP FinOps document embeddings"}
                )
                console.print("[dim]Using ChromaDB for vector storage[/]")
                return
            except Exception as e:
                console.print(f"[yellow]Warning: ChromaDB initialization failed: {e}[/]")
        
        if FAISS_AVAILABLE:
            # Simple FAISS-based storage
            self.faiss_index = None
            self.faiss_metadata = []
            console.print("[dim]Using FAISS for vector storage[/]")
            return
        
        console.print("[yellow]Warning: No vector store available. Install chromadb or faiss-cpu for RAG features.[/]")
    
    def _load_metadata(self):
        """Load document metadata."""
        metadata_file = self.storage_dir / "documents_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    self.documents_metadata = json.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load metadata: {e}[/]")
                self.documents_metadata = []
        else:
            self.documents_metadata = []
    
    def _save_metadata(self):
        """Save document metadata."""
        metadata_file = self.storage_dir / "documents_metadata.json"
        try:
            with open(metadata_file, 'w') as f:
                json.dump(self.documents_metadata, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save metadata: {e}[/]")
    
    def upload_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Upload and process a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with upload status and document info
        """
        if not PDF_AVAILABLE:
            return {
                "success": False,
                "error": "pypdf not installed. Install it: pip install pypdf"
            }
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            return {"success": False, "error": f"File not found: {pdf_path}"}
        
        if pdf_path.suffix.lower() != '.pdf':
            return {"success": False, "error": "Only PDF files are supported"}
        
        try:
            # Copy PDF to documents directory
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            doc_filename = f"{pdf_path.stem}_{timestamp}.pdf"
            doc_path = self.documents_dir / doc_filename
            import shutil
            shutil.copy2(pdf_path, doc_path)
            
            # Extract text from PDF
            text_chunks = self._extract_pdf_text(str(doc_path))
            
            if not text_chunks:
                doc_path.unlink()  # Remove file if extraction failed
                return {"success": False, "error": "Could not extract text from PDF"}
            
            # Create embeddings and add to vector store
            document_id = f"doc_{timestamp}"
            self._add_documents_to_store(document_id, text_chunks, str(doc_path))
            
            # Save metadata
            doc_metadata = {
                "id": document_id,
                "filename": pdf_path.name,
                "stored_filename": doc_filename,
                "uploaded_at": datetime.now().isoformat(),
                "chunks": len(text_chunks)
            }
            self.documents_metadata.append(doc_metadata)
            self._save_metadata()
            
            return {
                "success": True,
                "document_id": document_id,
                "filename": pdf_path.name,
                "chunks": len(text_chunks),
                "metadata": doc_metadata
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error processing PDF: {str(e)}"}
    
    def _extract_pdf_text(self, pdf_path: str) -> List[str]:
        """Extract text from PDF and chunk it.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of text chunks
        """
        if not PDF_AVAILABLE:
            return []
        
        try:
            text_chunks = []
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                current_chunk = ""
                chunk_size = 1000  # characters per chunk
                overlap = 200  # overlap between chunks
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if not page_text.strip():
                        continue
                    
                    # Split page text into chunks
                    words = page_text.split()
                    for word in words:
                        if len(current_chunk) + len(word) + 1 > chunk_size:
                            if current_chunk:
                                text_chunks.append(current_chunk.strip())
                            # Start new chunk with overlap
                            current_chunk = " ".join(current_chunk.split()[-overlap//10:]) + " " + word
                        else:
                            current_chunk += " " + word if current_chunk else word
                    
                    # Add metadata to chunk
                    current_chunk += f" [Page {page_num + 1}]"
                
                # Add remaining chunk
                if current_chunk:
                    text_chunks.append(current_chunk.strip())
            
            return text_chunks
            
        except Exception as e:
            console.print(f"[yellow]Error extracting PDF text: {e}[/]")
            return []
    
    def _add_documents_to_store(self, document_id: str, chunks: List[str], source: str):
        """Add document chunks to vector store.
        
        Args:
            document_id: Unique document identifier
            chunks: List of text chunks
            source: Source file path
        """
        if not self.embedding_model:
            return
        
        if self.collection:  # ChromaDB
            try:
                # Generate embeddings
                embeddings = self.embedding_model.encode(chunks, show_progress_bar=False)
                
                # Create IDs for each chunk
                chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
                
                # Prepare metadata
                metadatas = [
                    {
                        "source": source,
                        "document_id": document_id,
                        "chunk_index": i
                    }
                    for i in range(len(chunks))
                ]
                
                # Add to collection
                self.collection.add(
                    ids=chunk_ids,
                    embeddings=embeddings.tolist(),
                    documents=chunks,
                    metadatas=metadatas
                )
            except Exception as e:
                console.print(f"[yellow]Error adding to ChromaDB: {e}[/]")
        
        elif FAISS_AVAILABLE:  # FAISS
            try:
                embeddings = self.embedding_model.encode(chunks, show_progress_bar=False)
                embeddings = np.array(embeddings).astype('float32')
                
                # Initialize FAISS index if needed
                if self.faiss_index is None:
                    dimension = embeddings.shape[1]
                    self.faiss_index = faiss.IndexFlatL2(dimension)
                    # Try to load existing index if it exists
                    faiss_index_path = self.storage_dir / "faiss.index"
                    if faiss_index_path.exists():
                        try:
                            self.faiss_index = faiss.read_index(str(faiss_index_path))
                            # Load metadata
                            metadata_path = self.storage_dir / "faiss_metadata.json"
                            if metadata_path.exists():
                                with open(metadata_path, 'r') as f:
                                    self.faiss_metadata = json.load(f)
                        except Exception:
                            pass  # Start fresh if loading fails
                
                # Add to index
                self.faiss_index.add(embeddings)
                
                # Store metadata
                for i, chunk in enumerate(chunks):
                    self.faiss_metadata.append({
                        "chunk_id": f"{document_id}_chunk_{i}",
                        "text": chunk,
                        "source": source,
                        "document_id": document_id
                    })
                
                # Save FAISS index
                faiss.write_index(self.faiss_index, str(self.storage_dir / "faiss.index"))
                with open(self.storage_dir / "faiss_metadata.json", 'w') as f:
                    json.dump(self.faiss_metadata, f)
                    
            except Exception as e:
                console.print(f"[yellow]Error adding to FAISS: {e}[/]")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant document chunks.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant chunks with metadata
        """
        if not self.embedding_model:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query], show_progress_bar=False)[0]
            
            if self.collection:  # ChromaDB
                results = self.collection.query(
                    query_embeddings=[query_embedding.tolist()],
                    n_results=top_k
                )
                
                chunks = []
                if results['documents'] and len(results['documents'][0]) > 0:
                    for i in range(len(results['documents'][0])):
                        # Safely get metadata - handle None values
                        if results.get('metadatas') and len(results['metadatas']) > 0 and i < len(results['metadatas'][0]):
                            metadata = results['metadatas'][0][i] or {}
                        else:
                            metadata = {}
                        chunks.append({
                            "text": results['documents'][0][i],
                            "metadata": metadata,
                            "distance": results['distances'][0][i] if results.get('distances') and len(results['distances'][0]) > i else 0
                        })
                return chunks
            
            elif FAISS_AVAILABLE and self.faiss_index is not None:  # FAISS
                if len(self.faiss_metadata) == 0:
                    return []
                
                # Search
                query_vector = np.array([query_embedding]).astype('float32')
                distances, indices = self.faiss_index.search(query_vector, top_k)
                
                chunks = []
                for idx in indices[0]:
                    if idx < len(self.faiss_metadata):
                        chunks.append({
                            "text": self.faiss_metadata[idx]["text"],
                            "metadata": {
                                "source": self.faiss_metadata[idx]["source"],
                                "document_id": self.faiss_metadata[idx]["document_id"]
                            },
                            "distance": float(distances[0][idx])
                        })
                return chunks
            
            return []
            
        except Exception as e:
            console.print(f"[yellow]Error searching: {e}[/]")
            return []
    
    def get_documents(self) -> List[Dict[str, Any]]:
        """Get list of uploaded documents.
        
        Returns:
            List of document metadata
        """
        return self.documents_metadata.copy()
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector store.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if successful
        """
        try:
            # Remove from metadata
            self.documents_metadata = [
                doc for doc in self.documents_metadata if doc["id"] != document_id
            ]
            self._save_metadata()
            
            # Remove from vector store (ChromaDB)
            if self.collection:
                try:
                    # Get all chunks for this document
                    results = self.collection.get(
                        where={"document_id": document_id}
                    )
                    if results['ids']:
                        self.collection.delete(ids=results['ids'])
                except Exception:
                    pass  # Document might not exist
            
            # Remove file
            doc_info = next((d for d in self.documents_metadata if d["id"] == document_id), None)
            if doc_info and "stored_filename" in doc_info:
                doc_path = self.documents_dir / doc_info["stored_filename"]
                if doc_path.exists():
                    doc_path.unlink()
            
            return True
        except Exception as e:
            console.print(f"[yellow]Error deleting document: {e}[/]")
            return False

