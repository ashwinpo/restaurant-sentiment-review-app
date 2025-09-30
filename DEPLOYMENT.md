# Databricks Asset Bundle Deployment Guide

This guide covers deploying the Bloomin' Review App using Databricks Asset Bundles (DAB).

## Prerequisites

1. **Databricks CLI** version 0.250.0 or above
   ```bash
   # Install or upgrade
   curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
   
   # Verify version
   databricks --version
   ```

2. **Authentication** to your Databricks workspace
   ```bash
   # Configure authentication (interactive)
   databricks configure
   
   # Or use environment variables
   export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
   export DATABRICKS_TOKEN="your-token"
   ```

3. **Frontend built** and ready
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

## Configuration for Your Environment

### Step 1: Update `databricks.yml`

Edit the workspace URLs and user emails in `databricks.yml`:

```yaml
targets:
  dev:
    workspace:
      host: https://YOUR-WORKSPACE.cloud.databricks.com  # Your dev workspace
    permissions:
      - user_name: your.email@company.com  # Your email
```

### Step 2: Set Environment Variables

Create a `.databricks/project.json` file (already created, just update values):

```json
{
  "profile": "DEFAULT",
  "environments": {
    "dev": {
      "variables": {
        "warehouse_id": "abc123def456"  # Your SQL Warehouse ID
      }
    }
  }
}
```

**OR** set via CLI when deploying:
```bash
export DATABRICKS_BUNDLE_VAR_warehouse_id="abc123def456"
export DATABRICKS_BUNDLE_VAR_catalog="main"
export DATABRICKS_BUNDLE_VAR_schema="your_schema"
```

## Testing the Bundle Locally

### 1. Validate Configuration

Check if your `databricks.yml` is valid:
```bash
databricks bundle validate
```

This will:
- Parse the YAML
- Check for syntax errors
- Validate variable references
- Confirm authentication

### 2. Review Deployment Plan

See what will be deployed without actually deploying:
```bash
databricks bundle validate --target dev
```

### 3. Generate Deployment Manifest

See the full expanded configuration:
```bash
databricks bundle deploy --target dev --dry-run
```

## Deploying to Databricks

### Deploy to Development Environment

```bash
# Deploy to dev (default target)
databricks bundle deploy

# Or explicitly specify target
databricks bundle deploy --target dev
```

**What this does:**
1. Uploads your code to Databricks workspace
2. Creates the app resource in `/Workspace/Users/your.email/.bundle/bloomin_review_app/dev/`
3. Configures environment variables
4. Sets up permissions
5. Starts the app

### Check Deployment Status

```bash
# View deployment summary
databricks bundle summary

# View app logs
databricks bundle run bloomin_review --target dev

# Or check in Databricks UI
# Navigate to: Workspace > Apps > bloomin-review-dev
```

### Access Your Deployed App

After deployment, you'll see output like:
```
App URL: https://your-workspace.cloud.databricks.com/apps/bloomin-review-dev
```

## Environment-Specific Deployments

### Production Deployment

```bash
# Set production warehouse ID
export DATABRICKS_BUNDLE_VAR_warehouse_id="prod-warehouse-id"

# Deploy to production
databricks bundle deploy --target prod
```

### Client Environment Deployment

For deploying to client environments with different catalogs/schemas:

1. **Create a client-specific variables file** (`.databricks/client-config.json`):
   ```json
   {
     "variables": {
       "catalog": "client_catalog_name",
       "schema": "client_schema_name",
       "backend_table_name": "client_table_name",
       "warehouse_id": "client_warehouse_id"
     }
   }
   ```

2. **Deploy with overrides**:
   ```bash
   # Set variables via environment
   export DATABRICKS_BUNDLE_VAR_catalog="client_catalog"
   export DATABRICKS_BUNDLE_VAR_schema="client_schema"
   export DATABRICKS_BUNDLE_VAR_backend_table_name="guest_reviews"
   export DATABRICKS_BUNDLE_VAR_warehouse_id="client_warehouse"
   
   # Deploy to client target
   databricks bundle deploy --target client
   ```

3. **Or update `databricks.yml`** directly for the client and commit:
   ```yaml
   targets:
     client_xyz:
       mode: production
       workspace:
         host: https://client-workspace.cloud.databricks.com
       variables:
         catalog: "xyz_production"
         schema: "reviews"
         backend_table_name: "sentiment_analysis"
         warehouse_id: "xyz_warehouse_123"
   ```

## Table Configuration

The app uses these tables (automatically namespaced per environment):

1. **Backend Data Table**: `${catalog}.${schema}.${backend_table_name}`
   - Your source data table with reviews and ML predictions
   
2. **Evaluation Table**: `${catalog}.${schema}.${backend_table_name}_evaluation`
   - Auto-created by the app
   - Stores human validation results
   
3. **Recommendations Table**: `${catalog}.${schema}.${backend_table_name}_evaluation_recommendations`
   - Auto-created by the app
   - Stores recommendation mappings (when vector search is enabled)

**Example for client:**
- Backend: `client_prod.reviews.guest_feedback`
- Evaluation: `client_prod.reviews.guest_feedback_evaluation`
- Recommendations: `client_prod.reviews.guest_feedback_evaluation_recommendations`

## Updating a Deployed App

### Update Code

```bash
# Make your code changes
git pull  # or edit files

# Rebuild frontend if needed
cd frontend && npm run build && cd ..

# Redeploy
databricks bundle deploy --target dev
```

### Update Configuration

```bash
# Edit databricks.yml
vim databricks.yml

# Validate changes
databricks bundle validate --target dev

# Deploy changes
databricks bundle deploy --target dev
```

## Troubleshooting

### Validation Errors

```bash
# See detailed validation output
databricks bundle validate --target dev --debug
```

### Deployment Failures

```bash
# View deployment logs
databricks bundle deploy --target dev --debug

# Check app logs in Databricks UI
# Navigate to: Workspace > Apps > [your-app] > Logs
```

### Wrong Table Names

If tables aren't being found:

1. Check environment variables are set correctly:
   ```bash
   databricks bundle summary --target dev
   ```

2. Verify table exists in catalog:
   ```sql
   SHOW TABLES IN your_catalog.your_schema;
   ```

3. Check app logs for the actual table name being used

## Destroying/Removing Deployments

```bash
# Remove a specific deployment
databricks bundle destroy --target dev

# This will:
# - Stop the app
# - Remove app resources
# - Clean up workspace files
# Note: Does NOT delete your data tables
```

## Best Practices

### For Development
- Use `dev` target for testing
- Keep warehouse separate from production
- Use smaller/cheaper warehouse for dev

### For Production
- Use `prod` target
- Set up proper permissions (group-based)
- Use production-grade warehouse
- Enable monitoring and alerts

### For Client Deployments
- Create a dedicated target per client
- Use environment variables for flexibility
- Document client-specific configurations
- Test in dev before deploying to client
- Keep client configurations in version control

## Quick Reference

```bash
# Validate
databricks bundle validate

# Deploy to dev (default)
databricks bundle deploy

# Deploy to specific target
databricks bundle deploy --target prod

# View deployed resources
databricks bundle summary

# Destroy deployment
databricks bundle destroy --target dev

# Set variables via environment
export DATABRICKS_BUNDLE_VAR_warehouse_id="abc123"
export DATABRICKS_BUNDLE_VAR_catalog="main"
export DATABRICKS_BUNDLE_VAR_schema="reviews"
```

## Client Onboarding Checklist

When deploying for a new client:

- [ ] Get client's Databricks workspace URL
- [ ] Get SQL Warehouse ID from client
- [ ] Confirm catalog and schema names
- [ ] Confirm backend table name and structure
- [ ] Update `databricks.yml` with client target
- [ ] Set permissions appropriately
- [ ] Test connection to client tables
- [ ] Deploy to client workspace
- [ ] Verify app can read data
- [ ] Verify evaluation table creation
- [ ] Provide client with app URL
- [ ] Train client users on the app

## Support

For issues or questions:
1. Check logs in Databricks UI
2. Run validation: `databricks bundle validate --debug`
3. Check table permissions in Unity Catalog
4. Verify SQL Warehouse is running

