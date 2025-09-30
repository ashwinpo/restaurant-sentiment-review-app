from models import ReviewDetail, ReviewStatus, SentimentAnalysis
from datetime import datetime, timedelta
import random

# Mock data for testing with new JSON structure
MOCK_REVIEWS = [
    ReviewDetail(
        response_id="R001",
        question_label="Overall Experience",
        question_response="The food was absolutely amazing! The steak was cooked perfectly and the service was outstanding. Will definitely come back!",
        relevant_comments="The food was absolutely amazing! The steak was cooked perfectly and the service was outstanding. Will definitely come back!",
        profanity_check=False,
        profane=False,
        rewritten_comment=None,
        sentiment_analysis={
            "irrelevant": False,
            "aspects": {
                "Pricing": None,
                "Other": None,
                "Food and Beverage": 0.9,
                "Wait Time": None,
                "Service": 0.8,
                "Cleanliness": None,
                "Ambiance": 0.7
            }
        },
        created_at=datetime.now() - timedelta(hours=2),
        store_id="STORE_001",
        status=ReviewStatus.RANDOM_SAMPLE,
        validation_status="pending"
    ),
    ReviewDetail(
        response_id="R002",
        question_label="Service Quality",
        question_response="The waitress was rude and took forever to take our order. Food was cold when it arrived.",
        relevant_comments="The waitress was rude and took forever to take our order. Food was cold when it arrived.",
        profanity_check=False,
        profane=False,
        rewritten_comment=None,
        sentiment_analysis={
            "irrelevant": False,
            "aspects": {
                "Pricing": None,
                "Other": None,
                "Food and Beverage": -0.6,
                "Wait Time": -0.8,
                "Service": -0.9,
                "Cleanliness": None,
                "Ambiance": None
            }
        },
        created_at=datetime.now() - timedelta(hours=1),
        store_id="STORE_002",
        status=ReviewStatus.RANDOM_SAMPLE,
        validation_status="pending"
    ),
    ReviewDetail(
        response_id="R003",
        question_label="Food Quality",
        question_response="The damn food was terrible and the fucking service sucked ass!",
        relevant_comments="The damn food was terrible and the fucking service sucked ass!",
        profanity_check=True,
        profane=True,
        rewritten_comment="The food was terrible and the service was very poor!",
        sentiment_analysis={
            "irrelevant": False,
            "aspects": {
                "Pricing": None,
                "Other": None,
                "Food and Beverage": -0.9,
                "Wait Time": None,
                "Service": -0.8,
                "Cleanliness": None,
                "Ambiance": None
            }
        },
        created_at=datetime.now() - timedelta(minutes=30),
        store_id="STORE_001",
        status=ReviewStatus.RANDOM_SAMPLE,
        validation_status="pending"
    ),
    ReviewDetail(
        response_id="R004",
        question_label="Value",
        question_response="Great value for money! The portions were huge and prices reasonable.",
        relevant_comments="Great value for money! The portions were huge and prices reasonable.",
        profanity_check=False,
        profane=False,
        rewritten_comment=None,
        sentiment_analysis={
            "irrelevant": False,
            "aspects": {
                "Pricing": 0.9,
                "Other": None,
                "Food and Beverage": 0.7,
                "Wait Time": None,
                "Service": None,
                "Cleanliness": None,
                "Ambiance": None
            }
        },
        created_at=datetime.now() - timedelta(minutes=15),
        store_id="STORE_003",
        status=ReviewStatus.RANDOM_SAMPLE,
        validation_status="pending"
    ),
    ReviewDetail(
        response_id="R005",
        question_label="Atmosphere",
        question_response="The restaurant was okay, nothing special. Average food, average service.",
        relevant_comments="The restaurant was okay, nothing special. Average food, average service.",
        profanity_check=False,
        profane=False,
        rewritten_comment=None,
        sentiment_analysis={
            "irrelevant": False,
            "aspects": {
                "Pricing": None,
                "Other": None,
                "Food and Beverage": 0.0,
                "Wait Time": None,
                "Service": 0.0,
                "Cleanliness": None,
                "Ambiance": 0.0
            }
        },
        created_at=datetime.now() - timedelta(minutes=5),
        store_id="STORE_002",
        status=ReviewStatus.RANDOM_SAMPLE,
        validation_status="pending"
    ),
    ReviewDetail(
        response_id="R006",
        question_label="Irrelevant Comment",
        question_response="What time does the mall close?",
        relevant_comments="What time does the mall close?",
        profanity_check=False,
        profane=False,
        rewritten_comment=None,
        sentiment_analysis={
            "irrelevant": True
        },
        created_at=datetime.now() - timedelta(minutes=45),
        store_id="STORE_001",
        status=ReviewStatus.RANDOM_SAMPLE,
        validation_status="pending"
    ),
    # Some completed reviews
    ReviewDetail(
        response_id="C001",
        question_label="Completed Review",
        question_response="The service was excellent and food was great!",
        relevant_comments="The service was excellent and food was great!",
        profanity_check=False,
        profane=False,
        rewritten_comment=None,
        sentiment_analysis={
            "irrelevant": False,
            "aspects": {
                "Pricing": None,
                "Other": None,
                "Food and Beverage": 0.8,
                "Wait Time": None,
                "Service": 0.9,
                "Cleanliness": None,
                "Ambiance": None
            }
        },
        created_at=datetime.now() - timedelta(hours=3),
        store_id="STORE_001",
        status=ReviewStatus.COMPLETED,
        validation_status="completed",
        accuracy_score=0.95
    ),
    # Some recommended reviews
    ReviewDetail(
        response_id="REC001",
        question_label="Recommended Review",
        question_response="The ambiance was terrible but food was okay.",
        relevant_comments="The ambiance was terrible but food was okay.",
        profanity_check=False,
        profane=False,
        rewritten_comment=None,
        sentiment_analysis={
            "irrelevant": False,
            "aspects": {
                "Pricing": None,
                "Other": None,
                "Food and Beverage": 0.2,
                "Wait Time": None,
                "Service": None,
                "Cleanliness": None,
                "Ambiance": -0.8
            }
        },
        created_at=datetime.now() - timedelta(hours=1),
        store_id="STORE_002",
        status=ReviewStatus.RECOMMENDED,
        validation_status="pending"
    ),
]

def get_mock_reviews(limit: int = 10, offset: int = 0, status: str = "random_sample"):
    """Get mock reviews with pagination"""
    filtered_reviews = [r for r in MOCK_REVIEWS if r.status.value == status]
    return filtered_reviews[offset:offset + limit]

def get_mock_review_by_id(review_id: str):
    """Get a specific mock review by ID"""
    for review in MOCK_REVIEWS:
        if review.response_id == review_id:
            return review
    return None

def get_mock_metrics():
    """Get mock metrics for dashboard"""
    random_sample_reviews = [r for r in MOCK_REVIEWS if r.status == ReviewStatus.RANDOM_SAMPLE]
    completed_reviews = [r for r in MOCK_REVIEWS if r.status == ReviewStatus.COMPLETED]
    recommended_reviews = [r for r in MOCK_REVIEWS if r.status == ReviewStatus.RECOMMENDED]
    
    return {
        "total_random_sample": len(random_sample_reviews),
        "completed_today": len(completed_reviews),
        "recommended_reviews": len(recommended_reviews),
        "total_reviews": len(MOCK_REVIEWS),
        "average_accuracy": 0.87,
        "corrections_per_review": 2.3
    }
