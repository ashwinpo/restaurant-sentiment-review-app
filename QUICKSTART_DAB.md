# Quick Start: Testing Your Databricks Asset Bundle

Follow these steps to test your DAB configuration before deploying.

## Prerequisites Check

```bash
# 1. Check Databricks CLI version (need 0.250.0+)
databricks --version

# 2. Check you're authenticated
databricks current-user me

# 3. Verify frontend is built
ls -la frontend/dist/index.html
```

## Quick Test Workflow

### Step 1: Update Configuration (5 mins)

1. **Edit `databricks.yml`** (lines 40-41):
   ```yaml
   workspace:
     host: https://YOUR-WORKSPACE-URL.cloud.databricks.com
   ```
   Replace with your actual workspace URL (you can find this in your browser when logged into Databricks)

2. **Update your email** (line 57):
   ```yaml
   permissions:
     - user_name: your.email@databricks.com
   ```

3. **Set your warehouse ID**:
   ```bash
   export DATABRICKS_BUNDLE_VAR_warehouse_id="YOUR_WAREHOUSE_ID"
   ```
   
   To find your warehouse ID:
   - Go to Databricks → SQL Warehouses
   - Click on your warehouse
   - Copy the ID from the URL: `.../sql/warehouses/abc123def456` → use `abc123def456`

### Step 2: Validate (1 min)

```bash
# Test if configuration is valid
databricks bundle validate

# Should output: "✓ Configuration is valid"
```

**If you get errors:**
- Check YAML syntax (indentation must be exact)
- Verify workspace URL is correct
- Make sure you're authenticated

### Step 3: View Deployment Plan (1 min)

```bash
# See what will be deployed (without actually deploying)
databricks bundle deploy --target dev --dry-run
```

This shows:
- Where files will be uploaded
- What environment variables will be set
- What permissions will be applied

### Step 4: Deploy to Dev (2 mins)

```bash
# Deploy to development environment
databricks bundle deploy --target dev
```

**Expected output:**
```
Uploading bundle files to /Workspace/Users/your.email/.bundle/bloomin_review_app/dev...
Creating app: bloomin-review-dev
App URL: https://your-workspace.cloud.databricks.com/apps/bloomin-review-dev
✓ Deployment successful
```

### Step 5: Verify Deployment (1 min)

```bash
# View deployment summary
databricks bundle summary --target dev
```

**Check in Databricks UI:**
1. Go to your workspace
2. Navigate to **Workspace** → **Apps**
3. Find **bloomin-review-dev**
4. Click to open and verify it's running

### Step 6: Test the App (2 mins)

1. Click on the app URL from the deployment output
2. Should see the dashboard with metrics
3. Try navigating to a review to validate

**Check logs if issues:**
- In Databricks UI: Apps → bloomin-review-dev → Logs
- Look for database connection errors
- Verify table names are correct

## Common Issues and Fixes

### Issue: "Warehouse ID not found"

**Fix:** Verify warehouse ID is set correctly
```bash
# Check current value
echo $DATABRICKS_BUNDLE_VAR_warehouse_id

# Set it again
export DATABRICKS_BUNDLE_VAR_warehouse_id="abc123def456"

# Redeploy
databricks bundle deploy --target dev
```

### Issue: "Table not found"

**Fix:** Check if table names are correct
```bash
# View what table names the app will use
databricks bundle summary --target dev | grep BACKEND_DATA_TABLE

# To override table name
export DATABRICKS_BUNDLE_VAR_catalog="your_catalog"
export DATABRICKS_BUNDLE_VAR_schema="your_schema"
export DATABRICKS_BUNDLE_VAR_backend_table_name="your_table"

databricks bundle deploy --target dev
```

### Issue: "Authentication failed"

**Fix:** Re-authenticate
```bash
databricks configure
# Follow prompts to enter workspace URL and token
```

### Issue: "Bundle validation failed"

**Fix:** Check YAML syntax
```bash
# Run with debug for detailed error
databricks bundle validate --target dev --debug

# Common issues:
# - Indentation must be spaces (not tabs)
# - Strings with special chars need quotes
# - Variable references must use ${var.name} syntax
```

## Testing Different Configurations

### Test with Different Catalog/Schema

```bash
# Override table configuration for testing
export DATABRICKS_BUNDLE_VAR_catalog="test_catalog"
export DATABRICKS_BUNDLE_VAR_schema="test_schema"
export DATABRICKS_BUNDLE_VAR_backend_table_name="test_table"

# Deploy with test configuration
databricks bundle deploy --target dev

# Verify in app logs that correct table is being used
```

### Test Client Configuration

```bash
# Deploy using client target (simulates client environment)
export DATABRICKS_BUNDLE_VAR_warehouse_id="test_warehouse"
export DATABRICKS_BUNDLE_VAR_catalog="client_catalog"
export DATABRICKS_BUNDLE_VAR_schema="client_schema"

databricks bundle deploy --target client
```

## Clean Up After Testing

```bash
# Remove the deployed app
databricks bundle destroy --target dev

# This removes the app but keeps your data tables safe
```

## Next Steps

Once testing is successful:

1. **Document your configuration** - Save the warehouse ID and table names you used
2. **Set up prod target** - Update `databricks.yml` with production settings
3. **Create client configs** - Add targets for each client environment
4. **Set up CI/CD** - Automate deployments (see DEPLOYMENT.md)

## Quick Reference Commands

```bash
# Validate configuration
databricks bundle validate

# Deploy to dev
databricks bundle deploy --target dev

# View deployment
databricks bundle summary

# Check app logs
# (Go to Databricks UI → Apps → your-app → Logs)

# Destroy deployment
databricks bundle destroy --target dev
```

## Getting Help

1. **Validation errors**: Run with `--debug` flag
2. **App not starting**: Check logs in Databricks UI
3. **Table connection errors**: Verify warehouse is running and tables exist
4. **Permission errors**: Check Unity Catalog permissions on tables

**Full Documentation**: See `DEPLOYMENT.md` for comprehensive guide

