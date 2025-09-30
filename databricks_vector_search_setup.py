# Databricks notebook source
# MAGIC %md
# MAGIC # Vector Search Index Setup for Bloomin Review Comments
# MAGIC 
# MAGIC This notebook creates a vector search index from the survey review comments table to enable semantic similarity search.
# MAGIC This will power the "recommended" tab by finding semantically similar comments when corrections are made.
# MAGIC 
# MAGIC ## Configuration
# MAGIC Update the configuration section below to match your environment.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔧 Environment Setup

# COMMAND ----------

# Install required libraries
%pip install databricks-vectorsearch

# COMMAND ----------

# Restart Python to ensure libraries are loaded
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📋 Configuration Section
# MAGIC 
# MAGIC **Update these variables to match your environment:**

# COMMAND ----------

# =============================================================================
# CONFIGURATION - UPDATE THESE VALUES FOR YOUR ENVIRONMENT
# =============================================================================

# Source table configuration
SOURCE_TABLE_NAME = "main.ashwinpo_bloomin.aspect_sentiment"
PRIMARY_KEY_COLUMN = "Response_Id"
TEXT_COLUMN = "Question_Response"  # The column containing the review text

# Vector search configuration
VECTOR_SEARCH_ENDPOINT_NAME = "bloomin_review_vector_endpoint"
VECTOR_INDEX_NAME = "main.ashwinpo_bloomin.review_vector_index"

# Embedding configuration
EMBEDDING_MODEL_ENDPOINT_NAME = "databricks-bge-large-en"  # Databricks managed embedding model
PIPELINE_TYPE = "TRIGGERED"  # Options: "TRIGGERED" or "CONTINUOUS"
ENDPOINT_TYPE = "STANDARD"  # Options: "STANDARD" or "STORAGE_OPTIMIZED"

# Additional columns to include in search results (beyond primary key and text)
ADDITIONAL_COLUMNS = [
    "Question_Label",
    "sentiment_analysis", 
    "aspect_pricing",
    "aspect_service",
    "aspect_food_and_beverage",
    "aspect_ambiance",
    "aspect_cleanliness",
    "aspect_wait_time",
    "aspect_other"
]

# =============================================================================
# END CONFIGURATION
# =============================================================================

print("📋 Configuration loaded:")
print(f"  Source Table: {SOURCE_TABLE_NAME}")
print(f"  Vector Index: {VECTOR_INDEX_NAME}")
print(f"  Endpoint: {VECTOR_SEARCH_ENDPOINT_NAME}")
print(f"  Text Column: {TEXT_COLUMN}")
print(f"  Primary Key: {PRIMARY_KEY_COLUMN}")

# COMMAND ----------

# Import required libraries
from databricks.vector_search.client import VectorSearchClient
from pyspark.sql import SparkSession
import json

# Initialize clients
spark = SparkSession.builder.getOrCreate()
vs_client = VectorSearchClient()

print("✅ Libraries imported successfully")
print(f"✅ Spark session: {spark.version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔍 Data Validation

# COMMAND ----------

# Validate source table exists and check structure
print(f"🔍 Validating source table: {SOURCE_TABLE_NAME}")

try:
    # Check if table exists
    df = spark.table(SOURCE_TABLE_NAME)
    row_count = df.count()
    columns = df.columns
    
    print(f"✅ Table exists with {row_count:,} rows")
    print(f"✅ Columns: {', '.join(columns)}")
    
    # Validate required columns exist
    if PRIMARY_KEY_COLUMN not in columns:
        raise ValueError(f"❌ Primary key column '{PRIMARY_KEY_COLUMN}' not found in table")
    
    if TEXT_COLUMN not in columns:
        raise ValueError(f"❌ Text column '{TEXT_COLUMN}' not found in table")
    
    print(f"✅ Required columns validated")
    
    # Show sample data
    print("\n📊 Sample data:")
    sample_df = df.select(PRIMARY_KEY_COLUMN, TEXT_COLUMN).limit(3)
    sample_df.show(truncate=False)
    
    # Check for null values in key columns
    null_primary_keys = df.filter(df[PRIMARY_KEY_COLUMN].isNull()).count()
    null_text_values = df.filter(df[TEXT_COLUMN].isNull()).count()
    empty_text_values = df.filter((df[TEXT_COLUMN] == "") | (df[TEXT_COLUMN].isNull())).count()
    
    print(f"📊 Data quality check:")
    print(f"  Null primary keys: {null_primary_keys}")
    print(f"  Null text values: {null_text_values}")
    print(f"  Empty/null text values: {empty_text_values}")
    
    if null_primary_keys > 0:
        print("⚠️  Warning: Found null primary keys - these rows will be excluded from index")
    
    if empty_text_values > 0:
        print("⚠️  Warning: Found empty text values - these rows will be excluded from index")
    
    # Calculate valid rows for indexing
    valid_rows = row_count - null_primary_keys - empty_text_values
    print(f"✅ Valid rows for indexing: {valid_rows:,}")
    
except Exception as e:
    print(f"❌ Error validating source table: {str(e)}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔄 Enable Change Data Feed (CDC)

# COMMAND ----------

# Enable Change Data Feed on the source table (required for vector search)
print(f"🔄 Enabling Change Data Feed on table: {SOURCE_TABLE_NAME}")

try:
    # Check if CDC is already enabled
    table_properties_query = f"DESCRIBE TABLE EXTENDED {SOURCE_TABLE_NAME}"
    table_info = spark.sql(table_properties_query).collect()
    
    # Look for delta.enableChangeDataFeed in table properties
    cdc_enabled = False
    for row in table_info:
        if row[0] == "Table Properties" and row[1]:
            properties = row[1]
            if "delta.enableChangeDataFeed" in properties and "true" in properties:
                cdc_enabled = True
                break
    
    if cdc_enabled:
        print(f"✅ Change Data Feed is already enabled on {SOURCE_TABLE_NAME}")
    else:
        print(f"🔧 Enabling Change Data Feed on {SOURCE_TABLE_NAME}...")
        
        # Enable CDC on the table
        enable_cdc_query = f"""
        ALTER TABLE {SOURCE_TABLE_NAME} 
        SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
        """
        
        spark.sql(enable_cdc_query)
        print(f"✅ Change Data Feed enabled successfully on {SOURCE_TABLE_NAME}")
        print("📝 Note: This enables tracking of changes for vector index synchronization")
    
    # Verify CDC is enabled
    print("🔍 Verifying Change Data Feed status...")
    verification_query = f"SHOW TBLPROPERTIES {SOURCE_TABLE_NAME}"
    properties_df = spark.sql(verification_query)
    
    cdc_property = properties_df.filter(properties_df.key == "delta.enableChangeDataFeed").collect()
    if cdc_property and cdc_property[0].value == "true":
        print("✅ Change Data Feed verification successful")
    else:
        print("⚠️  Warning: Could not verify Change Data Feed status")
    
except Exception as e:
    print(f"❌ Error enabling Change Data Feed: {str(e)}")
    print("💡 You may need to enable CDC manually:")
    print(f"   ALTER TABLE {SOURCE_TABLE_NAME} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🌐 Vector Search Endpoint Setup

# COMMAND ----------

# Create or verify vector search endpoint
print(f"🌐 Setting up vector search endpoint: {VECTOR_SEARCH_ENDPOINT_NAME}")

try:
    # Check if endpoint already exists
    existing_endpoints = vs_client.list_endpoints()
    endpoint_names = [ep.get('name', '') for ep in existing_endpoints.get('endpoints', [])]
    
    if VECTOR_SEARCH_ENDPOINT_NAME in endpoint_names:
        print(f"✅ Endpoint '{VECTOR_SEARCH_ENDPOINT_NAME}' already exists")
        
        # Get endpoint details
        endpoint_info = vs_client.get_endpoint(VECTOR_SEARCH_ENDPOINT_NAME)
        print(f"📊 Endpoint status: {endpoint_info.get('endpoint_status', {}).get('state', 'Unknown')}")
        
    else:
        print(f"🔧 Creating new endpoint: {VECTOR_SEARCH_ENDPOINT_NAME}")
        
        # Create the endpoint
        vs_client.create_endpoint(
            name=VECTOR_SEARCH_ENDPOINT_NAME,
            endpoint_type=ENDPOINT_TYPE
        )
        
        print(f"✅ Endpoint '{VECTOR_SEARCH_ENDPOINT_NAME}' created successfully")
        print("⏳ Note: Endpoint may take a few minutes to become ready")
        
        # Wait for endpoint to be ready (optional)
        print("⏳ Waiting for endpoint to be ready...")
        vs_client.wait_for_endpoint(VECTOR_SEARCH_ENDPOINT_NAME)
        print("✅ Endpoint is ready!")

except Exception as e:
    print(f"❌ Error setting up endpoint: {str(e)}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔄 Primary Key Type Conversion

# COMMAND ----------

# Check and fix primary key data type for vector search compatibility
print(f"🔍 Checking primary key data type: {PRIMARY_KEY_COLUMN}")

try:
    # Get the schema of the source table
    table_schema = spark.table(SOURCE_TABLE_NAME).schema
    primary_key_field = None
    
    for field in table_schema.fields:
        if field.name == PRIMARY_KEY_COLUMN:
            primary_key_field = field
            break
    
    if primary_key_field is None:
        raise ValueError(f"Primary key column '{PRIMARY_KEY_COLUMN}' not found in table schema")
    
    primary_key_type = str(primary_key_field.dataType)
    print(f"📊 Current primary key type: {primary_key_type}")
    
    # Check if the primary key type is supported by vector search
    supported_types = ["bigint", "int", "smallint", "string"]
    is_supported = any(supported_type in primary_key_type.lower() for supported_type in supported_types)
    
    if is_supported and "string" in primary_key_type.lower():
        print(f"✅ Primary key type is supported: {primary_key_type}")
        # Use the original table
        VECTOR_SOURCE_TABLE = SOURCE_TABLE_NAME
    else:
        print(f"⚠️  Primary key type '{primary_key_type}' is not supported by vector search")
        print("🔧 Creating a view with string-converted primary key...")
        
        # Create a view with the primary key converted to string
        view_name = f"{SOURCE_TABLE_NAME}_vector_view"
        VECTOR_SOURCE_TABLE = view_name
        
        # Get all column names
        columns = [field.name for field in table_schema.fields]
        
        # Build SELECT statement with primary key conversion
        select_columns = []
        for col in columns:
            if col == PRIMARY_KEY_COLUMN:
                select_columns.append(f"CAST({col} AS STRING) as {col}")
            else:
                select_columns.append(col)
        
        select_statement = ", ".join(select_columns)
        
        # Create the view
        create_view_sql = f"""
        CREATE OR REPLACE VIEW {view_name} AS
        SELECT {select_statement}
        FROM {SOURCE_TABLE_NAME}
        """
        
        spark.sql(create_view_sql)
        print(f"✅ Created view with string primary key: {view_name}")
        
        # Verify the view
        view_schema = spark.table(view_name).schema
        for field in view_schema.fields:
            if field.name == PRIMARY_KEY_COLUMN:
                print(f"✅ Primary key type in view: {field.dataType}")
                break
        
        # Enable CDC on the view (inherit from base table)
        print(f"📝 Note: View will inherit CDC settings from base table: {SOURCE_TABLE_NAME}")
    
    print(f"🎯 Vector search will use table/view: {VECTOR_SOURCE_TABLE}")
    
except Exception as e:
    print(f"❌ Error checking/converting primary key type: {str(e)}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🧮 Vector Index Creation

# COMMAND ----------

# Create the vector search index
print(f"🧮 Creating vector search index: {VECTOR_INDEX_NAME}")

try:
    # Check if index already exists
    try:
        existing_index = vs_client.get_index(VECTOR_INDEX_NAME)
        print(f"✅ Index '{VECTOR_INDEX_NAME}' already exists")
        
        # Handle both dict and object return types
        try:
            if hasattr(existing_index, 'get'):
                # Dictionary-like response
                index_status = existing_index.get('status', {}).get('ready', 'Unknown')
                index_details = existing_index.get('spec', {})
            else:
                # VectorSearchIndex object - try to get status differently
                index_status = "exists (status unknown)"
                index_details = {}
            
            print(f"📊 Index status: {index_status}")
            
            if index_details:
                print(f"📊 Index details:")
                print(f"  Source table: {index_details.get('source_table')}")
                print(f"  Primary key: {index_details.get('primary_key')}")
                print(f"  Embedding source: {index_details.get('embedding_source_column')}")
                print(f"  Pipeline type: {index_details.get('pipeline_type')}")
                
        except Exception as detail_error:
            print(f"📊 Index exists (detail retrieval failed: {detail_error})")
        
    except Exception:
        print(f"🔧 Index does not exist, creating: {VECTOR_INDEX_NAME}")
        
        # Prepare columns to include in the index
        columns_to_include = [PRIMARY_KEY_COLUMN, TEXT_COLUMN] + ADDITIONAL_COLUMNS
        
        # Create the index with Databricks-managed embeddings
        index = vs_client.create_delta_sync_index_and_wait(
            endpoint_name=VECTOR_SEARCH_ENDPOINT_NAME,
            source_table_name=VECTOR_SOURCE_TABLE,
            index_name=VECTOR_INDEX_NAME,
            pipeline_type=PIPELINE_TYPE,
            primary_key=PRIMARY_KEY_COLUMN,
            embedding_source_column=TEXT_COLUMN,
            embedding_model_endpoint_name=EMBEDDING_MODEL_ENDPOINT_NAME
        )
        
        print(f"✅ Vector index '{VECTOR_INDEX_NAME}' created successfully!")
        
        # Get index status (handle both dict and object return types)
        try:
            if hasattr(index, 'get'):
                # Dictionary-like response
                index_ready = index.get('status', {}).get('ready', False)
            else:
                # VectorSearchIndex object - get fresh status
                fresh_index = vs_client.get_index(VECTOR_INDEX_NAME)
                index_ready = fresh_index.get('status', {}).get('ready', False)
            print(f"📊 Index ready: {index_ready}")
        except Exception as status_error:
            print(f"📊 Index created (status check failed: {status_error})")

except Exception as e:
        print(f"❌ Error creating vector index: {str(e)}")
        print("💡 Common issues:")
        print("  - Endpoint not ready yet (wait a few minutes)")
        print("  - Change Data Feed not enabled on source table")
        print("  - Primary key type not supported (must be bigint, int, smallint, or string)")
        print("  - Insufficient permissions on source table")
        print("  - Invalid embedding model endpoint name")
        print("💡 To enable Change Data Feed manually:")
        print(f"   ALTER TABLE {SOURCE_TABLE_NAME} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
        print("💡 Primary key type conversion is handled automatically by this notebook")
        raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🧪 Test Vector Search

# COMMAND ----------

# Test the vector search functionality
print("🧪 Testing vector search functionality...")

try:
    # Get a sample review text for testing
    sample_df = spark.table(VECTOR_SOURCE_TABLE).select(TEXT_COLUMN).filter(
        f"{TEXT_COLUMN} IS NOT NULL AND {TEXT_COLUMN} != ''"
    ).limit(1)
    
    sample_text = sample_df.collect()[0][TEXT_COLUMN]
    print(f"📝 Using sample text for testing: '{sample_text[:100]}...'")
    
    # Get the index for querying
    index = vs_client.get_index(VECTOR_INDEX_NAME)
    
    # Perform similarity search
    print("🔍 Performing similarity search...")
    
    results = index.similarity_search(
        query_text=sample_text,
        columns=[PRIMARY_KEY_COLUMN, TEXT_COLUMN, "aspect_service", "aspect_food_and_beverage"],
        num_results=5
    )
    
    print(f"✅ Found {len(results.get('result', {}).get('data_array', []))} similar reviews")
    
    # Display results
    for i, result in enumerate(results.get('result', {}).get('data_array', [])[:3]):
        print(f"\n📊 Result {i+1}:")
        print(f"  ID: {result[0]}")
        print(f"  Text: {result[1][:100]}...")
        print(f"  Score: {result[-1]}")  # Similarity score is usually the last element
    
    print("\n✅ Vector search test completed successfully!")
    
except Exception as e:
    print(f"❌ Error testing vector search: {str(e)}")
    print("💡 The index might still be building. Try running this test again in a few minutes.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 Index Statistics and Monitoring

# COMMAND ----------

# Get index statistics and monitoring information
print("📊 Index Statistics and Information")

try:
    # Get index details
    index_info = vs_client.get_index(VECTOR_INDEX_NAME)
    
    print(f"📋 Index: {VECTOR_INDEX_NAME}")
    print(f"📊 Status: {index_info.get('status', {}).get('ready', 'Unknown')}")
    
    # Index specifications
    spec = index_info.get('spec', {})
    print(f"\n🔧 Configuration:")
    print(f"  Source table: {spec.get('source_table')}")
    print(f"  Original table: {SOURCE_TABLE_NAME}")
    print(f"  Primary key: {spec.get('primary_key')}")
    print(f"  Embedding source: {spec.get('embedding_source_column')}")
    print(f"  Embedding model: {spec.get('embedding_model_endpoint_name')}")
    print(f"  Pipeline type: {spec.get('pipeline_type')}")
    
    # Status information
    status = index_info.get('status', {})
    print(f"\n📈 Status Information:")
    print(f"  Ready: {status.get('ready', 'Unknown')}")
    print(f"  Message: {status.get('message', 'No message')}")
    
    # If there's sync information
    if 'last_sync_timestamp' in status:
        print(f"  Last sync: {status.get('last_sync_timestamp')}")
    
    print(f"\n✅ Index monitoring information retrieved successfully")
    
except Exception as e:
    print(f"❌ Error getting index statistics: {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔄 Index Management Functions

# COMMAND ----------

# Utility functions for index management
def sync_index():
    """Manually trigger index synchronization"""
    try:
        print(f"🔄 Triggering sync for index: {VECTOR_INDEX_NAME}")
        vs_client.sync_index(VECTOR_INDEX_NAME)
        print("✅ Index sync triggered successfully")
    except Exception as e:
        print(f"❌ Error syncing index: {str(e)}")

def delete_index():
    """Delete the vector index (use with caution!)"""
    response = input(f"⚠️  Are you sure you want to delete index '{VECTOR_INDEX_NAME}'? (yes/no): ")
    if response.lower() == 'yes':
        try:
            vs_client.delete_index(VECTOR_INDEX_NAME)
            print(f"✅ Index '{VECTOR_INDEX_NAME}' deleted successfully")
        except Exception as e:
            print(f"❌ Error deleting index: {str(e)}")
    else:
        print("❌ Index deletion cancelled")

def query_similar_reviews(query_text, num_results=10):
    """Query for similar reviews"""
    try:
        index = vs_client.get_index(VECTOR_INDEX_NAME)
        results = index.similarity_search(
            query_text=query_text,
            columns=[PRIMARY_KEY_COLUMN, TEXT_COLUMN, "aspect_service", "aspect_food_and_beverage"],
            num_results=num_results
        )
        return results
    except Exception as e:
        print(f"❌ Error querying similar reviews: {str(e)}")
        return None

print("🔧 Index management functions defined:")
print("  - sync_index(): Manually trigger index sync")
print("  - delete_index(): Delete the index (with confirmation)")
print("  - query_similar_reviews(text, num_results): Query for similar reviews")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🎯 Integration Code for FastAPI Backend

# COMMAND ----------

# MAGIC %md
# MAGIC ### Python code to add to your FastAPI backend:
# MAGIC 
# MAGIC ```python
# MAGIC # Add to databricks_client.py
# MAGIC 
# MAGIC from databricks.vector_search.client import VectorSearchClient
# MAGIC 
# MAGIC # Configuration
# MAGIC VECTOR_INDEX_NAME = "main.ashwinpo_bloomin.review_vector_index"
# MAGIC 
# MAGIC def get_similar_reviews(query_text: str, num_results: int = 10) -> List[Dict]:
# MAGIC     """
# MAGIC     Find semantically similar reviews using vector search
# MAGIC     
# MAGIC     Args:
# MAGIC         query_text: The text to find similar reviews for
# MAGIC         num_results: Number of similar reviews to return
# MAGIC         
# MAGIC     Returns:
# MAGIC         List of similar review records
# MAGIC     """
# MAGIC     try:
# MAGIC         vs_client = VectorSearchClient()
# MAGIC         index = vs_client.get_index(VECTOR_INDEX_NAME)
# MAGIC         
# MAGIC         results = index.similarity_search(
# MAGIC             query_text=query_text,
# MAGIC             columns=["Response_Id", "Question_Response", "aspect_service", 
# MAGIC                     "aspect_food_and_beverage", "aspect_pricing", "sentiment_analysis"],
# MAGIC             num_results=num_results
# MAGIC         )
# MAGIC         
# MAGIC         # Convert results to list of dictionaries
# MAGIC         similar_reviews = []
# MAGIC         for result in results.get('result', {}).get('data_array', []):
# MAGIC             similar_reviews.append({
# MAGIC                 'response_id': result[0],
# MAGIC                 'question_response': result[1],
# MAGIC                 'aspect_service': result[2],
# MAGIC                 'aspect_food_and_beverage': result[3],
# MAGIC                 'aspect_pricing': result[4],
# MAGIC                 'sentiment_analysis': result[5],
# MAGIC                 'similarity_score': result[-1]  # Last element is similarity score
# MAGIC             })
# MAGIC         
# MAGIC         logger.info(f"Found {len(similar_reviews)} similar reviews for query")
# MAGIC         return similar_reviews
# MAGIC         
# MAGIC     except Exception as e:
# MAGIC         logger.error(f"Error finding similar reviews: {str(e)}")
# MAGIC         return []
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Setup Complete!
# MAGIC 
# MAGIC ### What was created:
# MAGIC 1. **Vector Search Endpoint**: `bloomin_review_vector_endpoint`
# MAGIC 2. **Vector Index**: `main.ashwinpo_bloomin.review_vector_index`
# MAGIC 3. **Embeddings**: Generated from `Question_Response` column using Databricks managed model
# MAGIC 
# MAGIC ### Next steps:
# MAGIC 1. **Integrate with FastAPI**: Add the provided code to your `databricks_client.py`
# MAGIC 2. **Create API endpoint**: Add a new route to find similar reviews
# MAGIC 3. **Update frontend**: Modify the recommended tab to use semantic search
# MAGIC 4. **Monitor performance**: Use the management functions to sync and monitor the index
# MAGIC 
# MAGIC ### Usage in your app:
# MAGIC - When a user makes a correction, use the corrected review text to find similar reviews
# MAGIC - Display these similar reviews in the "recommended" tab
# MAGIC - Users can then review and correct similar comments efficiently
# MAGIC 
# MAGIC **The vector search index is now ready for production use! 🚀**

# COMMAND ----------

# Final summary
print("🎉 Vector Search Setup Complete!")
print(f"📊 Endpoint: {VECTOR_SEARCH_ENDPOINT_NAME}")
print(f"🧮 Index: {VECTOR_INDEX_NAME}")
print(f"📝 Source: {SOURCE_TABLE_NAME}")
print(f"🔤 Text Column: {TEXT_COLUMN}")
print(f"🔑 Primary Key: {PRIMARY_KEY_COLUMN}")
print("\n✅ Ready for integration with your FastAPI backend!")
