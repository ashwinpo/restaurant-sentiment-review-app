from fastapi import APIRouter, Query, HTTPException, Path
from typing import List, Optional
import json
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from models import ReviewSummary, ReviewDetail, ValidationRequest, SentimentAnalysis, ReviewStatus, CategorySentiment
from mock_data import get_mock_reviews, get_mock_review_by_id
from databricks_client import query_reviews_table, test_connection, get_similar_reviews, store_recommendations, get_all_recommendations, get_recommendations_for_source

logger = logging.getLogger(__name__)

router = APIRouter()

# Test endpoints - must be defined before parameterized routes to avoid conflicts
@router.get("/test-connection")
async def test_databricks_connection():
    """Test endpoint to verify Databricks connection"""
    try:
        result = test_connection()
        return result
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

@router.get("/test-evaluation-table")
async def test_evaluation_table():
    """Test endpoint to verify evaluation table exists and structure"""
    try:
        from databricks_client import get_databricks_client
        client = get_databricks_client()
        
        # Test if table exists and get its schema
        from databricks_client import EVALUATION_TABLE
        describe_query = f"DESCRIBE TABLE {EVALUATION_TABLE}"
        try:
            schema = client.query(describe_query)
            
            # Test a simple select to see if we can read from it
            test_query = f"SELECT COUNT(*) as row_count FROM {EVALUATION_TABLE} LIMIT 1"
            count_result = client.query(test_query)
        except Exception as table_error:
            # Table might not exist, try to create it
            client.create_evaluation_table_if_not_exists()
            schema = client.query(describe_query)
            count_result = client.query(test_query)
        
        return {
            "table_exists": True,
            "schema": schema,
            "row_count": count_result[0] if count_result else 0
        }
    except Exception as e:
        logger.error(f"Evaluation table test failed: {str(e)}")
        return {
            "table_exists": False,
            "error": str(e)
        }

def convert_flattened_rows_to_review(db_rows: List[dict]) -> ReviewSummary:
    """Convert multiple flattened Databricks rows (same survey response) to a ReviewSummary model"""
    try:
        if not db_rows:
            raise ValueError("No rows provided")
        
        # All rows should have the same response_id, use first row for basic info
        first_row = db_rows[0]
        response_id = str(first_row['response_id'])
        
        # Verify all rows are for the same survey response
        for row in db_rows:
            if str(row['response_id']) != response_id:
                raise ValueError(f"Mixed response IDs in rows: {response_id} vs {row['response_id']}")
        
        # Build category sentiments from all rows
        category_sentiments = []
        for row in db_rows:
            if row.get('comment_category') and row.get('comment_subcategory'):
                category_sentiment = CategorySentiment(
                    category=row['comment_category'],
                    category_sentiment_label=row.get('category_sentiment_label', 'Neutral'),
                    category_sentiment_score=float(row.get('category_sentiment_score', 0.0)),
                    subcategory=row['comment_subcategory'],
                    subcategory_sentiment_label=row.get('subcategory_sentiment_label', 'Neutral'),
                    subcategory_sentiment_score=float(row.get('subcategory_sentiment_score', 0.0))
                )
                category_sentiments.append(category_sentiment)
        
        # Create SentimentAnalysis object
        # ResponseRelevancy can be: "useful", "profane but useful", "nonsense or irrelevant"
        # Only mark as irrelevant if it's explicitly "nonsense or irrelevant"
        response_relevancy = first_row.get('response_relevancy', '').lower()
        is_irrelevant = 'irrelevant' in response_relevancy or 'nonsense' in response_relevancy
        
        sentiment_analysis = SentimentAnalysis(
            irrelevant=is_irrelevant,
            category_sentiments=category_sentiments
        )
        
        # Determine if review should be flagged (extreme sentiment scores)
        flagged_for_review = any(
            abs(sentiment.category_sentiment_score) > 0.5 or 
            abs(sentiment.subcategory_sentiment_score) > 0.5 
            for sentiment in category_sentiments
        )
        
        return ReviewSummary(
            response_id=response_id,
            question_label=first_row.get('question_label', 'COMMENT'),
            question_response=first_row.get('question_response', ''),
            relevant_comments=first_row.get('question_response', ''),  # Use question_response as relevant_comments
            profanity_check=True,  # Assume profanity was checked since we have profane column
            profane=bool(first_row.get('profane', False)),
            rewritten_comment=first_row.get('rewritten_comment') or '',
            sentiment_analysis=sentiment_analysis,
            status=ReviewStatus.RECOMMENDED if flagged_for_review else ReviewStatus.RANDOM_SAMPLE,
            store_id=first_row.get('store_key'),
            overall_sentiment_label=first_row.get('overall_sentiment_label'),
            overall_sentiment_score=first_row.get('overall_sentiment_score'),
            category_sentiments=category_sentiments,
            created_at=first_row.get('visit_datetime')  # Map visit_datetime to created_at
        )
    except Exception as e:
        logger.error(f"Error converting flattened rows to ReviewSummary: {str(e)}")
        logger.error(f"Problematic rows: {db_rows}")
        raise HTTPException(status_code=500, detail=f"Data conversion error: {str(e)}")

def convert_databricks_to_review(db_row: dict) -> ReviewSummary:
    """Convert a single Databricks row to a ReviewSummary model (legacy function)"""
    # For backward compatibility, convert single row as if it's a list
    return convert_flattened_rows_to_review([db_row])

def convert_completed_review_to_summary(db_row: dict) -> ReviewSummary:
    """Convert a completed review from evaluation table to ReviewSummary model"""
    try:
        import json
        
        # Parse category sentiments from JSON if available
        category_sentiments = []
        category_sentiments_json = db_row.get('human_eval_category_sentiments')
        if category_sentiments_json:
            try:
                category_sentiments_data = json.loads(category_sentiments_json)
                for cs_data in category_sentiments_data:
                    category_sentiment = CategorySentiment(
                        category=cs_data.get('category', ''),
                        category_sentiment_label=cs_data.get('category_sentiment_label', 'Neutral'),
                        category_sentiment_score=float(cs_data.get('category_sentiment_score', 0.0)),
                        subcategory=cs_data.get('subcategory', ''),
                        subcategory_sentiment_label=cs_data.get('subcategory_sentiment_label', 'Neutral'),
                        subcategory_sentiment_score=float(cs_data.get('subcategory_sentiment_score', 0.0))
                    )
                    category_sentiments.append(category_sentiment)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse category sentiments JSON: {str(e)}")
                category_sentiments = []
        
        # Create SentimentAnalysis object from human evaluations
        sentiment_analysis = SentimentAnalysis(
            irrelevant=bool(db_row.get('irrelevant', False)),
            category_sentiments=category_sentiments
        )
        
        return ReviewSummary(
            response_id=str(db_row['response_id']),
            question_label=db_row.get('question_label', 'COMMENT'),
            question_response=db_row.get('question_response', ''),
            relevant_comments=db_row.get('question_response', ''),
            profanity_check=True,
            profane=bool(db_row.get('profane', False)),
            rewritten_comment=db_row.get('rewritten_comment', ''),
            sentiment_analysis=sentiment_analysis,
            status=ReviewStatus.COMPLETED,  # These are completed reviews
            overall_sentiment_label=db_row.get('human_eval_overall_sentiment_label'),
            overall_sentiment_score=db_row.get('human_eval_overall_sentiment_score'),
            category_sentiments=category_sentiments
        )
    except Exception as e:
        logger.error(f"Error converting completed review to ReviewSummary: {str(e)}")
        logger.error(f"Problematic row: {db_row}")
        raise HTTPException(status_code=500, detail=f"Data conversion error: {str(e)}")

@router.post("/refresh-random-sample")
async def refresh_random_sample(
    limit: int = Query(20, description="Number of reviews in the new random sample"),
    use_databricks: bool = Query(True, description="Use Databricks data source")
):
    """Generate a new random sample of reviews excluding already validated ones"""
    
    if not use_databricks:
        # Fallback to mock data
        reviews = get_mock_reviews(limit=limit, offset=0, status="random_sample")
        return {
            "success": True,
            "message": f"Generated new random sample of {len(reviews)} reviews (mock data)",
            "sample_size": len(reviews)
        }
    
    try:
        # Get a fresh random sample excluding validated reviews
        db_rows = query_reviews_table(limit=limit, offset=0, exclude_validated=True)
        
        # Group rows by response_id since each survey can have multiple category/subcategory rows
        reviews_by_id = {}
        for row in db_rows:
            response_id = str(row['response_id'])
            if response_id not in reviews_by_id:
                reviews_by_id[response_id] = []
            reviews_by_id[response_id].append(row)
        
        # Convert grouped rows to ReviewSummary objects
        reviews = []
        for response_id, grouped_rows in reviews_by_id.items():
            try:
                review = convert_flattened_rows_to_review(grouped_rows)
                reviews.append(review)
            except Exception as e:
                logger.error(f"Failed to convert rows for response_id {response_id}: {str(e)}")
                continue
        
        logger.info(f"Generated new random sample of {len(reviews)} unvalidated reviews")
        
        return {
            "success": True,
            "message": f"Generated new random sample of {len(reviews)} unvalidated reviews",
            "sample_size": len(reviews)
        }
        
    except Exception as e:
        logger.error(f"Failed to generate new random sample: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate new random sample: {str(e)}")

@router.get("/reviews", response_model=List[ReviewSummary])
async def get_reviews(
    status: str = Query("random_sample", description="Filter by review status: random_sample, completed, recommended"),
    limit: int = Query(10, description="Number of reviews to return"),
    offset: int = Query(0, description="Number of reviews to skip"),
    store_id: Optional[str] = Query(None, description="Filter by store ID"),
    use_databricks: bool = Query(True, description="Use Databricks data source (set to false for mock data)"),
):
    """Get reviews with filtering and pagination"""
    
    if not use_databricks:
        # Fallback to mock data for testing
        logger.info("Using mock data (use_databricks=false)")
        reviews = get_mock_reviews(limit=limit, offset=offset, status=status)
        if store_id:
            reviews = [r for r in reviews if r.store_id == store_id]
        return reviews
    
    try:
        if status == "completed":
            # Query completed reviews from evaluation table
            logger.info(f"Querying completed reviews from evaluation table: {limit} reviews with offset {offset}")
            from databricks_client import query_completed_reviews
            db_rows = query_completed_reviews(limit=limit, offset=offset)
            
            # Convert to ReviewSummary objects
            reviews = []
            for row in db_rows:
                try:
                    review = convert_completed_review_to_summary(row)
                    reviews.append(review)
                except Exception as e:
                    logger.error(f"Failed to convert completed review {row.get('response_id', 'unknown')}: {str(e)}")
                    # Continue processing other rows
                    continue
        elif status == "recommended":
            # DISABLED: Recommended reviews feature temporarily disabled pending vector search setup
            logger.info(f"Recommended reviews feature is disabled - returning empty list")
            return []
            
            # # Get all recommendation groups
            # logger.info(f"Querying recommended reviews from recommendations table")
            # recommendation_groups = get_all_recommendations()
            # 
            # if not recommendation_groups:
            #     # No recommendations available yet
            #     logger.info("No recommendations found - user hasn't completed any evaluations with corrections yet")
            #     return []
            # 
            # # Get all recommended reviews from all groups (flattened)
            # all_recommended_reviews = []
            # for group in recommendation_groups[:5]:  # Limit to latest 5 source reviews to avoid too many results
            #     source_reviews = get_recommendations_for_source(group['source_review_id'])
            #     for review_dict in source_reviews:
            #         # Convert dict back to ReviewSummary object
            #         review = ReviewSummary(**{k: v for k, v in review_dict.items() if k != 'similarity_score'})
            #         review.status = ReviewStatus.RECOMMENDED
            #         all_recommended_reviews.append(review)
            # 
            # # Apply pagination
            # reviews = all_recommended_reviews[offset:offset + limit]
            # logger.info(f"Returning {len(reviews)} recommended reviews from {len(recommendation_groups)} source evaluations")
        else:
            # Query regular reviews from source table (flattened structure)
            # For random_sample, exclude already validated reviews
            exclude_validated = (status == "random_sample")
            logger.info(f"Querying Databricks for {limit} reviews with offset {offset} (exclude_validated: {exclude_validated})")
            db_rows = query_reviews_table(limit=limit, offset=offset, status_filter=status, exclude_validated=exclude_validated)
            
            # Group rows by response_id since each survey can have multiple category/subcategory rows
            reviews_by_id = {}
            for row in db_rows:
                response_id = str(row['response_id'])
                if response_id not in reviews_by_id:
                    reviews_by_id[response_id] = []
                reviews_by_id[response_id].append(row)
            
            # Convert grouped rows to ReviewSummary objects
            reviews = []
            for response_id, grouped_rows in reviews_by_id.items():
                try:
                    review = convert_flattened_rows_to_review(grouped_rows)
                    reviews.append(review)
                except Exception as e:
                    logger.error(f"Failed to convert rows for response_id {response_id}: {str(e)}")
                    # Continue processing other rows
                    continue
        
        logger.info(f"Successfully converted {len(reviews)} reviews from Databricks")
        
        # Apply store_id filter if specified (for future use)
        if store_id:
            reviews = [r for r in reviews if r.store_id == store_id]
        
        return reviews
        
    except Exception as e:
        logger.error(f"Failed to fetch reviews from Databricks: {str(e)}")
        # Fallback to mock data on error
        logger.info("Falling back to mock data due to Databricks error")
        reviews = get_mock_reviews(limit=limit, offset=offset, status=status)
        if store_id:
            reviews = [r for r in reviews if r.store_id == store_id]
        return reviews

@router.get("/reviews/{review_id}", response_model=ReviewDetail)
async def get_review_detail(
    review_id: str = Path(..., description="Review ID"),
    use_databricks: bool = Query(True, description="Use Databricks data source (set to false for mock data)")
):
    """Get detailed review information"""
    
    if not use_databricks:
        # Fallback to mock data
        review = get_mock_review_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return review
    
    try:
        # First check if this review has been evaluated (prioritize evaluation data)
        from databricks_client import get_databricks_client, EVALUATION_TABLE, BACKEND_DATA_TABLE
        client = get_databricks_client()
        
        # Check for evaluation data first
        eval_query = f"""
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
            created_at,
            updated_at
        FROM {EVALUATION_TABLE}
        WHERE survey_response_id = '{review_id}'
        """
        
        try:
            eval_results = client.query(eval_query)
            if eval_results:
                # Review has been evaluated - use evaluation data
                logger.info(f"Found evaluation data for review {review_id}, using human evaluation")
                eval_row = eval_results[0]
                
                # Convert evaluation data to ReviewSummary
                review_summary = convert_completed_review_to_summary(eval_row)
                
                # Create ReviewDetail with evaluation status
                review_detail = ReviewDetail(
                    **review_summary.dict(),
                    validation_status="completed",
                    user_corrections=None,  # Could be populated from evaluation data if needed
                    accuracy_score=None
                )
                
                return review_detail
                
        except Exception as eval_error:
            logger.info(f"No evaluation found for review {review_id}, using original data: {str(eval_error)}")
        
        # No evaluation found - use original source data
        # Note: No filter on ResponseRelevancy - include ALL reviews so humans can validate relevancy classification
        logger.info(f"Using original source data for review {review_id}")
        query = f"""
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
        WHERE t.SurveyResponseId = '{review_id}'
        ORDER BY t.CommentCategory, t.CommentSubcategory
        """
        
        results = client.query(query)
        
        if not results:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Convert flattened results to ReviewSummary using our conversion function
        review_summary = convert_flattened_rows_to_review(results)
        
        # Create ReviewDetail with additional fields
        review_detail = ReviewDetail(
            **review_summary.dict(),
            validation_status="pending",
            user_corrections=None,
            accuracy_score=None
        )
        
        return review_detail
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Failed to fetch review {review_id} from Databricks: {str(e)}")
        # Fallback to mock data
        review = get_mock_review_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return review

@router.get("/reviews/{review_id}/similar")
async def get_similar_reviews_for_review(
    review_id: str = Path(..., description="Review ID to find similar reviews for"),
    limit: int = Query(10, description="Number of similar reviews to return"),
    use_databricks: bool = Query(True, description="Use Databricks vector search")
):
    """Get semantically similar reviews for a given review"""
    
    if not use_databricks:
        # Fallback to empty results for testing
        return []
    
    try:
        # First get the original review to use its text for similarity search
        original_review = await get_review_detail(review_id, use_databricks=True)
        query_text = original_review.question_response
        
        if not query_text or len(query_text.strip()) < 10:
            logger.warning(f"Review {review_id} has insufficient text for similarity search")
            return []
        
        # Get similar reviews, excluding the original
        similar_reviews_data = get_similar_reviews(
            query_text=query_text,
            num_results=limit,
            exclude_response_id=review_id
        )
        
        # Convert to ReviewSummary objects
        similar_reviews = []
        for row in similar_reviews_data:
            try:
                # Create a mock db_row structure for conversion
                db_row = {
                    'response_id': row['response_id'],
                    'question_label': row.get('question_label', 'COMMENT'),
                    'question_response': row['question_response'],
                    'Pricing': float(row['aspect_pricing']) if row.get('aspect_pricing') is not None else None,
                    'Other': float(row['aspect_other']) if row.get('aspect_other') is not None else None,
                    'Food_Experience': float(row['aspect_food_and_beverage']) if row.get('aspect_food_and_beverage') is not None else None,
                    'Wait_Time': float(row['aspect_wait_time']) if row.get('aspect_wait_time') is not None else None,
                    'Service': float(row['aspect_service']) if row.get('aspect_service') is not None else None,
                    'Cleanliness': float(row['aspect_cleanliness']) if row.get('aspect_cleanliness') is not None else None,
                    'Ambiance': float(row['aspect_ambiance']) if row.get('aspect_ambiance') is not None else None,
                    'irrelevant': False,  # Assume not irrelevant since they were indexed
                    'profane': False,
                    'rewritten_comment': '',
                    'Flagged_For_Review': True,  # Mark as recommended since they're similar
                    'similarity_score': row.get('similarity_score', 0.0)
                }
                
                review = convert_databricks_to_review(db_row)
                # Override status to recommended since these are similar reviews
                review.status = ReviewStatus.RECOMMENDED
                similar_reviews.append(review)
                
            except Exception as e:
                logger.error(f"Failed to convert similar review {row.get('response_id', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"Found {len(similar_reviews)} similar reviews for {review_id}")
        return similar_reviews
        
    except Exception as e:
        logger.error(f"Failed to get similar reviews for {review_id}: {str(e)}")
        # Return empty list on error rather than raising exception
        return []


@router.get("/recommendations")
async def get_recommendation_groups(
    use_databricks: bool = Query(True, description="Use Databricks data source")
):
    """Get all recommendation groups showing which evaluations generated recommendations"""
    
    # DISABLED: Recommended reviews feature temporarily disabled pending vector search setup
    logger.info("Recommendations endpoint called but feature is disabled - returning empty list")
    return []
    
    # if not use_databricks:
    #     return []
    # 
    # try:
    #     recommendation_groups = get_all_recommendations()
    #     
    #     # Enhance with source review details for better display
    #     enhanced_groups = []
    #     for group in recommendation_groups:
    #         source_review_id = group['source_review_id']
    #         
    #         # Get the recommended reviews for this source
    #         recommended_reviews_data = get_recommendations_for_source(source_review_id)
    #         
    #         # Convert to ReviewSummary objects for frontend
    #         recommended_reviews = []
    #         for review_dict in recommended_reviews_data:
    #             review = ReviewSummary(**{k: v for k, v in review_dict.items() if k != 'similarity_score'})
    #             review.status = ReviewStatus.RECOMMENDED
    #             recommended_reviews.append(review.dict())
    #         
    #         enhanced_groups.append({
    #             "source_review_id": source_review_id,
    #             "source_review_text": group['source_review_text'][:200] + "..." if len(group['source_review_text']) > 200 else group['source_review_text'],
    #             "recommendation_timestamp": group['recommendation_timestamp'],
    #             "recommendation_count": group['recommendation_count'],
    #             "recommended_reviews": recommended_reviews  # Include all recommended reviews
    #         })
    #     
    #     return enhanced_groups
    #     
    # except Exception as e:
    #     logger.error(f"Failed to get recommendation groups: {str(e)}")
    #     return []


@router.get("/recommendations/{source_review_id}")
async def get_recommendations_by_source(
    source_review_id: str = Path(..., description="Source review ID that generated recommendations"),
    use_databricks: bool = Query(True, description="Use Databricks data source")
):
    """Get all recommended reviews for a specific source review"""
    
    # DISABLED: Recommended reviews feature temporarily disabled pending vector search setup
    logger.info(f"Recommendations by source endpoint called for {source_review_id} but feature is disabled - returning empty list")
    return []
    
    # if not use_databricks:
    #     return []
    # 
    # try:
    #     recommended_reviews = get_recommendations_for_source(source_review_id)
    #     
    #     # Convert to ReviewSummary objects
    #     reviews = []
    #     for review_dict in recommended_reviews:
    #         review = ReviewSummary(**{k: v for k, v in review_dict.items() if k != 'similarity_score'})
    #         review.status = ReviewStatus.RECOMMENDED
    #         reviews.append(review)
    #     
    #     return reviews
    #     
    # except Exception as e:
    #     logger.error(f"Failed to get recommendations for source {source_review_id}: {str(e)}")
    #     return []

@router.post("/reviews/{review_id}/validate")
async def validate_review(
    review_id: str = Path(..., description="Review ID"),
    validation: ValidationRequest = ...,
    use_databricks: bool = Query(True, description="Write to Databricks evaluation table")
):
    """Validate a review with optional label overrides"""
    
    if not use_databricks:
        # Fallback to mock behavior
        review = get_mock_review_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        review.validation_status = "validated"
        return {
            "success": True,
            "review_id": review_id,
            "decision": validation.decision,
            "message": f"Review {review_id} has been {validation.decision}ed"
        }
    
    try:
        # First, get the original review to get the question_response
        original_review = await get_review_detail(review_id, use_databricks=True)
        
        # Prepare human evaluation data optimized for the optimization pipeline
        human_eval_data = {
            "question_label": original_review.question_label,
            "question_response": original_review.question_response,
            "profane": None,  # Will be set based on validation
            "rewritten_comment": None,  # Will be set if provided
            "irrelevant": None,  # Will be set based on validation
            "overall_sentiment_label": None,  # Will be set based on validation
            "overall_sentiment_score": None,  # Will be set based on validation
            "category_sentiments": [],  # Will be populated from validation
            "aspects": {},  # Legacy aspects for backward compatibility
            "store_id": original_review.store_id,
            "visit_datetime": original_review.created_at
        }
        
        # Prepare machine evaluation data (original predictions) for comparison
        machine_eval_data = {
            "profane": original_review.profane,
            "rewritten_comment": original_review.rewritten_comment,
            "irrelevant": False,  # Assume original was not marked irrelevant
            "overall_sentiment_label": original_review.overall_sentiment_label,
            "overall_sentiment_score": original_review.overall_sentiment_score,
            "category_sentiments": original_review.category_sentiments or []
        }
        
        # Handle different validation decisions
        if validation.decision == "accept":
            # Accept the original ML predictions as correct
            sentiment_data = original_review.sentiment_analysis
            if isinstance(sentiment_data, dict):
                human_eval_data["irrelevant"] = sentiment_data.get("irrelevant", False)
            else:
                human_eval_data["irrelevant"] = sentiment_data.irrelevant
            
            human_eval_data["profane"] = original_review.profane
            human_eval_data["rewritten_comment"] = original_review.rewritten_comment
            human_eval_data["overall_sentiment_label"] = original_review.overall_sentiment_label
            human_eval_data["overall_sentiment_score"] = original_review.overall_sentiment_score
            human_eval_data["category_sentiments"] = original_review.category_sentiments or []
            
        elif validation.decision == "override":
            # Use the human-provided corrections
            if validation.updated_labels:
                sentiment_data = validation.updated_labels.get("sentiment_analysis", {})
                human_eval_data["irrelevant"] = sentiment_data.get("irrelevant", False)
                
                human_eval_data["profane"] = validation.updated_labels.get("profane", original_review.profane)
                human_eval_data["rewritten_comment"] = validation.updated_labels.get("rewritten_comment", original_review.rewritten_comment)
                human_eval_data["overall_sentiment_label"] = validation.updated_labels.get("overall_sentiment_label", original_review.overall_sentiment_label)
                human_eval_data["overall_sentiment_score"] = validation.updated_labels.get("overall_sentiment_score", original_review.overall_sentiment_score)
                
                # Get category sentiments from updated labels
                category_sentiments = validation.updated_labels.get("category_sentiments", original_review.category_sentiments or [])
                # Convert CategorySentiment objects to dictionaries if needed
                if category_sentiments:
                    human_eval_data["category_sentiments"] = []
                    for cs in category_sentiments:
                        if hasattr(cs, 'dict'):  # Pydantic model
                            human_eval_data["category_sentiments"].append(cs.dict())
                        elif isinstance(cs, dict):
                            human_eval_data["category_sentiments"].append(cs)
                        else:
                            # Try to convert to dict
                            human_eval_data["category_sentiments"].append({
                                "category": getattr(cs, 'category', ''),
                                "category_sentiment_label": getattr(cs, 'category_sentiment_label', ''),
                                "category_sentiment_score": getattr(cs, 'category_sentiment_score', 0.0),
                                "subcategory": getattr(cs, 'subcategory', ''),
                                "subcategory_sentiment_label": getattr(cs, 'subcategory_sentiment_label', ''),
                                "subcategory_sentiment_score": getattr(cs, 'subcategory_sentiment_score', 0.0)
                            })
                else:
                    human_eval_data["category_sentiments"] = []
                    
            else:
                # No corrections provided, treat as accept
                sentiment_data = original_review.sentiment_analysis
                if isinstance(sentiment_data, dict):
                    human_eval_data["irrelevant"] = sentiment_data.get("irrelevant", False)
                else:
                    human_eval_data["irrelevant"] = sentiment_data.irrelevant
                
                human_eval_data["profane"] = original_review.profane
                human_eval_data["rewritten_comment"] = original_review.rewritten_comment
                human_eval_data["overall_sentiment_label"] = original_review.overall_sentiment_label
                human_eval_data["overall_sentiment_score"] = original_review.overall_sentiment_score
                human_eval_data["category_sentiments"] = original_review.category_sentiments or []
                
        elif validation.decision == "skip":
            # Don't write anything for skipped reviews
            return {
                "success": True,
                "review_id": review_id,
                "decision": validation.decision,
                "message": f"Review {review_id} has been skipped (no evaluation written)"
            }
        
        # Write to Databricks evaluation table
        from databricks_client import write_human_evaluation
        success = write_human_evaluation(review_id, human_eval_data, machine_eval_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to write evaluation to database")
        
        # DISABLED: Recommendation generation temporarily disabled pending vector search setup
        # If this was an override with corrections, find similar reviews for recommendation
        # similar_reviews_found = 0
        # if validation.decision == "override" and validation.corrections_made and validation.corrections_made > 0:
        #     try:
        #         similar_reviews_data = get_similar_reviews(
        #             query_text=original_review.question_response,
        #             num_results=5,
        #             exclude_response_id=review_id
        #         )
        #         similar_reviews_found = len(similar_reviews_data)
        #         
        #         # Store recommendations in database for persistence
        #         if similar_reviews_data:
        #             store_recommendations(
        #                 source_review_id=review_id,
        #                 source_review_text=original_review.question_response,
        #                 similar_reviews=similar_reviews_data
        #             )
        #         
        #         logger.info(f"Found and stored {similar_reviews_found} similar reviews for recommendation after correction")
        #     except Exception as e:
        #         logger.warning(f"Could not find similar reviews after correction: {str(e)}")
        
        return {
            "success": True,
            "review_id": review_id,
            "decision": validation.decision,
            "corrections_made": validation.corrections_made or 0,
            "message": f"Review {review_id} has been {validation.decision}ed and saved to evaluation table"
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Failed to validate review {review_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
