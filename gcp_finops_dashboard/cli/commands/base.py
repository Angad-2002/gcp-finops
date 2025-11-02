"""Base command module with shared functionality."""

from typing import Optional
import click
from google.cloud import bigquery

class BaseCommand:
    """Base class for CLI commands with shared functionality."""
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        billing_table_prefix: str = "gcp_billing_export_v1",
        location: str = "US",
    ):
        self.project_id = project_id
        self.billing_table_prefix = billing_table_prefix
        self.location = location
        self.client = None
    
    def init_bigquery(self):
        """Initialize BigQuery client."""
        self.client = bigquery.Client(project=self.project_id)
    
    @staticmethod
    def common_options(f):
        """Decorator to add common command options."""
        options = [
            click.option(
                "--project-id",
                help="GCP project ID (defaults to gcloud config)",
            ),
            click.option(
                "--billing-table-prefix",
                default="gcp_billing_export_v1",
                help="Billing table prefix (default: gcp_billing_export_v1)",
            ),
            click.option(
                "--location",
                default="US",
                help="BigQuery location (default: US, e.g., 'asia-southeast1', 'europe-west1')",
            ),
        ]
        for option in reversed(options):
            f = option(f)
        return f
