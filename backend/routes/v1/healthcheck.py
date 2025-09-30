import os
from datetime import datetime, timezone
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/healthcheck")
async def healthcheck() -> Dict[str, str]:
    """Return the API status."""
    return {"status": "OK", "timestamp": datetime.now(timezone.utc).isoformat()}

@router.get("/debug/env")
async def debug_environment() -> Dict[str, Any]:
    """Debug endpoint to check available environment variables (for deployment troubleshooting)."""
    databricks_env_vars = {
        # OAuth Service Principal
        "DATABRICKS_SERVER_HOSTNAME": bool(os.environ.get("DATABRICKS_SERVER_HOSTNAME")),
        "DATABRICKS_HTTP_PATH": bool(os.environ.get("DATABRICKS_HTTP_PATH")),
        "DATABRICKS_CLIENT_ID": bool(os.environ.get("DATABRICKS_CLIENT_ID")),
        "DATABRICKS_CLIENT_SECRET": bool(os.environ.get("DATABRICKS_CLIENT_SECRET")),
        
        # Databricks Apps built-in
        "DATABRICKS_HOST": bool(os.environ.get("DATABRICKS_HOST")),
        "DATABRICKS_TOKEN": bool(os.environ.get("DATABRICKS_TOKEN")),
        
        # Legacy
        "DATABRICKS_WAREHOUSE_ID": bool(os.environ.get("DATABRICKS_WAREHOUSE_ID")),
        "DB_HOST": bool(os.environ.get("DB_HOST")),
        "DB_PAT": bool(os.environ.get("DB_PAT")),
    }
    
    # Show partial values for debugging (first few characters only)
    partial_values = {}
    for key in databricks_env_vars:
        value = os.environ.get(key)
        if value:
            if "SECRET" in key or "TOKEN" in key or "PAT" in key:
                partial_values[key] = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                partial_values[key] = value
        else:
            partial_values[key] = None
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment_variables_available": databricks_env_vars,
        "partial_values": partial_values,
        "recommended_auth": "DATABRICKS_HOST + DATABRICKS_TOKEN (Databricks Apps built-in)" if databricks_env_vars["DATABRICKS_HOST"] and databricks_env_vars["DATABRICKS_TOKEN"] else "OAuth Service Principal"
    }
