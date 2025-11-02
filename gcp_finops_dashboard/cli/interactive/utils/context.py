"""Common context collection utilities."""

import os
from typing import Optional, Dict, Any
from InquirerPy import inquirer

def prompt_common_context() -> Dict[str, Any]:
    """Collect common context like project, billing dataset, regions, location, hide flag.
    
    Uses session environment variables as defaults if set (from Quick Setup).
    
    Returns:
        Dictionary with keys: project_id, billing_dataset, regions, location, hide_project_id
    """
    # Get defaults from session environment variables
    default_project = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or ""
    default_billing = os.getenv("GCP_BILLING_DATASET") or ""
    default_regions = os.getenv("GCP_REGIONS") or ""
    
    project_id = inquirer.text(
        message="Enter GCP project ID (blank = default config):",
        default=default_project,
    ).execute()
    if project_id.strip() == "":
        project_id = None
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., project.billing_export):",
        default=default_billing,
    ).execute()
    
    regions_input = inquirer.text(
        message="Enter regions (comma-separated, or press Enter for all):",
        default=default_regions,
    ).execute()
    region_list: Optional[list] = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    location = inquirer.text(
        message="BigQuery location (default: US):",
        default="US",
    ).execute()
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output?",
        default=False,
    ).execute()
    return {
        "project_id": project_id,
        "billing_dataset": billing_dataset,
        "regions": region_list,
        "location": location,
        "hide_project_id": hide_project_id,
    }

