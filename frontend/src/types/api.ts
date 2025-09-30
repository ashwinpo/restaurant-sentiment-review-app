export type ValidationDecision = "accept" | "override" | "skip";

export type ReviewStatus = "random_sample" | "completed" | "recommended";

// Category types based on flattened data structure
export type CommentCategory = 
  | "Atmosphere"
  | "Food"
  | "General"
  | "Menu Feedback"
  | "Other"
  | "Service"
  | "Value";

// New subcategory types
export type CommentSubcategory =
  | "Atmosphere"
  | "Flavor"
  | "Food Preparation"
  | "Quality"
  | "General"
  | "Menu Feedback"
  | "Other"
  | "Service Personnel"
  | "Slow Service- After seating delays"
  | "Wait Time- Prior to seating "
  | "Missing Items"
  | "Loyalty/Offers"
  | "Price";

// New interface for individual category/subcategory sentiment pairs
export interface CategorySentiment {
  category: string;
  category_sentiment_label: string;
  category_sentiment_score: number;
  subcategory: string;
  subcategory_sentiment_label: string;
  subcategory_sentiment_score: number;
}

export interface SentimentAnalysis {
  irrelevant: boolean;
  category_sentiments?: CategorySentiment[];
}

export interface ReviewSummary {
  response_id: string;
  question_label: string;
  question_response: string;
  relevant_comments: string;
  profanity_check: boolean;
  profane: boolean;
  rewritten_comment?: string;
  sentiment_analysis: SentimentAnalysis;
  created_at?: string;
  store_id?: string;
  status: ReviewStatus;
  // New fields for flattened structure
  overall_sentiment_label?: string;
  overall_sentiment_score?: number;
  category_sentiments?: CategorySentiment[];
}

export interface ReviewDetail extends ReviewSummary {
  validation_status?: string;
  user_corrections?: Record<string, any>;
  accuracy_score?: number;
}

export interface ValidationRequest {
  updated_labels?: Record<string, any>;
  decision: ValidationDecision;
  corrections_made?: number;
}

export interface MetricsOverview {
  total_random_sample: number;
  completed_today: number;
  recommended_reviews: number;
  total_reviews: number;
  average_accuracy: number;
  corrections_per_review: number;
}

export interface ValidationResponse {
  success: boolean;
  review_id: string;
  decision: ValidationDecision;
  message: string;
}
