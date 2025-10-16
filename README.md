# GCP FinOps Dashboard

A comprehensive cost optimization and resource auditing tool for Google Cloud Platform (GCP). This dashboard provides detailed insights into your GCP spending, identifies optimization opportunities, and offers AI-powered recommendations to reduce costs.

## 🚀 Features

### Core Functionality
- **Cost Analysis**: Track current month, last month, and year-to-date spending
- **Resource Auditing**: Comprehensive audits for Cloud Run, Cloud Functions, Compute Engine, Cloud SQL, and Storage
- **Optimization Recommendations**: AI-powered suggestions to reduce costs
- **Cost Forecasting**: Prophet-based predictions for future spending
- **PDF Reports**: Generate detailed reports for stakeholders
- **REST API**: Full API for integration with other tools

### Supported GCP Services
- **Cloud Run**: Service optimization, idle detection, resource sizing
- **Cloud Functions**: Function analysis, cold start optimization
- **Compute Engine**: Instance auditing, idle detection, right-sizing
- **Cloud SQL**: Database optimization, storage analysis
- **Storage**: Persistent disk and static IP auditing

### AI-Powered Insights
- **Groq LLM Integration**: Natural language analysis of cost data
- **Anomaly Detection**: Identify unusual spending patterns
- **Executive Summaries**: Generate stakeholder-ready reports
- **Smart Recommendations**: Prioritize optimization opportunities

## 📋 Prerequisites

- Python 3.9 or higher
- Google Cloud Project with billing enabled
- BigQuery billing export configured
- GCP authentication set up

## 🛠️ Installation

### Option 1: Install from PyPI (Recommended)
```bash
pip install gcp-finops-dashboard
```

### Option 2: Install from Source
```bash
git clone https://github.com/your-repo/gcp-finops-dashboard.git
cd gcp-finops-dashboard
pip install -e .
```

### Option 3: Using uv (Fast Python Package Manager)
```bash
uv add gcp-finops-dashboard
```

## ⚙️ Setup

### 1. Enable Required GCP APIs
```bash
gcloud services enable \
    cloudbilling.googleapis.com \
    bigquery.googleapis.com \
    run.googleapis.com \
    cloudfunctions.googleapis.com \
    compute.googleapis.com \
    sqladmin.googleapis.com \
    cloudresourcemanager.googleapis.com \
    monitoring.googleapis.com
```

### 2. Set Up BigQuery Billing Export
1. Go to [GCP Billing Export](https://console.cloud.google.com/billing/export)
2. Enable "BigQuery Export"
3. Note your dataset name (e.g., `billing_export`)
4. Wait 24 hours for data to populate

### 3. Authenticate with GCP
```bash
gcloud auth application-default login
```

### 4. Set Project ID
```bash
gcloud config set project YOUR_PROJECT_ID
# OR set environment variable:
export GCP_PROJECT_ID=YOUR_PROJECT_ID
```

### 5. Optional: Configure AI Features
To enable AI-powered insights, set your Groq API key:
```bash
export GROQ_API_KEY=your_groq_api_key_here
```

## 🚀 Quick Start

### Command Line Interface

#### Run Complete Dashboard
```bash
gcp-finops --billing-dataset YOUR_PROJECT.billing_export
```

#### Generate PDF Report
```bash
gcp-finops --billing-dataset YOUR_PROJECT.billing_export --report-type pdf
```

#### Run Specific Audit
```bash
gcp-finops --billing-dataset YOUR_PROJECT.billing_export --audit cloud-run
```

#### Use Configuration File
```bash
gcp-finops --config-file config.yaml
```

### Configuration File

Create a `config.yaml` file:

```yaml
# GCP Project and Billing Settings
project-id: my-gcp-project
billing-dataset: my-project.billing_export
billing-table-prefix: gcp_billing_export_v1
location: US

# Regions to audit
regions:
  - us-central1
  - us-east1
  - us-west1

# Report Settings
report-name: gcp-finops-report
report-type:
  - dashboard
  - pdf
dir: ./reports

# Time Range Settings
time-range: 30  # days
months-back: 2

# Filter Settings (optional)
label:
  - env=prod
  - team=devops
service:
  - cloud-run
  - compute
  - cloud-sql

# Mode Settings (optional)
audit: all  # Options: cloud-run, cloud-functions, compute, cloud-sql, storage, all
trend: true
forecast: true

# API Settings (optional)
api: true
api-port: 8000
```

## 🌐 API Server

### Start the API Server
```bash
gcp-finops --api --api-port 8000
```

### API Endpoints

#### Dashboard Data
- `GET /api/dashboard` - Complete dashboard data
- `GET /api/summary` - Cost summary
- `GET /api/costs/services` - Costs by service
- `GET /api/costs/trend` - Cost trend data

#### Audits
- `GET /api/audits` - All audit results
- `GET /api/audits/{audit_type}` - Specific audit results
- `GET /api/recommendations` - Optimization recommendations

#### AI Features
- `GET /api/ai/status` - AI service status
- `POST /api/ai/analyze` - Generate AI analysis
- `POST /api/ai/ask` - Ask questions about your data
- `POST /api/ai/executive-summary` - Generate executive summary

#### Forecasting
- `GET /api/forecast` - Cost forecast
- `GET /api/forecast/summary` - Forecast summary
- `GET /api/forecast/service/{service}` - Service-specific forecast

#### Reports
- `POST /api/reports/generate` - Generate PDF report
- `GET /api/reports` - List all reports
- `GET /api/reports/{filename}/download` - Download report

## 📊 Usage Examples

### Python API Usage

```python
from gcp_finops_dashboard.dashboard_runner import DashboardRunner
from gcp_finops_dashboard.visualizations import DashboardVisualizer

# Initialize runner
runner = DashboardRunner(
    project_id="your-project-id",
    billing_dataset="your-project.billing_export",
    regions=["us-central1", "us-east1"]
)

# Run analysis
data = runner.run()

# Display results
visualizer = DashboardVisualizer()
visualizer.display_dashboard(data)
```

### Cloud Run Specific Audit

```python
from gcp_finops_dashboard.cloud_run_auditor import CloudRunAuditor
from gcp_finops_dashboard.gcp_client import GCPClient

# Initialize auditor
gcp_client = GCPClient(project_id="your-project-id")
auditor = CloudRunAuditor(
    gcp_client.cloud_run,
    gcp_client.monitoring,
    "your-project-id"
)

# Run audit
result = auditor.audit_all_services(["us-central1", "us-east1"])

# Display results
print(f"Total services: {result.total_count}")
print(f"Potential savings: ${result.potential_monthly_savings:,.2f}")
```

### Cost Forecasting

```python
from gcp_finops_dashboard.forecast_service import ForecastService

# Initialize forecast service
forecast_service = ForecastService(
    client=bigquery_client,
    billing_dataset="your-project.billing_export"
)

# Generate forecast
forecast = forecast_service.forecast_costs(
    forecast_days=90,
    historical_days=180
)

print(f"Predicted cost: ${forecast.total_predicted_cost:,.2f}")
```

## 🔧 Command Line Options

### Global Options
- `--config-file, -C`: Path to configuration file (TOML, YAML, or JSON)
- `--project-id, -p`: GCP project ID
- `--billing-dataset, -b`: BigQuery billing dataset
- `--billing-table-prefix`: Billing table prefix (default: gcp_billing_export_v1)
- `--location, -l`: BigQuery location (default: US)
- `--regions, -r`: Regions to audit (space-separated)
- `--hide-project-id`: Hide project ID in output for security

### Report Options
- `--report-name, -n`: Base name for report file
- `--report-type, -y`: Report types (csv, json, pdf, dashboard)
- `--dir, -d`: Directory to save reports

### Time Range Options
- `--time-range, -t`: Time range in days
- `--months-back, -m`: Number of months to look back

### Filter Options
- `--label, -g`: Filter by labels/tags
- `--service, -s`: Filter by specific GCP services

### Mode Options
- `--audit, -a`: Run specific audit (cloud-run, cloud-functions, compute, cloud-sql, storage, all)
- `--trend`: Display trend report
- `--forecast`: Display cost forecast

### API Options
- `--api`: Start API server
- `--api-port`: Port for API server (default: 8000)

## 📁 Project Structure

```
gcp-finops-dashboard/
├── gcp_finops_dashboard/          # Main package
│   ├── __init__.py
│   ├── api.py                     # FastAPI server
│   ├── cli.py                     # Command-line interface
│   ├── dashboard_runner.py        # Main dashboard orchestrator
│   ├── gcp_client.py             # GCP service clients
│   ├── cost_processor.py         # BigQuery cost analysis
│   ├── forecast_service.py       # Prophet-based forecasting
│   ├── llm_service.py            # AI/LLM integration
│   ├── pdf_utils.py              # PDF report generation
│   ├── visualizations.py         # Terminal visualizations
│   ├── types.py                  # Data models
│   ├── helpers.py                # Utility functions
│   └── auditors/                 # Service-specific auditors
│       ├── cloud_run_auditor.py
│       ├── cloud_functions_auditor.py
│       ├── compute_auditor.py
│       ├── cloud_sql_auditor.py
│       └── storage_auditor.py
├── examples/                      # Usage examples
│   ├── basic_usage.py
│   ├── cloud_run_audit.py
│   ├── forecast_example.py
│   └── generate_mock_billing_data.py
├── reports/                       # Generated reports
├── config.example.yaml           # Configuration template
├── pyproject.toml                # Package configuration
└── requirements.txt              # Dependencies
```

## 🔍 Auditing Capabilities

### Cloud Run Auditing
- **Idle Service Detection**: Identifies services with zero traffic
- **Resource Optimization**: Analyzes CPU and memory allocation
- **Cost Analysis**: Calculates potential savings from optimization
- **Traffic Pattern Analysis**: Identifies usage patterns

### Cloud Functions Auditing
- **Cold Start Analysis**: Identifies functions with frequent cold starts
- **Memory Optimization**: Suggests optimal memory allocation
- **Timeout Analysis**: Identifies functions with excessive timeouts
- **Cost per Invocation**: Calculates cost efficiency

### Compute Engine Auditing
- **Idle Instance Detection**: Finds instances with low utilization
- **Right-sizing Recommendations**: Suggests optimal machine types
- **Preemptible Instance Opportunities**: Identifies suitable workloads
- **Reserved Instance Analysis**: Evaluates RI purchase opportunities

### Cloud SQL Auditing
- **Storage Optimization**: Analyzes disk usage and growth
- **Instance Sizing**: Identifies over/under-provisioned instances
- **Backup Cost Analysis**: Reviews backup storage costs
- **Performance vs Cost**: Balances performance and cost

### Storage Auditing
- **Persistent Disk Analysis**: Identifies unused or oversized disks
- **Static IP Monitoring**: Finds unused static IP addresses
- **Storage Class Optimization**: Suggests appropriate storage classes
- **Lifecycle Policy Recommendations**: Optimizes data retention

## 🤖 AI Features

### Groq LLM Integration
The dashboard integrates with Groq's fast LLM API to provide:

- **Natural Language Analysis**: Ask questions about your cost data
- **Anomaly Detection**: Identify unusual spending patterns
- **Executive Summaries**: Generate stakeholder-ready reports
- **Smart Recommendations**: Prioritize optimization opportunities
- **Cost Spike Explanations**: Understand why costs changed

### Available Models
- `llama3-8b-8192` (Default, Fast)
- `llama3-70b-8192` (High Quality)
- `mixtral-8x7b-32768` (Balanced)
- `gemma2-9b-it` (Efficient)

### Example AI Queries
```bash
# Ask questions about your data
curl -X POST "http://localhost:8000/api/ai/ask" \
  -d "question=Why are my Cloud Run costs so high?"

# Generate executive summary
curl -X POST "http://localhost:8000/api/ai/executive-summary"

# Analyze dashboard data
curl -X POST "http://localhost:8000/api/ai/analyze"
```

## 📈 Forecasting

### Prophet-Based Cost Prediction
The dashboard uses Facebook's Prophet library for time series forecasting:

- **Historical Analysis**: Uses 6 months of billing data
- **Trend Detection**: Identifies seasonal patterns and trends
- **Confidence Intervals**: Provides uncertainty estimates
- **Service-Level Forecasting**: Predicts costs by service
- **Alert Thresholds**: Recommends budget limits

### Forecast Features
- **Daily Predictions**: Forecast costs day by day
- **Service Breakdown**: Predict costs by GCP service
- **Trend Analysis**: Identify upward/downward trends
- **Budget Recommendations**: Suggest alert thresholds
- **Export Capabilities**: Export forecasts to CSV

## 📊 Report Generation

### PDF Reports
Generate comprehensive PDF reports including:

- **Executive Summary**: High-level cost overview
- **Cost Breakdown**: Detailed spending analysis
- **Audit Results**: Resource optimization findings
- **Recommendations**: Prioritized action items
- **Forecasts**: Future cost predictions
- **Charts and Graphs**: Visual cost analysis

### Report Customization
- **Custom Branding**: Add company logos and colors
- **Filtered Views**: Generate reports for specific services/regions
- **Scheduled Generation**: Automate report creation
- **Multiple Formats**: PDF, JSON, CSV exports

## 🔧 Configuration

### Environment Variables
```bash
# Required
GCP_PROJECT_ID=your-project-id
GCP_BILLING_DATASET=your-project.billing_export

# Optional
GROQ_API_KEY=your_groq_api_key
BIGQUERY_LOCATION=US
GCP_REGIONS=us-central1,us-east1,europe-west1
```

### Configuration Files
The dashboard supports multiple configuration formats:

- **YAML** (`.yaml`, `.yml`)
- **TOML** (`.toml`)
- **JSON** (`.json`)

### Advanced Configuration
```yaml
# Advanced filtering
filters:
  labels:
    - env=production
    - team=engineering
  services:
    - Cloud Run
    - Compute Engine
  regions:
    - us-central1
    - us-east1

# Custom thresholds
thresholds:
  idle_threshold: 0.1  # 10% CPU utilization
  cost_threshold: 100  # $100/month minimum
  utilization_threshold: 0.8  # 80% utilization target
```

## 🚀 Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gcp-finops", "--api", "--api-port", "8000"]
```

### Cloud Run Deployment
```bash
# Build and deploy
gcloud run deploy gcp-finops-dashboard \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=your-project-id
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gcp-finops-dashboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gcp-finops-dashboard
  template:
    metadata:
      labels:
        app: gcp-finops-dashboard
    spec:
      containers:
      - name: gcp-finops-dashboard
        image: gcp-finops-dashboard:latest
        ports:
        - containerPort: 8000
        env:
        - name: GCP_PROJECT_ID
          value: "your-project-id"
        - name: GCP_BILLING_DATASET
          value: "your-project.billing_export"
```

## 🔒 Security

### Authentication
- **Application Default Credentials**: Uses gcloud authentication
- **Service Account**: Supports service account authentication
- **IAM Permissions**: Minimal required permissions

### Required IAM Permissions
```json
{
  "version": 3,
  "bindings": [
    {
      "role": "roles/bigquery.dataViewer",
      "members": ["serviceAccount:your-sa@project.iam.gserviceaccount.com"]
    },
    {
      "role": "roles/run.viewer",
      "members": ["serviceAccount:your-sa@project.iam.gserviceaccount.com"]
    },
    {
      "role": "roles/cloudfunctions.viewer",
      "members": ["serviceAccount:your-sa@project.iam.gserviceaccount.com"]
    },
    {
      "role": "roles/compute.viewer",
      "members": ["serviceAccount:your-sa@project.iam.gserviceaccount.com"]
    },
    {
      "role": "roles/cloudsql.viewer",
      "members": ["serviceAccount:your-sa@project.iam.gserviceaccount.com"]
    },
    {
      "role": "roles/monitoring.viewer",
      "members": ["serviceAccount:your-sa@project.iam.gserviceaccount.com"]
    }
  ]
}
```

### Data Privacy
- **No Data Storage**: Dashboard doesn't store sensitive data
- **Local Processing**: All analysis runs locally
- **Secure API**: API endpoints require proper authentication
- **Audit Logging**: All operations are logged

## 🧪 Testing

### Run Tests
```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=gcp_finops_dashboard

# Run specific test
pytest tests/test_cloud_run_auditor.py
```

### Mock Data
The project includes mock billing data for testing:
```bash
# Generate mock data
python examples/generate_mock_billing_data.py

# Load mock data to BigQuery
python examples/load_mock_data_to_bigquery.py
```

## 📚 Examples

### Basic Usage
```python
# examples/basic_usage.py
from gcp_finops_dashboard.dashboard_runner import DashboardRunner

runner = DashboardRunner(
    project_id="your-project-id",
    billing_dataset="your-project.billing_export"
)

data = runner.run()
print(f"Total cost: ${data.current_month_cost:,.2f}")
```

### Cloud Run Audit
```python
# examples/cloud_run_audit.py
from gcp_finops_dashboard.cloud_run_auditor import CloudRunAuditor

auditor = CloudRunAuditor(cloud_run_client, monitoring_client, project_id)
result = auditor.audit_all_services(["us-central1"])

for rec in result.recommendations:
    print(f"Save ${rec.potential_monthly_savings:,.2f}: {rec.recommendation}")
```

### Forecasting
```python
# examples/forecast_example.py
from gcp_finops_dashboard.forecast_service import ForecastService

forecast_service = ForecastService(bigquery_client, billing_dataset)
forecast = forecast_service.forecast_costs(forecast_days=90)

print(f"Predicted cost: ${forecast.total_predicted_cost:,.2f}")
```

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-repo/gcp-finops-dashboard.git
cd gcp-finops-dashboard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Code Style
- **Black**: Code formatting
- **Ruff**: Linting
- **MyPy**: Type checking
- **Pre-commit**: Git hooks

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [API Documentation](http://localhost:8000/docs) (when API server is running)
- [Configuration Guide](docs/configuration.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

### Community
- [GitHub Issues](https://github.com/your-repo/gcp-finops-dashboard/issues)
- [Discussions](https://github.com/your-repo/gcp-finops-dashboard/discussions)
- [Discord](https://discord.gg/your-discord)

### Professional Support
For enterprise support, custom features, or consulting services, contact us at support@yourcompany.com.

## 🗺️ Roadmap

### Upcoming Features
- [ ] **Multi-Cloud Support**: AWS and Azure integration
- [ ] **Real-time Monitoring**: Live cost tracking
- [ ] **Automated Optimization**: Auto-scaling recommendations
- [ ] **Cost Allocation**: Team and project cost tracking
- [ ] **Budget Management**: Automated budget alerts
- [ ] **Compliance Reporting**: SOC2, GDPR compliance reports
- [ ] **Mobile App**: iOS and Android applications
- [ ] **Slack Integration**: Cost alerts in Slack
- [ ] **Terraform Integration**: Infrastructure as Code optimization

### Version History
- **v1.0.0**: Initial release with core auditing features
- **v1.1.0**: Added AI-powered insights and forecasting
- **v1.2.0**: Enhanced API and report generation
- **v1.3.0**: Multi-region support and advanced filtering

## 🙏 Acknowledgments

- **Google Cloud Platform**: For providing excellent APIs and services
- **Prophet**: For time series forecasting capabilities
- **Groq**: For fast LLM inference
- **FastAPI**: For the excellent web framework
- **Rich**: For beautiful terminal output
- **Contributors**: Thank you to all contributors who help improve this project

---

**Made with ❤️ for the GCP community**

For more information, visit my [website](https://angad2002.vercel.app)
