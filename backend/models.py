from pydantic import BaseModel
from typing import Optional, List, Dict, Union, Any
from datetime import datetime
from enum import Enum

class ValidationDecision(str, Enum):
    ACCEPT = "accept"
    OVERRIDE = "override"
    SKIP = "skip"

class ReviewStatus(str, Enum):
    RANDOM_SAMPLE = "random_sample"
    COMPLETED = "completed"
    RECOMMENDED = "recommended"

# New category types based on the flattened data structure
class CommentCategory(str, Enum):
    ATMOSPHERE = "Atmosphere"
    FOOD = "Food"
    GENERAL = "General"
    MENU_FEEDBACK = "Menu Feedback"
    OTHER = "Other"
    SERVICE = "Service"
    VALUE = "Value"

# New subcategory types
class CommentSubcategory(str, Enum):
    ATMOSPHERE = "Atmosphere"
    FLAVOR = "Flavor"
    FOOD_PREPARATION = "Food Preparation"
    QUALITY = "Quality"
    GENERAL = "General"
    MENU_FEEDBACK = "Menu Feedback"
    OTHER = "Other"
    SERVICE_PERSONNEL = "Service Personnel"
    SLOW_SERVICE_AFTER_SEATING = "Slow Service- After seating delays"
    WAIT_TIME_PRIOR_TO_SEATING = "Wait Time- Prior to seating "
    MISSING_ITEMS = "Missing Items"
    LOYALTY_OFFERS = "Loyalty/Offers"
    PRICE = "Price"

# New model for individual sentiment entries (flattened structure)
class CategorySentiment(BaseModel):
    category: str  # CommentCategory
    category_sentiment_label: str  # Positive/Negative/Neutral
    category_sentiment_score: float
    subcategory: str  # CommentSubcategory
    subcategory_sentiment_label: str  # Positive/Negative/Neutral
    subcategory_sentiment_score: float

class SentimentAnalysis(BaseModel):
    irrelevant: bool
    aspects: Optional[Dict[str, Optional[float]]] = None
    # New field for flattened structure
    category_sentiments: Optional[List[CategorySentiment]] = None

# New model for the flattened data structure
class FlattenedReviewEntry(BaseModel):
    guest_sentiment_score_hash_key: str
    survey_response_hash_key: str
    survey_header_hash_key: str
    date_key: str
    visit_datetime: str
    visit_time: str
    survey_response_id: str
    question_id: str
    question_label: str
    question_response: str
    response_relevancy: str
    is_profanity_rewritten_flag: bool
    rewritten_question_response: Optional[str]
    overall_sentiment_label: str
    overall_sentiment_score: int
    comment_category: str
    category_sentiment_label: str
    category_sentiment_score: float
    comment_subcategory: str
    subcategory_sentiment_label: str
    subcategory_sentiment_score: float
    store_key: str
    jvp_code: str
    jvp_name: str
    mvp_code: str
    mvp_name: str
    concept_code: str
    day_part: str
    part_week: int
    part_month: int
    part_year: int
    source: str

class ReviewSummary(BaseModel):
    response_id: str
    question_label: str
    question_response: str
    relevant_comments: str
    profanity_check: bool
    profane: bool
    rewritten_comment: Optional[str]
    sentiment_analysis: Union[SentimentAnalysis, dict]  # JSON structure from LLM
    created_at: Optional[datetime] = None
    store_id: Optional[str] = None
    status: ReviewStatus = ReviewStatus.RANDOM_SAMPLE
    # New fields for flattened structure
    overall_sentiment_label: Optional[str] = None
    overall_sentiment_score: Optional[int] = None
    category_sentiments: Optional[List[CategorySentiment]] = None

class ReviewDetail(ReviewSummary):
    validation_status: Optional[str] = "pending"
    user_corrections: Optional[Dict[str, Any]] = None
    accuracy_score: Optional[float] = None  # How much user changed from original

class ValidationRequest(BaseModel):
    updated_labels: Optional[Dict[str, Any]] = None
    decision: ValidationDecision
    corrections_made: Optional[int] = 0  # Number of changes made

class MetricsOverview(BaseModel):
    total_random_sample: int
    completed_today: int
    recommended_reviews: int
    total_reviews: int
    average_accuracy: float
    corrections_per_review: float
