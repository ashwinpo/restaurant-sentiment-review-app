"""
Databricks connection and query utilities
Using service principal authentication for Databricks Apps deployment
Databricks automatically injects DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET
"""
import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv

from databricks import sql
from databricks.sdk.core import Config

# Vector search imports (optional - only needed if vector search is available)
try:
    from databricks.sdk import WorkspaceClient
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False
    logger.warning("Vector search client not available - similar review functionality will be disabled")

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Service Principal credentials - automatically injected by Databricks Apps
DATABRICKS_CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID")
DATABRICKS_CLIENT_SECRET = os.environ.get("DATABRICKS_CLIENT_SECRET")

# Warehouse configuration
DATABRICKS_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")

# Table configuration - easily configurable
BACKEND_DATA_TABLE = os.environ.get("BACKEND_DATA_TABLE", "main.ashwinpo_bloomin.guestexperience_guestsentimentscore")
EVALUATION_TABLE = os.environ.get("EVALUATION_TABLE", f"{BACKEND_DATA_TABLE}_evaluation")

# Vector search configuration
VECTOR_INDEX_NAME = os.environ.get("VECTOR_INDEX_NAME", "main.ashwinpo_bloomin.review_vector_index")
EMBEDDING_MODEL_ENDPOINT_NAME = os.environ.get("EMBEDDING_MODEL_ENDPOINT_NAME", "databricks-gte-large-en")

# Legacy environment variables for local development fallback
DB_HOST = os.environ.get("DB_HOST")
DB_PAT = os.environ.get("DB_PAT")

class DatabricksClient:
    """Databricks SQL connection client with service principal authentication"""
    
    def __init__(self):
        # Enhanced logging for deployment debugging
        logger.info("🔧 Initializing DatabricksClient...")
        
        # Debug: Log available environment variables and table configuration
        env_vars = {
            "DATABRICKS_CLIENT_ID": bool(DATABRICKS_CLIENT_ID),
            "DATABRICKS_CLIENT_SECRET": bool(DATABRICKS_CLIENT_SECRET),
            "DATABRICKS_WAREHOUSE_ID": bool(DATABRICKS_WAREHOUSE_ID),
            "DB_HOST": bool(DB_HOST),
            "DB_PAT": bool(DB_PAT),
        }
        logger.info(f"🔍 Environment variables available: {env_vars}")
        logger.info(f"📊 Backend data table: {BACKEND_DATA_TABLE}")
        logger.info(f"📝 Evaluation table: {EVALUATION_TABLE}")
        
        # Build warehouse HTTP path
        if DATABRICKS_WAREHOUSE_ID:
            self.http_path = f"/sql/1.0/warehouses/{DATABRICKS_WAREHOUSE_ID}"
        else:
            raise ValueError("DATABRICKS_WAREHOUSE_ID must be provided")
        
        # Initialize Databricks SDK Config - automatically handles service principal auth
        # when DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET are available
        self.databricks_cfg = Config()
        
        # For local development fallback, override with explicit values if provided
        if DB_HOST:
            self.databricks_cfg.host = DB_HOST
            logger.info(f"📍 Override host for local dev: {DB_HOST}")
        if DB_PAT:
            self.databricks_cfg.token = DB_PAT
            logger.info(f"🔑 Using provided PAT token for local dev: {DB_PAT[:8]}...")
        else:
            logger.info(f"🔑 Using token from .databrickscfg: {self.databricks_cfg.token[:8] if self.databricks_cfg.token else 'None'}...")
        
        logger.info("🔐 Using service principal authentication via SDK Config")
        logger.info(f"📍 SDK Host: {self.databricks_cfg.host}")
        logger.info(f"📍 HTTP Path: {self.http_path}")
    
    def create_evaluation_table_if_not_exists(self):
        """Create the evaluation table if it doesn't exist"""
        try:
            logger.info(f"🏗️ Checking if evaluation table exists: {EVALUATION_TABLE}")
            
            # Check if table exists
            check_query = f"DESCRIBE TABLE {EVALUATION_TABLE}"
            try:
                self.query(check_query)
                logger.info(f"✅ Evaluation table already exists: {EVALUATION_TABLE}")
                return True
            except Exception:
                logger.info(f"📝 Evaluation table doesn't exist, creating: {EVALUATION_TABLE}")
                
                # Create evaluation table optimized for the optimization pipeline inputs
                # Key fields: ResponseRelevancy, OverallSentiment, CategorySubcategory
                create_query = f"""
                CREATE TABLE {EVALUATION_TABLE} (
                    evaluation_hash_key STRING,
                    survey_response_id STRING,
                    question_label STRING,
                    question_response STRING,
                    
                    -- Core optimization pipeline inputs
                    response_relevancy STRING,  -- "useful", "profane but useful", "nonsense or irrelevant"
                    overall_sentiment_label STRING,  -- "Positive", "Negative", "Neutral"
                    overall_sentiment_score INT,
                    category_subcategory_list STRING,  -- Colon separated list of [category:subcategory]
                    
                    -- Human evaluation data (detailed breakdown)
                    human_eval_profane BOOLEAN,
                    human_eval_rewritten_comment STRING,
                    human_eval_irrelevant BOOLEAN,
                    human_eval_overall_sentiment_label STRING,
                    human_eval_overall_sentiment_score INT,
                    
                    -- Category sentiment details (JSON for flexibility)
                    human_eval_category_sentiments STRING,  -- JSON array of category sentiment objects
                    
                    -- Machine evaluation data (original predictions)
                    machine_eval_profane BOOLEAN,
                    machine_eval_rewritten_comment STRING,
                    machine_eval_irrelevant BOOLEAN,
                    machine_eval_overall_sentiment_label STRING,
                    machine_eval_overall_sentiment_score INT,
                    machine_eval_category_sentiments STRING,  -- JSON array of original category sentiment objects
                    
                    -- Legacy aspect scores for backward compatibility
                    human_eval_pricing FLOAT,
                    human_eval_other FLOAT,
                    human_eval_food_experience FLOAT,
                    human_eval_wait_time FLOAT,
                    human_eval_service FLOAT,
                    human_eval_cleanliness FLOAT,
                    human_eval_ambiance FLOAT,
                    
                    -- Metadata
                    store_key STRING,
                    visit_datetime TIMESTAMP,
                    evaluation_model STRING,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                ) USING DELTA
                """
                
                self.query(create_query)
                logger.info(f"✅ Successfully created evaluation table: {EVALUATION_TABLE}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create evaluation table: {str(e)}")
            raise Exception(f"Failed to create evaluation table {EVALUATION_TABLE}: {str(e)}")

    def create_recommendations_table_if_not_exists(self):
        """Create the recommendations tracking table if it doesn't exist"""
        recommendations_table = f"{EVALUATION_TABLE}_recommendations"
        try:
            logger.info(f"🏗️ Checking if recommendations table exists: {recommendations_table}")
            
            # Check if table exists
            check_query = f"DESCRIBE TABLE {recommendations_table}"
            try:
                self.query(check_query)
                logger.info(f"✅ Recommendations table already exists: {recommendations_table}")
                return True
            except Exception:
                logger.info(f"📝 Recommendations table doesn't exist, creating: {recommendations_table}")
                
                create_query = f"""
                CREATE TABLE {recommendations_table} (
                    source_review_id STRING,
                    recommended_review_id STRING,
                    similarity_score FLOAT,
                    recommendation_timestamp TIMESTAMP,
                    source_review_text STRING,
                    is_active BOOLEAN
                ) USING DELTA
                """
                
                self.query(create_query)
                logger.info(f"✅ Successfully created recommendations table: {recommendations_table}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create recommendations table: {str(e)}")
            raise Exception(f"Failed to create recommendations table {recommendations_table}: {str(e)}")
    
    def get_connection(self):
        """Get a Databricks SQL connection using service principal authentication via SDK Config"""
        try:
            logger.info(f"🔌 Connecting with SDK Config: {self.databricks_cfg.host}")
            logger.info(f"📍 HTTP Path: {self.http_path}")
            
            return sql.connect(
                server_hostname=self.databricks_cfg.host,
                http_path=self.http_path,
                credentials_provider=lambda: self.databricks_cfg.authenticate,
            )
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Databricks: {str(e)}")
            logger.error(f"🔍 SDK Host: {self.databricks_cfg.host}")
            logger.error(f"🔍 HTTP Path: {self.http_path}")
            logger.error(f"🔍 Service Principal ID: {DATABRICKS_CLIENT_ID[:8]}..." if DATABRICKS_CLIENT_ID else "None")
            raise Exception(f"Databricks connection failed: {str(e)}")
    
    def query(self, sql_query: str, as_dict: bool = True) -> List[Dict]:
        """
        Execute a SQL query and return results
        
        Args:
            sql_query: SQL query to execute
            as_dict: Return results as list of dictionaries (default: True)
            
        Returns:
            List of dictionaries containing query results
        """
        logger.info(f"📊 Executing SQL query...")
        logger.info(f"🔍 Query preview: {sql_query[:100]}{'...' if len(sql_query) > 100 else ''}")
        
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchall()
                
                logger.info(f"✅ Query executed successfully, returned {len(result)} rows")
                
                if as_dict:
                    columns = [col[0] for col in cursor.description]
                    logger.info(f"📋 Columns: {', '.join(columns)}")
                    return [dict(zip(columns, row)) for row in result]
                else:
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Query execution failed: {str(e)}")
            logger.error(f"🔍 Failed query: {sql_query}")
            logger.error(f"🔍 Auth method: Service Principal via SDK Config")
            raise Exception(f"DBSQL Query Failed: {str(e)}")
        finally:
            conn.close()

# Global client instance
_client: Optional[DatabricksClient] = None

def get_databricks_client() -> DatabricksClient:
    """Get or create the global Databricks client instance"""
    global _client
    if _client is None:
        _client = DatabricksClient()
    return _client

def query_reviews_table(
    limit: int = 10,
    offset: int = 0,
    status_filter: Optional[str] = None,
    exclude_validated: bool = False
) -> List[Dict]:
    """
    Query the flattened sentiment analysis reviews table
    Groups multiple category/subcategory rows per survey response
    
    Args:
        limit: Number of unique survey responses to return
        offset: Number of survey responses to skip
        status_filter: Optional status filter (for future use)
        exclude_validated: If True, exclude reviews that have already been validated
        
    Returns:
        List of aggregated review records as dictionaries
    """
    client = get_databricks_client()
    
    # Build exclusion clause for validated reviews
    exclusion_clause = ""
    if exclude_validated:
        exclusion_clause = f"""
        AND SurveyResponseId NOT IN (
            SELECT DISTINCT survey_response_id 
            FROM {EVALUATION_TABLE}
        )
        """
    
    # Query to get unique survey responses and aggregate their category sentiments
    # Note: No filter on ResponseRelevancy - we want to include ALL reviews (useful, profane, irrelevant)
    # so human evaluators can validate and correct the relevancy classification
    sql_query = f"""
    WITH unique_surveys AS (
        SELECT DISTINCT SurveyResponseId
        FROM {BACKEND_DATA_TABLE}
        WHERE 1=1
        {exclusion_clause}
        ORDER BY RAND()  -- Random sampling instead of ordered
        LIMIT {limit} OFFSET {offset}
    ),
    survey_details AS (
        SELECT 
            t.SurveyResponseId as response_id,
            t.QuestionLabel as question_label,
            t.QuestionResponse as question_response,
            t.ResponseRelevancy as response_relevancy,
            t.IsProfanityRewrittenFlag as profane,
            t.RewrittenQuestionResponse as rewritten_comment,
            t.OverallSentimentLabel as overall_sentiment_label,
            t.OverallSentimentScore as overall_sentiment_score,
            t.CommentCategory as comment_category,
            t.CategorySentimentLabel as category_sentiment_label,
            t.CategorySentimentScore as category_sentiment_score,
            t.CommentSubcategory as comment_subcategory,
            t.SubCategorySentimentLabel as subcategory_sentiment_label,
            t.SubCategorySentimentScore as subcategory_sentiment_score,
            t.StoreKey as store_key,
            t.VisitDateTime as visit_datetime
        FROM {BACKEND_DATA_TABLE} t
        INNER JOIN unique_surveys u ON t.SurveyResponseId = u.SurveyResponseId
    )
    SELECT *
    FROM survey_details
    ORDER BY response_id, comment_category, comment_subcategory
    """
    
    try:
        results = client.query(sql_query)
        logger.info(f"Retrieved {len(results)} reviews from {BACKEND_DATA_TABLE} (exclude_validated: {exclude_validated})")
        return results
    except Exception as e:
        logger.error(f"Failed to query reviews table {BACKEND_DATA_TABLE}: {str(e)}")
        raise

def write_human_evaluation_optimized(
    survey_response_id: str,
    human_eval_data: Dict,
    machine_eval_data: Optional[Dict] = None,
    evaluation_model: str = "human_validation_v3_optimized"
) -> bool:
    """
    Write human evaluation data optimized for the optimization pipeline
    Single row per survey response with all optimization pipeline inputs
    
    Args:
        survey_response_id: The survey response ID
        human_eval_data: Dictionary containing human evaluation data
        machine_eval_data: Optional dictionary containing original machine evaluation data
        evaluation_model: Model version identifier
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"💾 Writing human evaluation for {survey_response_id}")
    logger.info(f"📝 Human eval data keys: {list(human_eval_data.keys())}")
    logger.info(f"🔧 Evaluation model: {evaluation_model}")
    
    client = get_databricks_client()
    
    # Ensure evaluation table exists
    client.create_evaluation_table_if_not_exists()
    
    # Ensure recommendations table exists
    client.create_recommendations_table_if_not_exists()
    
    # Generate unique hash key for this evaluation entry
    import hashlib
    import json
    evaluation_hash_key = hashlib.sha256(f"{survey_response_id}_{evaluation_model}".encode()).hexdigest()
    
    # Determine ResponseRelevancy based on human evaluation
    response_relevancy = "useful"  # default
    if human_eval_data.get('irrelevant', False):
        response_relevancy = "nonsense or irrelevant"
    elif human_eval_data.get('profane', False):
        response_relevancy = "profane but useful"
    
    # Get category sentiments and create category:subcategory list
    category_sentiments = human_eval_data.get('category_sentiments', [])
    category_subcategory_pairs = []
    
    if category_sentiments:
        for cs in category_sentiments:
            # Handle both dict and CategorySentiment object formats
            if hasattr(cs, 'category'):  # Pydantic model
                category = cs.category
                subcategory = cs.subcategory
            else:  # Dictionary
                category = cs.get('category', '')
                subcategory = cs.get('subcategory', '')
            
            if category and subcategory:
                category_subcategory_pairs.append(f"{category}:{subcategory}")
    
    category_subcategory_list = ", ".join(category_subcategory_pairs) if category_subcategory_pairs else ""
    
    # Convert category sentiments to JSON for storage
    def serialize_category_sentiments(sentiments):
        if not sentiments:
            return "[]"
        serializable_sentiments = []
        for cs in sentiments:
            if hasattr(cs, 'dict'):  # Pydantic model
                serializable_sentiments.append(cs.dict())
            elif isinstance(cs, dict):
                serializable_sentiments.append(cs)
            else:
                # Try to convert to dict manually
                serializable_sentiments.append({
                    'category': getattr(cs, 'category', ''),
                    'category_sentiment_label': getattr(cs, 'category_sentiment_label', ''),
                    'category_sentiment_score': getattr(cs, 'category_sentiment_score', 0.0),
                    'subcategory': getattr(cs, 'subcategory', ''),
                    'subcategory_sentiment_label': getattr(cs, 'subcategory_sentiment_label', ''),
                    'subcategory_sentiment_score': getattr(cs, 'subcategory_sentiment_score', 0.0)
                })
        return json.dumps(serializable_sentiments)
    
    human_category_sentiments_json = serialize_category_sentiments(category_sentiments)
    machine_category_sentiments_json = serialize_category_sentiments(machine_eval_data.get('category_sentiments', [])) if machine_eval_data else "[]"
    
    # Use MERGE (upsert) to handle concurrent evaluations of the same review
    upsert_query = f"""
    MERGE INTO {EVALUATION_TABLE} AS target
    USING (
        SELECT 
            '{evaluation_hash_key}' as evaluation_hash_key,
            '{survey_response_id}' as survey_response_id,
            {_format_sql_value(human_eval_data.get('question_label', 'COMMENT'))} as question_label,
            {_format_sql_value(human_eval_data.get('question_response'))} as question_response,
            {_format_sql_value(response_relevancy)} as response_relevancy,
            {_format_sql_value(human_eval_data.get('overall_sentiment_label'))} as overall_sentiment_label,
            {_format_sql_value(int(human_eval_data.get('overall_sentiment_score', 0)) if human_eval_data.get('overall_sentiment_score') is not None else None)} as overall_sentiment_score,
            {_format_sql_value(category_subcategory_list)} as category_subcategory_list,
            {_format_sql_value(human_eval_data.get('profane', False))} as human_eval_profane,
            {_format_sql_value(human_eval_data.get('rewritten_comment'))} as human_eval_rewritten_comment,
            {_format_sql_value(human_eval_data.get('irrelevant', False))} as human_eval_irrelevant,
            {_format_sql_value(human_eval_data.get('overall_sentiment_label'))} as human_eval_overall_sentiment_label,
            {_format_sql_value(int(human_eval_data.get('overall_sentiment_score', 0)) if human_eval_data.get('overall_sentiment_score') is not None else None)} as human_eval_overall_sentiment_score,
            {_format_sql_value(human_category_sentiments_json)} as human_eval_category_sentiments,
            {_format_sql_value(machine_eval_data.get('profane', False) if machine_eval_data else False)} as machine_eval_profane,
            {_format_sql_value(machine_eval_data.get('rewritten_comment') if machine_eval_data else None)} as machine_eval_rewritten_comment,
            {_format_sql_value(machine_eval_data.get('irrelevant', False) if machine_eval_data else False)} as machine_eval_irrelevant,
            {_format_sql_value(machine_eval_data.get('overall_sentiment_label') if machine_eval_data else None)} as machine_eval_overall_sentiment_label,
            {_format_sql_value(int(machine_eval_data.get('overall_sentiment_score', 0)) if machine_eval_data and machine_eval_data.get('overall_sentiment_score') is not None else None)} as machine_eval_overall_sentiment_score,
            {_format_sql_value(machine_category_sentiments_json)} as machine_eval_category_sentiments,
            NULL as human_eval_pricing,
            NULL as human_eval_other,
            NULL as human_eval_food_experience,
            NULL as human_eval_wait_time,
            NULL as human_eval_service,
            NULL as human_eval_cleanliness,
            NULL as human_eval_ambiance,
            {_format_sql_value(human_eval_data.get('store_id'))} as store_key,
            {_format_sql_value(human_eval_data.get('visit_datetime'))} as visit_datetime,
            '{evaluation_model}' as evaluation_model
    ) AS source
    ON target.survey_response_id = source.survey_response_id
    WHEN MATCHED THEN
        UPDATE SET
            response_relevancy = source.response_relevancy,
            overall_sentiment_label = source.overall_sentiment_label,
            overall_sentiment_score = source.overall_sentiment_score,
            category_subcategory_list = source.category_subcategory_list,
            human_eval_profane = source.human_eval_profane,
            human_eval_rewritten_comment = source.human_eval_rewritten_comment,
            human_eval_irrelevant = source.human_eval_irrelevant,
            human_eval_overall_sentiment_label = source.human_eval_overall_sentiment_label,
            human_eval_overall_sentiment_score = source.human_eval_overall_sentiment_score,
            human_eval_category_sentiments = source.human_eval_category_sentiments,
            human_eval_pricing = source.human_eval_pricing,
            human_eval_other = source.human_eval_other,
            human_eval_food_experience = source.human_eval_food_experience,
            human_eval_wait_time = source.human_eval_wait_time,
            human_eval_service = source.human_eval_service,
            human_eval_cleanliness = source.human_eval_cleanliness,
            human_eval_ambiance = source.human_eval_ambiance,
            evaluation_model = source.evaluation_model,
            updated_at = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
        INSERT (
            evaluation_hash_key, survey_response_id, question_label, question_response,
            response_relevancy, overall_sentiment_label, overall_sentiment_score, category_subcategory_list,
            human_eval_profane, human_eval_rewritten_comment, human_eval_irrelevant,
            human_eval_overall_sentiment_label, human_eval_overall_sentiment_score, human_eval_category_sentiments,
            machine_eval_profane, machine_eval_rewritten_comment, machine_eval_irrelevant,
            machine_eval_overall_sentiment_label, machine_eval_overall_sentiment_score, machine_eval_category_sentiments,
            human_eval_pricing, human_eval_other, human_eval_food_experience, human_eval_wait_time,
            human_eval_service, human_eval_cleanliness, human_eval_ambiance,
            store_key, visit_datetime, evaluation_model, created_at, updated_at
        )
        VALUES (
            source.evaluation_hash_key, source.survey_response_id, source.question_label, source.question_response,
            source.response_relevancy, source.overall_sentiment_label, source.overall_sentiment_score, source.category_subcategory_list,
            source.human_eval_profane, source.human_eval_rewritten_comment, source.human_eval_irrelevant,
            source.human_eval_overall_sentiment_label, source.human_eval_overall_sentiment_score, source.human_eval_category_sentiments,
            source.machine_eval_profane, source.machine_eval_rewritten_comment, source.machine_eval_irrelevant,
            source.machine_eval_overall_sentiment_label, source.machine_eval_overall_sentiment_score, source.machine_eval_category_sentiments,
            source.human_eval_pricing, source.human_eval_other, source.human_eval_food_experience, source.human_eval_wait_time,
            source.human_eval_service, source.human_eval_cleanliness, source.human_eval_ambiance,
            source.store_key, source.visit_datetime, source.evaluation_model, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
        )
    """
    
    try:
        logger.info(f"📤 Executing UPSERT query for survey response {survey_response_id}")
        logger.info(f"🎯 ResponseRelevancy: {response_relevancy}")
        logger.info(f"🎯 OverallSentiment: {human_eval_data.get('overall_sentiment_label')}")
        logger.info(f"🎯 CategorySubcategory: {category_subcategory_list}")
        
        client.query(upsert_query)
        logger.info(f"✅ Successfully upserted evaluation entry for response_id: {survey_response_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to upsert evaluation entry: {str(e)}")
        logger.error(f"🔍 SQL query that failed: {upsert_query}")
        logger.error(f"🔍 Target table: {EVALUATION_TABLE}")
        return False

# Legacy wrapper function for backward compatibility
def write_human_evaluation_flattened(
    survey_response_id: str,
    human_eval_data: Dict,
    machine_eval_data: Optional[Dict] = None,
    evaluation_model: str = "human_validation_v2_flattened"
) -> bool:
    """Legacy wrapper - redirects to optimized version"""
    return write_human_evaluation_optimized(
        survey_response_id=survey_response_id,
        human_eval_data=human_eval_data,
        machine_eval_data=machine_eval_data,
        evaluation_model=evaluation_model
    )

# Legacy wrapper function for backward compatibility
def write_human_evaluation(
    response_id: str,
    human_eval_data: Dict,
    machine_eval_data: Optional[Dict] = None,
    evaluation_model: str = "human_validation_v1_legacy"
) -> bool:
    """
    Legacy wrapper for write_human_evaluation_optimized
    Converts old format to new optimized format
    """
    return write_human_evaluation_optimized(
        survey_response_id=response_id,
        human_eval_data=human_eval_data,
        machine_eval_data=machine_eval_data,
        evaluation_model=evaluation_model
    )

def _format_sql_value(value) -> str:
    """Format a Python value for SQL insertion"""
    if value is None:
        return "NULL"
    elif isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    elif isinstance(value, str):
        # Escape single quotes in strings
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    elif isinstance(value, (int, float)):
        return str(value)
    else:
        return "NULL"

def query_completed_reviews(
    limit: int = 10,
    offset: int = 0
) -> List[Dict]:
    """
    Query completed reviews from the evaluation table
    
    Args:
        limit: Number of records to return
        offset: Number of records to skip
        
    Returns:
        List of completed review records as dictionaries
    """
    client = get_databricks_client()
    
    # Query the evaluation table to get completed reviews (optimized format)
    sql_query = f"""
    SELECT 
        survey_response_id as response_id,
        question_label,
        question_response,
        response_relevancy,
        overall_sentiment_label,
        overall_sentiment_score,
        category_subcategory_list,
        human_eval_profane as profane,
        human_eval_rewritten_comment as rewritten_comment,
        human_eval_irrelevant as irrelevant,
        human_eval_overall_sentiment_label,
        human_eval_overall_sentiment_score,
        human_eval_category_sentiments,
        human_eval_pricing as Pricing,
        human_eval_other as Other,
        human_eval_food_experience as Food_Experience,
        human_eval_wait_time as Wait_Time,
        human_eval_service as Service,
        human_eval_cleanliness as Cleanliness,
        human_eval_ambiance as Ambiance,
        store_key,
        visit_datetime,
        evaluation_model,
        created_at
    FROM {EVALUATION_TABLE}
    ORDER BY created_at DESC
    LIMIT {limit} OFFSET {offset}
    """
    
    try:
        results = client.query(sql_query)
        logger.info(f"Retrieved {len(results)} completed reviews from {EVALUATION_TABLE}")
        return results
    except Exception as e:
        logger.error(f"Failed to query completed reviews from {EVALUATION_TABLE}: {str(e)}")
        raise

def get_metrics_data() -> Dict:
    """
    Get real metrics data from Databricks tables
    
    Returns:
        Dictionary containing metrics data
    """
    client = get_databricks_client()
    
    try:
        # Count total unique survey responses in source table 
        source_count_query = f"SELECT COUNT(DISTINCT SurveyResponseId) as total_count FROM {BACKEND_DATA_TABLE}"
        source_result = client.query(source_count_query)
        total_reviews = source_result[0]['total_count'] if source_result else 0
        
        # Random sample is limited to 20 reviews for evaluation
        total_random_sample = min(20, total_reviews)
        
        # Count completed evaluations
        completed_total = 0
        try:
            eval_count_query = f"SELECT COUNT(DISTINCT survey_response_id) as eval_count FROM {EVALUATION_TABLE}"
            eval_result = client.query(eval_count_query)
            completed_total = eval_result[0]['eval_count'] if eval_result else 0
        except Exception as e:
            logger.info(f"Evaluation table not accessible (expected if not created yet): {str(e)}")
            completed_total = 0
        
        # Calculate accuracy by comparing original vs human evaluations (if evaluation table exists)
        average_accuracy = 0.0
        corrections_per_review = 0.0
        
        if completed_total > 0:
            try:
                accuracy_query = f"""
                SELECT 
                    src.SurveyResponseId,
                    src.OverallSentimentScore as orig_overall_score,
                    eval.human_eval_overall_sentiment_score as human_overall_score
                FROM {BACKEND_DATA_TABLE} src
                INNER JOIN {EVALUATION_TABLE} eval
                ON src.SurveyResponseId = eval.survey_response_id
                """
                
                accuracy_results = client.query(accuracy_query)
                
                if accuracy_results:
                    # Calculate accuracy based on how close human scores are to original scores
                    total_comparisons = len(accuracy_results)
                    accurate_predictions = 0
                    total_corrections = 0
                    
                    for row in accuracy_results:
                        orig_overall = int(row.get('orig_overall_score', 0) or 0)
                        human_overall = int(row.get('human_overall_score', 0) or 0)
                        
                        # Consider prediction accurate if within 1 point (since we're using integers now)
                        if abs(orig_overall - human_overall) <= 1:
                            accurate_predictions += 1
                        
                        # Count corrections (any changes)
                        if orig_overall != human_overall:
                            total_corrections += 1
                    
                    average_accuracy = accurate_predictions / total_comparisons if total_comparisons > 0 else 0.0
                    corrections_per_review = total_corrections / completed_total if completed_total > 0 else 0.0
                    
            except Exception as e:
                logger.warning(f"Could not calculate accuracy metrics: {str(e)}")
                average_accuracy = 0.0
                corrections_per_review = 0.0
        
        # Count recommended reviews (flagged for review) - using extreme sentiment logic for new schema
        recommended_query = f"""
        SELECT COUNT(DISTINCT SurveyResponseId) as recommended_count 
        FROM {BACKEND_DATA_TABLE} 
        WHERE (CategorySentimentScore < -0.5 OR CategorySentimentScore > 0.5)
           OR (SubCategorySentimentScore < -0.5 OR SubCategorySentimentScore > 0.5)
        """
        
        try:
            recommended_result = client.query(recommended_query)
            recommended_count = recommended_result[0]['recommended_count'] if recommended_result else 0
        except Exception as e:
            logger.warning(f"Could not calculate recommended reviews: {str(e)}")
            recommended_count = 0
        
        return {
            "total_random_sample": total_random_sample,  # Limited to 20 for evaluation
            "completed_today": completed_total,
            "recommended_reviews": recommended_count,
            "total_reviews": total_reviews,  # Total count in database
            "average_accuracy": round(average_accuracy, 2),
            "corrections_per_review": round(corrections_per_review, 1)
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics data: {str(e)}")
        # Return default values on error
        return {
            "total_random_sample": 0,
            "completed_today": 0,
            "recommended_reviews": 0,
            "total_reviews": 0,
            "average_accuracy": 0.0,
            "corrections_per_review": 0.0
        }

def get_embeddings(text: str) -> Optional[List[float]]:
    """
    Generate embeddings for text using Databricks serving endpoint
    
    Args:
        text: Text to generate embeddings for
        
    Returns:
        List of embedding floats or None if failed
    """
    if not VECTOR_SEARCH_AVAILABLE:
        return None
    
    try:
        w = WorkspaceClient()
        openai_client = w.serving_endpoints.get_open_ai_client()
        
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL_ENDPOINT_NAME, input=text
        )
        return response.data[0].embedding
        
    except Exception as e:
        logger.error(f"❌ Error generating embeddings: {str(e)}")
        return None


def get_similar_reviews(query_text: str, num_results: int = 10, exclude_response_id: Optional[str] = None) -> List[Dict]:
    """
    Find semantically similar reviews using vector search (simplified cookbook implementation)
    
    Args:
        query_text: The text to find similar reviews for
        num_results: Number of similar reviews to return
        exclude_response_id: Optional response ID to exclude from results
        
    Returns:
        List of similar review records with similarity scores
    """
    if not VECTOR_SEARCH_AVAILABLE:
        logger.warning("Vector search not available - returning empty results")
        return []
    
    try:
        logger.info(f"🔍 Searching for reviews similar to: '{query_text[:100]}...'")
        
        # Generate embeddings for the query text using the simple method
        query_vector = get_embeddings(query_text)
        if query_vector is None:
            logger.error("Failed to generate embeddings for query text")
            return []
        
        # Use WorkspaceClient for vector search
        w = WorkspaceClient()
        
        # Define columns to fetch
        columns_to_fetch = [
            "Response_Id", 
            "Question_Response", 
            "Question_Label",
            "aspect_service", 
            "aspect_food_and_beverage", 
            "aspect_pricing",
            "aspect_ambiance",
            "aspect_cleanliness", 
            "aspect_wait_time",
            "aspect_other",
            "sentiment_analysis"
        ]
        
        # Perform vector search using the simple cookbook approach
        try:
            query_result = w.vector_search_indexes.query_index(
                index_name=VECTOR_INDEX_NAME,
                columns=columns_to_fetch,
                query_vector=query_vector,
                num_results=num_results + (5 if exclude_response_id else 0),  # Get extra in case we need to exclude
            )
        except Exception as vs_error:
            logger.error(f"❌ Vector search query failed: {str(vs_error)}")
            return []
        
        # Process results into our expected format
        similar_reviews = []
        data_array = query_result.result.data_array
        
        for result in data_array:
            response_id = str(result[0])
            
            # Skip the original review if we're excluding it
            if exclude_response_id and response_id == exclude_response_id:
                continue
                
            # Stop when we have enough results
            if len(similar_reviews) >= num_results:
                break
            
            similar_reviews.append({
                'response_id': response_id,
                'question_response': result[1] if len(result) > 1 else '',
                'question_label': result[2] if len(result) > 2 else 'COMMENT',
                'aspect_service': result[3] if len(result) > 3 and result[3] != 'null' else None,
                'aspect_food_and_beverage': result[4] if len(result) > 4 and result[4] != 'null' else None,
                'aspect_pricing': result[5] if len(result) > 5 and result[5] != 'null' else None,
                'aspect_ambiance': result[6] if len(result) > 6 and result[6] != 'null' else None,
                'aspect_cleanliness': result[7] if len(result) > 7 and result[7] != 'null' else None,
                'aspect_wait_time': result[8] if len(result) > 8 and result[8] != 'null' else None,
                'aspect_other': result[9] if len(result) > 9 and result[9] != 'null' else None,
                'sentiment_analysis': result[10] if len(result) > 10 else None,
                'similarity_score': 1.0  # Databricks vector search returns results in similarity order
            })
        
        logger.info(f"✅ Found {len(similar_reviews)} similar reviews")
        return similar_reviews
        
    except Exception as e:
        logger.error(f"❌ Error finding similar reviews: {str(e)}")
        logger.error(f"🔍 Vector index: {VECTOR_INDEX_NAME}")
        logger.error(f"🔍 Query text: {query_text[:100]}...")
        return []


def store_recommendations(source_review_id: str, source_review_text: str, similar_reviews: List[Dict]):
    """
    Store recommendations in the database for tracking and persistence
    
    Args:
        source_review_id: The review ID that generated these recommendations
        source_review_text: The text of the source review
        similar_reviews: List of similar reviews found
    """
    if not similar_reviews:
        return
    
    try:
        client = get_databricks_client()
        recommendations_table = f"{EVALUATION_TABLE}_recommendations"
        
        # First, deactivate any existing recommendations for this source review
        deactivate_query = f"""
        UPDATE {recommendations_table} 
        SET is_active = false 
        WHERE source_review_id = '{source_review_id}'
        """
        client.query(deactivate_query)
        
        # Insert new recommendations
        for review in similar_reviews:
            insert_query = f"""
            INSERT INTO {recommendations_table} (
                source_review_id,
                recommended_review_id,
                similarity_score,
                recommendation_timestamp,
                source_review_text,
                is_active
            ) VALUES (
                '{source_review_id}',
                '{review.get("response_id")}',
                {review.get("similarity_score", 0.0)},
                current_timestamp(),
                '{source_review_text.replace("'", "''")}',
                true
            )
            """
            client.query(insert_query)
        
        logger.info(f"✅ Stored {len(similar_reviews)} recommendations for review {source_review_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to store recommendations: {str(e)}")


def get_all_recommendations() -> List[Dict]:
    """
    Get all active recommendations grouped by source review
    
    Returns:
        List of recommendation groups with source review info
    """
    try:
        client = get_databricks_client()
        recommendations_table = f"{EVALUATION_TABLE}_recommendations"
        
        # Get all active recommendations with source review details
        query = f"""
        SELECT 
            r.source_review_id,
            r.source_review_text,
            MAX(r.recommendation_timestamp) as recommendation_timestamp,
            COUNT(*) as recommendation_count
        FROM {recommendations_table} r
        WHERE r.is_active = true
        GROUP BY r.source_review_id, r.source_review_text
        ORDER BY MAX(r.recommendation_timestamp) DESC
        """
        
        result = client.query(query)
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to get recommendations: {str(e)}")
        return []


def get_recommendations_for_source(source_review_id: str) -> List[Dict]:
    """
    Get all recommended reviews for a specific source review
    
    Args:
        source_review_id: The review ID that generated the recommendations
        
    Returns:
        List of recommended reviews with full details
    """
    try:
        client = get_databricks_client()
        recommendations_table = f"{EVALUATION_TABLE}_recommendations"
        
        # Get recommended review IDs for this source
        rec_query = f"""
        SELECT recommended_review_id, similarity_score
        FROM {recommendations_table}
        WHERE source_review_id = '{source_review_id}' AND is_active = true
        ORDER BY similarity_score DESC
        """
        
        recommendations = client.query(rec_query)
        if not recommendations:
            return []
        
        # Get full review details for each recommendation
        review_ids = [rec['recommended_review_id'] for rec in recommendations]
        ids_str = "', '".join(review_ids)
        
        # Check which IDs actually exist in the source table
        existing_ids = []
        for review_id in review_ids:
            check_query = f"SELECT COUNT(*) as count FROM {BACKEND_DATA_TABLE} WHERE SurveyResponseId = '{review_id}'"
            result = client.query(check_query)
            if result and result[0]['count'] > 0:
                existing_ids.append(review_id)
        
        # If none exist, return empty (no fallback)
        if not existing_ids:
            logger.warning(f"None of the recommended review IDs exist in the source table. Returning empty results.")
            return []
        
        ids_str = "', '".join(existing_ids)
        reviews_query = f"""
        SELECT 
            CAST(SurveyResponseId AS STRING) as response_id,
            QuestionLabel as question_label,
            QuestionResponse as question_response,
            NULL as Pricing,
            NULL as Other,
            NULL as Food_Experience,
            NULL as Wait_Time,
            NULL as Service,
            NULL as Cleanliness,
            NULL as Ambiance,
            CASE WHEN ResponseRelevancy = 'useful' THEN false ELSE true END as irrelevant,
            IsProfanityRewrittenFlag as profane,
            COALESCE(RewrittenQuestionResponse, '') as rewritten_comment,
            true as Flagged_For_Review
        FROM {BACKEND_DATA_TABLE}
        WHERE SurveyResponseId IN ('{ids_str}')
        """
        
        reviews = client.query(reviews_query)
        
        # Add similarity scores and convert to ReviewSummary objects
        result_reviews = []
        for review in reviews:
            # Find the similarity score for this review
            similarity_score = 0.0
            for rec in recommendations:
                if rec['recommended_review_id'] == review['response_id']:
                    similarity_score = rec['similarity_score']
                    break
            
            # Convert to ReviewSummary - import here to avoid circular imports
            from models import ReviewSummary, ReviewStatus, SentimentAnalysis
            
            # Create ReviewSummary object with correct field names
            sentiment_analysis = SentimentAnalysis(
                irrelevant=review.get('irrelevant', False),
                aspects={
                    'pricing': review.get('Pricing'),
                    'other': review.get('Other'),
                    'food_experience': review.get('Food_Experience'),
                    'wait_time': review.get('Wait_Time'),
                    'service': review.get('Service'),
                    'cleanliness': review.get('Cleanliness'),
                    'ambiance': review.get('Ambiance')
                }
            )
            
            review_obj = ReviewSummary(
                response_id=review['response_id'],
                question_label=review.get('question_label', 'COMMENT'),
                question_response=review['question_response'],
                relevant_comments=review['question_response'],  # Use same text
                profanity_check=review.get('Flagged_For_Review', True),
                profane=review.get('profane', False),
                rewritten_comment=review.get('rewritten_comment', ''),
                sentiment_analysis=sentiment_analysis,
                status=ReviewStatus.RECOMMENDED
            )
            
            # Add similarity score as metadata
            review_dict = review_obj.dict()
            review_dict['similarity_score'] = similarity_score
            result_reviews.append(review_dict)
        
        # Sort by similarity score descending
        result_reviews.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        return result_reviews
        
    except Exception as e:
        logger.error(f"❌ Failed to get recommendations for source {source_review_id}: {str(e)}")
        return []

def test_connection() -> Dict:
    """Test the Databricks connection and return basic info"""
    try:
        client = get_databricks_client()
        
        # Simple test query
        test_query = "SELECT 1 as test_value"
        result = client.query(test_query)
        
        # Get table info
        table_info_query = f"DESCRIBE TABLE {BACKEND_DATA_TABLE}"
        table_schema = client.query(table_info_query)
        
        # Test vector search if available
        vector_search_status = "not_available"
        if VECTOR_SEARCH_AVAILABLE:
            try:
                # Test embeddings endpoint
                test_embedding = get_embeddings("test connection")
                if test_embedding:
                    vector_search_status = "available"
                    vector_index_ready = True
                else:
                    vector_search_status = "embeddings_failed"
                    vector_index_ready = False
            except Exception as ve:
                vector_search_status = f"error: {str(ve)}"
                vector_index_ready = False
        else:
            vector_index_ready = False
        
        return {
            "connection_status": "success",
            "test_query_result": result,
            "table_schema": table_schema,
            "warehouse_id": DATABRICKS_WAREHOUSE_ID,
            "vector_search_status": vector_search_status,
            "vector_index_ready": vector_index_ready,
            "vector_index_name": VECTOR_INDEX_NAME,
            "embedding_model": EMBEDDING_MODEL_ENDPOINT_NAME
        }
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return {
            "connection_status": "failed",
            "error": str(e)
        }
