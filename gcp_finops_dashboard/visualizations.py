"""Visualization module for dashboard display - backward compatibility wrapper.

This module provides backward compatibility by re-exporting the modular visualization components.
All functionality has been moved to utils/visualizations/ modules.
"""

# Re-export for backward compatibility
from .utils.visualizations import (
    DashboardVisualizer,
    ChartGenerator,
    print_progress,
    print_error,
    print_warning,
)

__all__ = [
    "DashboardVisualizer",
    "ChartGenerator",
    "print_progress",
    "print_error",
    "print_warning",
]
