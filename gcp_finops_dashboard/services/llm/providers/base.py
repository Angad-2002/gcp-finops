"""Base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLMProvider(ABC):
    """Base interface for LLM providers."""
    
    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if the provider's dependencies are installed."""
        pass
    
    @classmethod
    @abstractmethod
    def get_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get available models for this provider."""
        pass
    
    @abstractmethod
    def __init__(self, api_key: str, model: str):
        """Initialize the provider with API key and model."""
        pass
    
    @abstractmethod
    def call(
        self,
        prompt: str,
        system_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Make a call to the provider's API.
        
        Args:
            prompt: User prompt
            system_message: System message/instructions
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation
            
        Returns:
            Generated text response
        """
        pass

