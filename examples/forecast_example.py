"""
Example: Using the GCP FinOps Forecasting API

This script demonstrates how to use the Prophet-based cost forecasting endpoints.
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any

# API Configuration
API_BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def get_cost_forecast(days: int = 90, historical_days: int = 180) -> Dict[str, Any]:
    """Get general cost forecast."""
    print_section(f"Getting {days}-Day Cost Forecast")
    
    response = requests.get(
        f"{API_BASE_URL}/api/forecast",
        params={
            "days": days,
            "historical_days": historical_days
        }
    )
    
    if response.status_code == 200:
        forecast = response.json()
        
        print(f"Total Predicted Cost: ${forecast['total_predicted_cost']:.2f}")
        print(f"Forecast Period: {forecast['forecast_days']} days")
        print(f"Trend: {forecast['trend'].upper()}")
        print(f"Model Confidence: {forecast['model_confidence']:.1%}")
        print(f"Generated At: {forecast['generated_at']}")
        
        print(f"\nFirst 5 Forecast Points:")
        for point in forecast['forecast_points'][:5]:
            print(f"  {point['date']}: ${point['predicted_cost']:.2f} "
                  f"(${point['lower_bound']:.2f} - ${point['upper_bound']:.2f})")
        
        return forecast
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {}


def get_forecast_summary(days: int = 30) -> Dict[str, Any]:
    """Get summarized forecast information."""
    print_section("Getting Forecast Summary")
    
    response = requests.get(
        f"{API_BASE_URL}/api/forecast/summary",
        params={"days": days}
    )
    
    if response.status_code == 200:
        summary = response.json()
        
        print(f"Current Month Cost: ${summary['current_month_cost']:.2f}")
        print(f"Predicted Cost (Next {days} days): ${summary['predicted_cost_next_30d']:.2f}")
        
        diff = summary['predicted_cost_next_30d'] - summary['current_month_cost']
        pct_change = (diff / summary['current_month_cost'] * 100) if summary['current_month_cost'] > 0 else 0
        
        print(f"Difference: ${diff:.2f} ({pct_change:+.1f}%)")
        print(f"Trend: {summary['trend'].upper()}")
        print(f"Confidence: {summary['confidence']:.1%}")
        
        return summary
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {}


def get_service_forecast(service_name: str, days: int = 90) -> Dict[str, Any]:
    """Get forecast for a specific service."""
    print_section(f"Forecasting '{service_name}' Costs")
    
    response = requests.get(
        f"{API_BASE_URL}/api/forecast/service/{service_name}",
        params={"days": days}
    )
    
    if response.status_code == 200:
        forecast = response.json()
        
        print(f"Service: {forecast['service_name']}")
        print(f"Total Predicted Cost: ${forecast['total_predicted_cost']:.2f}")
        print(f"Trend: {forecast['trend'].upper()}")
        print(f"Model Confidence: {forecast['model_confidence']:.1%}")
        
        # Show weekly averages
        points = forecast['forecast_points']
        if points:
            week_1 = sum(p['predicted_cost'] for p in points[:7]) / 7
            week_2 = sum(p['predicted_cost'] for p in points[7:14]) / 7 if len(points) >= 14 else 0
            
            print(f"\nWeekly Averages:")
            print(f"  Week 1: ${week_1:.2f}/day")
            if week_2 > 0:
                print(f"  Week 2: ${week_2:.2f}/day")
        
        return forecast
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {}


def get_forecast_trends() -> Dict[str, Any]:
    """Get forecast trends for all major services."""
    print_section("Service-Level Forecast Trends")
    
    response = requests.get(f"{API_BASE_URL}/api/forecast/trends")
    
    if response.status_code == 200:
        trends = response.json()
        
        print(f"Top {len(trends['trends'])} Services:\n")
        
        for i, trend in enumerate(trends['trends'], 1):
            diff = trend['predicted_cost_30d'] - trend['current_cost']
            pct_change = (diff / trend['current_cost'] * 100) if trend['current_cost'] > 0 else 0
            
            print(f"{i}. {trend['service_name']}")
            print(f"   Current: ${trend['current_cost']:.2f}")
            print(f"   Predicted (30d): ${trend['predicted_cost_30d']:.2f}")
            print(f"   Change: ${diff:+.2f} ({pct_change:+.1f}%)")
            print(f"   Trend: {trend['trend'].upper()}")
            print(f"   Confidence: {trend['confidence']:.1%}")
            print()
        
        return trends
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {}


def get_alert_thresholds() -> Dict[str, Any]:
    """Get recommended budget alert thresholds."""
    print_section("Recommended Budget Alert Thresholds")
    
    response = requests.get(f"{API_BASE_URL}/api/forecast/alert-thresholds")
    
    if response.status_code == 200:
        thresholds = response.json()
        
        print(f"Predicted Monthly Cost: ${thresholds['predicted_monthly_cost']:.2f}")
        print(f"Trend: {thresholds['trend'].upper()}")
        print(f"Confidence: {thresholds['confidence']:.1%}")
        
        print("\nRecommended Alert Thresholds:")
        print(f"  🟢 Conservative (+10%): ${thresholds['recommended_thresholds']['conservative']:.2f}")
        print(f"  🟡 Warning (+20%):      ${thresholds['recommended_thresholds']['warning']:.2f}")
        print(f"  🔴 Critical (+30%):     ${thresholds['recommended_thresholds']['critical']:.2f}")
        
        print("\nSuggestions:")
        print("  - Set budget alerts at the Warning threshold")
        print("  - Configure critical alerts at the Critical threshold")
        print("  - Review costs if they exceed Conservative threshold")
        
        return thresholds
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {}


def export_forecast_to_csv(forecast: Dict[str, Any], filename: str = "forecast.csv"):
    """Export forecast data to CSV."""
    import csv
    
    print_section(f"Exporting Forecast to {filename}")
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date', 'Predicted Cost', 'Lower Bound', 'Upper Bound'])
        
        for point in forecast['forecast_points']:
            writer.writerow([
                point['date'],
                f"{point['predicted_cost']:.2f}",
                f"{point['lower_bound']:.2f}",
                f"{point['upper_bound']:.2f}"
            ])
    
    print(f"✓ Exported {len(forecast['forecast_points'])} data points to {filename}")


def main():
    """Run all forecast examples."""
    print("\n" + "🔮" * 30)
    print("  GCP FinOps Forecasting Examples")
    print("🔮" * 30)
    
    try:
        # 1. Get general cost forecast
        forecast = get_cost_forecast(days=90, historical_days=180)
        
        # 2. Get forecast summary
        summary = get_forecast_summary(days=30)
        
        # 3. Get service forecast (example: Cloud Run)
        service_forecast = get_service_forecast("Cloud Run", days=90)
        
        # 4. Get forecast trends for all services
        trends = get_forecast_trends()
        
        # 5. Get recommended alert thresholds
        thresholds = get_alert_thresholds()
        
        # 6. Export forecast to CSV
        if forecast:
            export_forecast_to_csv(forecast, "gcp_cost_forecast.csv")
        
        print_section("Complete!")
        print("All forecasting examples executed successfully.")
        print("\nNext Steps:")
        print("  1. Integrate forecasts into your monitoring system")
        print("  2. Set up budget alerts based on recommended thresholds")
        print("  3. Review service-level trends to identify optimization opportunities")
        print("  4. Schedule regular forecast generation (e.g., weekly reports)")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server")
        print(f"   Make sure the API is running at {API_BASE_URL}")
        print("   Start it with: python -m gcp_finops_dashboard.api")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()

