"""LLM service for AI-powered FinOps insights - backward compatibility wrapper.

This module provides backward compatibility by re-exporting the modular LLM service.
All functionality has been moved to services/llm/ modules.
"""

# Re-export for backward compatibility
from .services.llm import (
    LLMService,
    get_llm_service,
    refresh_llm_service,
    get_available_providers,
    get_available_models,
)

__all__ = [
    "LLMService",
    "get_llm_service",
    "refresh_llm_service",
    "get_available_providers",
    "get_available_models",
]
