"""
Load Mock Billing Data Directly to BigQuery

This script generates mock data and loads it directly into BigQuery
without needing CSV files.

Usage:
    python examples/load_mock_data_to_bigquery.py \
        --project your-project-id \
        --dataset billing_export \
        --days 180
"""

import argparse
from datetime import datetime
from google.cloud import bigquery
import pandas as pd
import json
from generate_mock_billing_data import generate_mock_billing_data


def create_billing_table(client: bigquery.Client, dataset_id: str, table_date: str):
    """Create a billing export table with the correct schema."""
    
    table_id = f"{dataset_id}.gcp_billing_export_v1_{table_date}"
    
    schema = [
        bigquery.SchemaField("billing_account_id", "STRING"),
        bigquery.SchemaField("service", "JSON"),
        bigquery.SchemaField("sku", "JSON"),
        bigquery.SchemaField("usage_start_time", "TIMESTAMP"),
        bigquery.SchemaField("usage_end_time", "TIMESTAMP"),
        bigquery.SchemaField("project", "JSON"),
        bigquery.SchemaField("labels", "JSON"),
        bigquery.SchemaField("location", "JSON"),
        bigquery.SchemaField("cost", "FLOAT64"),
        bigquery.SchemaField("currency", "STRING"),
        bigquery.SchemaField("currency_conversion_rate", "FLOAT64"),
        bigquery.SchemaField("usage", "JSON"),
        bigquery.SchemaField("credits", "JSON"),
        bigquery.SchemaField("invoice", "JSON"),
        bigquery.SchemaField("cost_type", "STRING"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    
    try:
        table = client.create_table(table)
        print(f"✓ Created table: {table_id}")
    except Exception as e:
        if "Already Exists" in str(e):
            print(f"✓ Table already exists: {table_id}")
        else:
            raise
    
    return table_id


def load_data_to_bigquery(
    project_id: str,
    dataset_id: str,
    num_days: int = 180,
    base_cost: float = 150.0
):
    """Generate and load mock data to BigQuery."""
    
    print("=" * 60)
    print("  Loading Mock Data to BigQuery")
    print("=" * 60)
    
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)
    
    # Ensure dataset exists
    dataset_ref = f"{project_id}.{dataset_id}"
    try:
        client.get_dataset(dataset_ref)
        print(f"✓ Dataset exists: {dataset_ref}")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset)
        print(f"✓ Created dataset: {dataset_ref}")
    
    # Generate mock data
    print(f"\nGenerating {num_days} days of mock data...")
    df = generate_mock_billing_data(num_days=num_days, base_daily_cost=base_cost)
    
    # Convert timestamp strings to datetime
    df['usage_start_time'] = pd.to_datetime(df['usage_start_time'])
    df['usage_end_time'] = pd.to_datetime(df['usage_end_time'])
    
    # Group by date and create separate tables for each month
    df['table_suffix'] = df['usage_start_time'].dt.strftime('%Y%m%d')
    table_suffixes = df['table_suffix'].unique()
    
    print(f"\nLoading data into {len(table_suffixes)} table(s)...")
    
    total_rows = 0
    for suffix in sorted(table_suffixes):
        # Create table for this date
        table_id = create_billing_table(client, dataset_id, suffix)
        
        # Get data for this table
        table_data = df[df['table_suffix'] == suffix].drop('table_suffix', axis=1)
        
        # Load data
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        
        job = client.load_table_from_dataframe(
            table_data,
            table_id,
            job_config=job_config
        )
        
        job.result()  # Wait for job to complete
        
        print(f"  ✓ Loaded {len(table_data)} rows to {table_id}")
        total_rows += len(table_data)
    
    print(f"\n✓ Total rows loaded: {total_rows:,}")
    print(f"✓ Total cost: ${df['cost'].sum():,.2f}")
    print(f"✓ Daily average: ${df['cost'].sum() / num_days:,.2f}")
    
    print("\n" + "=" * 60)
    print("  Next Steps:")
    print("=" * 60)
    print("\n1. Update your environment variables:")
    print(f"   export GCP_PROJECT_ID='{project_id}'")
    print(f"   export GCP_BILLING_DATASET='{project_id}.{dataset_id}'")
    
    print("\n2. Restart the API server:")
    print("   python start-api.py")
    
    print("\n3. Test forecasting:")
    print("   curl localhost:8000/api/forecast/summary?days=30")
    print("   curl localhost:8000/api/forecast?days=90")
    
    print("\n4. View in web dashboard:")
    print("   http://localhost:3000/trends")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate and load mock GCP billing data to BigQuery"
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="GCP Project ID"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="billing_export",
        help="BigQuery dataset name (default: billing_export)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=180,
        help="Number of days of data to generate (default: 180)"
    )
    parser.add_argument(
        "--base-cost",
        type=float,
        default=150.0,
        help="Base daily cost in USD (default: 150.0)"
    )
    
    args = parser.parse_args()
    
    load_data_to_bigquery(
        project_id=args.project,
        dataset_id=args.dataset,
        num_days=args.days,
        base_cost=args.base_cost
    )


if __name__ == "__main__":
    main()

