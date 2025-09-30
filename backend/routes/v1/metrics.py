from fastapi import APIRouter, Query
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from models import MetricsOverview
from mock_data import get_mock_metrics

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/metrics/overview", response_model=MetricsOverview)
async def get_metrics_overview(
    use_databricks: bool = Query(True, description="Use Databricks data source (set to false for mock data)")
):
    """Get dashboard metrics overview"""
    
    if not use_databricks:
        # Fallback to mock data
        return get_mock_metrics()
    
    try:
        # Get real metrics from Databricks
        from databricks_client import get_metrics_data
        metrics_data = get_metrics_data()
        
        return MetricsOverview(**metrics_data)
        
    except Exception as e:
        logger.error(f"Failed to get metrics from Databricks: {str(e)}")
        # Fallback to mock data on error
        return get_mock_metrics()
