import axios from 'axios';
import type { 
  ReviewSummary, 
  ReviewDetail, 
  ValidationRequest, 
  ValidationResponse, 
  MetricsOverview 
} from '../types/api';

const API_BASE_URL = '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const reviewsApi = {
  // Get reviews with filtering and pagination
  getReviews: async (params?: {
    status?: string;
    limit?: number;
    offset?: number;
    store_id?: string;
  }): Promise<ReviewSummary[]> => {
    const response = await apiClient.get('/reviews', { params });
    return response.data;
  },

  // Get detailed review information
  getReviewDetail: async (reviewId: string): Promise<ReviewDetail> => {
    const response = await apiClient.get(`/reviews/${reviewId}`);
    return response.data;
  },

  // Validate a review
  validateReview: async (
    reviewId: string, 
    validation: ValidationRequest
  ): Promise<ValidationResponse> => {
    const response = await apiClient.post(`/reviews/${reviewId}/validate`, validation);
    return response.data;
  },

  // Get recommendation groups with source context
  getRecommendationGroups: async (): Promise<any[]> => {
    const response = await apiClient.get('/recommendations');
    return response.data;
  },

  // Get recommendations for a specific source review
  getRecommendationsForSource: async (sourceReviewId: string): Promise<ReviewSummary[]> => {
    const response = await apiClient.get(`/recommendations/${sourceReviewId}`);
    return response.data;
  },
};

export const metricsApi = {
  // Get dashboard metrics
  getOverview: async (): Promise<MetricsOverview> => {
    const response = await apiClient.get('/metrics/overview');
    return response.data;
  },
};

export const healthApi = {
  // Health check
  healthCheck: async (): Promise<{ status: string; timestamp: string }> => {
    const response = await apiClient.get('/healthcheck');
    return response.data;
  },
};
