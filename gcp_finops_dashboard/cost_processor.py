"""BigQuery cost processor for billing data analysis."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from google.cloud import bigquery
import pandas as pd

from .types import CostData
from .helpers import (
    get_current_month_range,
    get_last_month_range,
    get_date_range
)


class CostProcessor:
    """Process cost data from BigQuery billing export."""
    
    def __init__(
        self,
        client: bigquery.Client,
        billing_dataset: str,
        billing_table_prefix: str = "gcp_billing_export_v1"
    ):
        """Initialize cost processor.
        
        Args:
            client: BigQuery client
            billing_dataset: Full dataset ID (e.g., 'project.dataset_name')
            billing_table_prefix: Table prefix for billing export tables
        """
        self.client = client
        self.billing_dataset = billing_dataset
        self.billing_table_prefix = billing_table_prefix
    
    def get_current_month_cost(self, project_id: Optional[str] = None) -> float:
        """Get total cost for current month.
        
        Args:
            project_id: Filter by project ID (optional)
        
        Returns:
            Total cost for current month
        """
        start_date, end_date = get_current_month_range()
        return self._get_total_cost(start_date, end_date, project_id)
    
    def get_last_month_cost(self, project_id: Optional[str] = None) -> float:
        """Get total cost for last month.
        
        Args:
            project_id: Filter by project ID (optional)
        
        Returns:
            Total cost for last month
        """
        start_date, end_date = get_last_month_range()
        return self._get_total_cost(start_date, end_date, project_id)
    
    def get_ytd_cost(self, project_id: Optional[str] = None) -> float:
        """Get year-to-date total cost.
        
        Args:
            project_id: Filter by project ID (optional)
        
        Returns:
            YTD total cost
        """
        year_start = datetime.now().replace(month=1, day=1).strftime("%Y%m%d")
        today = datetime.now().strftime("%Y%m%d")
        return self._get_total_cost(year_start, today, project_id)
    
    def get_service_costs(
        self,
        start_date: str,
        end_date: str,
        project_id: Optional[str] = None,
        top_n: int = 10
    ) -> Dict[str, float]:
        """Get cost breakdown by service.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_id: Filter by project ID (optional)
            top_n: Return top N services by cost
        
        Returns:
            Dictionary of service name to cost
        """
        # Handle project field as RECORD (STRUCT) format
        if project_id:
            project_filter = f"""AND project.id = '{project_id}'"""
        else:
            project_filter = ""
        
        query = f"""
            SELECT 
                service.description as service_name,
                SUM(cost) as total_cost
            FROM `{self.billing_dataset}.{self.billing_table_prefix}_*`
            WHERE _TABLE_SUFFIX BETWEEN @start_date AND @end_date
            {project_filter}
            GROUP BY service_name
            ORDER BY total_cost DESC
            LIMIT {top_n}
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
                bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        
        return {row.service_name: float(row.total_cost) for row in results}
    
    def get_service_cost_trend(
        self,
        service_name: str,
        months: int = 6,
        project_id: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """Get monthly cost trend for a service.
        
        Args:
            service_name: Service name (e.g., 'Cloud Run')
            months: Number of months to look back
            project_id: Filter by project ID (optional)
        
        Returns:
            List of (month, cost) tuples
        """
        start_date, end_date = get_date_range(months)
        # Handle project field as RECORD (STRUCT) format
        if project_id:
            project_filter = f"""AND project.id = '{project_id}'"""
        else:
            project_filter = ""
        
        query = f"""
            SELECT 
                FORMAT_DATE('%Y-%m', DATE(usage_start_time)) as month,
                SUM(cost) as total_cost
            FROM `{self.billing_dataset}.{self.billing_table_prefix}_*`
            WHERE _TABLE_SUFFIX BETWEEN @start_date AND @end_date
            AND service.description = @service_name
            {project_filter}
            GROUP BY month
            ORDER BY month
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
                bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
                bigquery.ScalarQueryParameter("service_name", "STRING", service_name),
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        
        return [(row.month, float(row.total_cost)) for row in results]
    
    def get_cloud_run_costs(
        self,
        start_date: str,
        end_date: str,
        project_id: Optional[str] = None
    ) -> Dict[str, float]:
        """Get Cloud Run cost breakdown by service.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_id: Filter by project ID (optional)
        
        Returns:
            Dictionary of service name to cost
        """
        # Handle project field as RECORD (STRUCT) format
        if project_id:
            project_filter = f"""AND project.id = '{project_id}'"""
        else:
            project_filter = ""
        
        query = f"""
            SELECT 
                labels.value as service_name,
                SUM(cost) as total_cost
            FROM `{self.billing_dataset}.{self.billing_table_prefix}_*`,
            UNNEST(CAST(labels AS ARRAY<STRUCT<key STRING, value STRING>>)) as labels
            WHERE _TABLE_SUFFIX BETWEEN @start_date AND @end_date
            AND (
                JSON_EXTRACT_SCALAR(service, '$.description') = 'Cloud Run' OR
                CAST(service AS STRING) LIKE '%Cloud Run%'
            )
            AND labels.key = 'service_name'
            {project_filter}
            GROUP BY service_name
            ORDER BY total_cost DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
                bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
            ]
        )
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            return {row.service_name: float(row.total_cost) for row in results}
        except Exception:
            # If service_name label doesn't exist, return empty dict
            return {}
    
    def get_sku_costs(
        self,
        service_name: str,
        start_date: str,
        end_date: str,
        project_id: Optional[str] = None,
        top_n: int = 10
    ) -> List[CostData]:
        """Get SKU-level cost breakdown for a service.
        
        Args:
            service_name: Service name (e.g., 'Cloud Run')
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_id: Filter by project ID (optional)
            top_n: Return top N SKUs by cost
        
        Returns:
            List of CostData objects
        """
        # Handle project field as RECORD (STRUCT) format
        if project_id:
            project_filter = f"""AND project.id = '{project_id}'"""
        else:
            project_filter = ""
        
        query = f"""
            SELECT 
                service.description as service_name,
                sku.description as sku_name,
                SUM(cost) as total_cost,
                SUM(usage.amount) as usage_amount,
                usage.unit as usage_unit,
                project.id as project_id,
                location.region as region
            FROM `{self.billing_dataset}.{self.billing_table_prefix}_*`
            WHERE _TABLE_SUFFIX BETWEEN @start_date AND @end_date
            AND service.description = @service_name
            {project_filter}
            GROUP BY service_name, sku_name, usage_unit, project_id, region
            ORDER BY total_cost DESC
            LIMIT {top_n}
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
                bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
                bigquery.ScalarQueryParameter("service_name", "STRING", service_name),
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        
        cost_data = []
        for row in results:
            cost_data.append(CostData(
                service=row.service_name,
                sku=row.sku_name,
                cost=float(row.total_cost),
                usage_amount=float(row.usage_amount),
                usage_unit=row.usage_unit,
                project_id=row.project_id,
                region=row.region,
            ))
        
        return cost_data
    
    def _get_total_cost(
        self,
        start_date: str,
        end_date: str,
        project_id: Optional[str] = None
    ) -> float:
        """Get total cost for a date range.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_id: Filter by project ID (optional)
        
        Returns:
            Total cost
        """
        # Handle project field as RECORD (STRUCT) format
        if project_id:
            project_filter = f"""AND project.id = '{project_id}'"""
        else:
            project_filter = ""
        
        query = f"""
            SELECT 
                SUM(cost) as total_cost
            FROM `{self.billing_dataset}.{self.billing_table_prefix}_*`
            WHERE _TABLE_SUFFIX BETWEEN @start_date AND @end_date
            {project_filter}
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
                bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        
        for row in results:
            return float(row.total_cost) if row.total_cost else 0.0
        
        return 0.0

