"""
Generate Mock GCP Billing Data for Testing Prophet Forecasting

This script creates realistic GCP billing data with:
- Multiple services (Cloud Run, Compute Engine, BigQuery, etc.)
- Seasonal patterns (weekday vs weekend)
- Growth trends
- Random variations

Usage:
    python examples/generate_mock_billing_data.py --days 180 --output mock_billing.csv
    
    # Upload to BigQuery:
    bq load --autodetect --source_format=CSV \
        your-project:billing_export.gcp_billing_export_v1_YYYYMMDD \
        mock_billing.csv
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import json


def generate_mock_billing_data(num_days: int = 180, base_daily_cost: float = 150.0) -> pd.DataFrame:
    """
    Generate realistic mock GCP billing data.
    
    Args:
        num_days: Number of days of data to generate
        base_daily_cost: Base daily cost in USD
    
    Returns:
        DataFrame with mock billing data
    """
    
    # Define GCP services and their cost distributions
    services = [
        {"name": "Cloud Run", "weight": 0.25, "volatility": 0.15},
        {"name": "Compute Engine", "weight": 0.30, "volatility": 0.10},
        {"name": "BigQuery", "weight": 0.20, "volatility": 0.20},
        {"name": "Cloud Storage", "weight": 0.10, "volatility": 0.05},
        {"name": "Cloud Functions", "weight": 0.08, "volatility": 0.25},
        {"name": "Cloud SQL", "weight": 0.07, "volatility": 0.08},
    ]
    
    # SKUs for each service
    skus = {
        "Cloud Run": ["CPU Allocation", "Memory Allocation", "Request Count"],
        "Compute Engine": ["N1 Instance", "Network Egress", "Persistent Disk"],
        "BigQuery": ["Storage", "Analysis", "Streaming Insert"],
        "Cloud Storage": ["Standard Storage", "Network Egress", "Operations"],
        "Cloud Functions": ["Invocations", "CPU Time", "Memory Time"],
        "Cloud SQL": ["DB Instance", "Storage", "Network"],
    }
    
    # Generate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_days)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    records = []
    
    print(f"Generating {num_days} days of mock billing data...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Base daily cost: ${base_daily_cost:.2f}")
    
    for day_idx, date in enumerate(dates):
        # Add growth trend (2% monthly growth)
        growth_factor = 1 + (0.02 / 30 * day_idx)
        
        # Add weekly seasonality (weekends are 30% cheaper)
        day_of_week = date.dayofweek
        weekend_factor = 0.7 if day_of_week >= 5 else 1.0
        
        # Add monthly seasonality (end of month spike)
        day_of_month = date.day
        month_end_factor = 1.2 if day_of_month >= 28 else 1.0
        
        # Calculate daily cost with all factors
        daily_cost = base_daily_cost * growth_factor * weekend_factor * month_end_factor
        
        # Add random noise (±10%)
        daily_cost *= np.random.uniform(0.9, 1.1)
        
        # Generate records for each service
        for service in services:
            service_cost = daily_cost * service["weight"]
            
            # Add service-specific volatility
            service_cost *= np.random.uniform(
                1 - service["volatility"], 
                1 + service["volatility"]
            )
            
            # Distribute cost across SKUs
            service_skus = skus[service["name"]]
            sku_costs = np.random.dirichlet(np.ones(len(service_skus))) * service_cost
            
            for sku, sku_cost in zip(service_skus, sku_costs):
                if sku_cost < 0.01:  # Skip tiny costs
                    continue
                
                # Generate usage amount based on SKU type
                if "Count" in sku or "Invocations" in sku:
                    usage_amount = sku_cost * 1000  # Requests
                    usage_unit = "requests"
                elif "Time" in sku or "CPU" in sku or "Memory" in sku:
                    usage_amount = sku_cost * 100  # Hours
                    usage_unit = "seconds"
                elif "Storage" in sku:
                    usage_amount = sku_cost * 50  # GB-months
                    usage_unit = "byte-seconds"
                else:
                    usage_amount = sku_cost * 10
                    usage_unit = "byte-seconds"
                
                record = {
                    "billing_account_id": "MOCK-BILLING-ACCOUNT",
                    "service": json.dumps({"id": service["name"].lower().replace(" ", "-"), 
                                          "description": service["name"]}),
                    "sku": json.dumps({"id": sku.lower().replace(" ", "-"), 
                                      "description": sku}),
                    "usage_start_time": date.isoformat(),
                    "usage_end_time": (date + timedelta(days=1)).isoformat(),
                    "project": json.dumps({"id": "mock-project-123", 
                                          "name": "Mock Project"}),
                    "labels": json.dumps([{"key": "environment", "value": "test"}]),
                    "location": json.dumps({"location": "us-central1", 
                                           "country": "US", 
                                           "region": "us-central1"}),
                    "cost": round(sku_cost, 4),
                    "currency": "USD",
                    "currency_conversion_rate": 1.0,
                    "usage": json.dumps({
                        "amount": round(usage_amount, 2),
                        "unit": usage_unit,
                        "amount_in_pricing_units": round(usage_amount, 2),
                        "pricing_unit": usage_unit
                    }),
                    "credits": json.dumps([]),  # No credits in mock data
                    "invoice": json.dumps({"month": date.strftime("%Y%m")}),
                    "cost_type": "regular",
                }
                
                records.append(record)
    
    df = pd.DataFrame(records)
    
    # Print summary statistics
    print(f"\n✓ Generated {len(records)} billing records")
    print(f"✓ Date range: {df['usage_start_time'].min()[:10]} to {df['usage_start_time'].max()[:10]}")
    print(f"✓ Total cost: ${df['cost'].sum():,.2f}")
    print(f"✓ Daily average: ${df['cost'].sum() / num_days:,.2f}")
    print(f"✓ Services: {len(services)}")
    
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate mock GCP billing data")
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
    parser.add_argument(
        "--output", 
        type=str, 
        default="mock_billing_data.csv", 
        help="Output CSV file (default: mock_billing_data.csv)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "json", "both"],
        default="csv",
        help="Output format (default: csv)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  GCP Mock Billing Data Generator")
    print("=" * 60)
    
    # Generate data
    df = generate_mock_billing_data(
        num_days=args.days,
        base_daily_cost=args.base_cost
    )
    
    # Save to file(s)
    if args.format in ["csv", "both"]:
        df.to_csv(args.output, index=False)
        print(f"\n✓ Saved to: {args.output}")
        print(f"  Size: {len(df)} rows")
    
    if args.format in ["json", "both"]:
        json_output = args.output.replace(".csv", ".json")
        df.to_json(json_output, orient="records", lines=True)
        print(f"✓ Saved to: {json_output}")
    
    print("\n" + "=" * 60)
    print("  Next Steps:")
    print("=" * 60)
    print("\n1. Upload to BigQuery:")
    print(f"   bq load --source_format=CSV --autodetect \\")
    print(f"     your-project:billing_export.gcp_billing_export_v1_$(date +%Y%m%d) \\")
    print(f"     {args.output}")
    
    print("\n2. Or use with the Python API directly:")
    print(f"   df = pd.read_csv('{args.output}')")
    print(f"   # Process with your forecasting code")
    
    print("\n3. Test forecasting:")
    print(f"   curl localhost:8000/api/forecast/summary?days=30")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

