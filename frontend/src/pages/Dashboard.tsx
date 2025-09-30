import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useLocation } from 'react-router-dom';
import { reviewsApi, metricsApi } from '../api/client';
import type { ReviewSummary, ReviewStatus } from '../types/api';

const Dashboard = () => {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const activeTab = (params.get('tab') as ReviewStatus) || 'random_sample';
  const queryClient = useQueryClient();

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: metricsApi.getOverview,
  });

  const { data: reviews, isLoading: reviewsLoading } = useQuery({
    queryKey: ['reviews', activeTab],
    queryFn: () => reviewsApi.getReviews({ status: activeTab, limit: 20 }),
    staleTime: 30000, // 30 seconds
  });

  // Mutation for refreshing random sample
  const refreshSampleMutation = useMutation({
    mutationFn: () => fetch('/api/v1/refresh-random-sample?limit=20', { method: 'POST' }).then(res => res.json()),
    onSuccess: () => {
      // Invalidate and refetch the reviews query to show the new sample
      queryClient.invalidateQueries({ queryKey: ['reviews', 'random_sample'] });
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
    },
  });

  // DISABLED: Recommended reviews feature temporarily disabled pending vector search setup
  // const { data: recommendationGroups } = useQuery({
  //   queryKey: ['recommendationGroups'],
  //   queryFn: () => reviewsApi.getRecommendationGroups(),
  //   enabled: activeTab === 'recommended',
  //   staleTime: 5 * 60 * 1000, // 5 minutes
  // });

  const getSentimentSummary = (review: ReviewSummary) => {
    if (review.sentiment_analysis.irrelevant) {
      return { name: 'Irrelevant', score: null, color: 'bg-gray-100 text-gray-800' };
    }

    // Use category sentiments system
    if (review.category_sentiments && review.category_sentiments.length > 0) {
      // Find the category/subcategory with the strongest sentiment (furthest from 0)
      const topSentiment = review.category_sentiments.reduce((a, b) => 
        Math.abs(a.subcategory_sentiment_score) > Math.abs(b.subcategory_sentiment_score) ? a : b
      );

      const score = topSentiment.subcategory_sentiment_score;
      const color = score > 0.5 ? 'bg-green-100 text-green-800' : 
                    score < -0.5 ? 'bg-red-100 text-red-800' : 
                    'bg-yellow-100 text-yellow-800';

      return {
        name: `${topSentiment.category} → ${topSentiment.subcategory}`,
        score,
        color,
        isCategory: true,
        categoryCount: review.category_sentiments.length
      };
    }

    // No category sentiments available
    return { name: 'No categories', score: null, color: 'bg-gray-100 text-gray-800' };
  };

  const getTabTitle = () => {
    switch (activeTab) {
      case 'random_sample': return 'Random Sample Reviews';
      case 'completed': return 'Completed Reviews';
      case 'recommended': return 'Recommended Reviews';
      default: return 'Reviews';
    }
  };

  const getTabDescription = () => {
    switch (activeTab) {
      case 'random_sample': return 'Random sample of reviews for validation';
      case 'completed': return 'Reviews you have already validated';
      case 'recommended': return 'Reviews recommended based on your corrections';
      default: return 'Reviews for validation';
    }
  };

  if (metricsLoading || reviewsLoading) {
    return (
      <div className="animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white p-6 rounded-lg shadow h-24"></div>
          ))}
        </div>
        <div className="bg-white rounded-lg shadow h-96"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-bloomin-red rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">🎲</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Random Sample</p>
              <p className="text-2xl font-bold text-gray-900">{metrics?.total_random_sample || 0}</p>
              <p className="text-xs text-gray-500">reviews shown</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">📋</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Reviews</p>
              <p className="text-2xl font-bold text-gray-900">{metrics?.total_reviews?.toLocaleString() || 0}</p>
              <p className="text-xs text-gray-500">in database</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-bloomin-green rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">✅</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Completed</p>
              <p className="text-2xl font-bold text-gray-900">{metrics?.completed_today || 0}</p>
              <p className="text-xs text-gray-500">evaluations</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">📝</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Avg Corrections</p>
              <p className="text-2xl font-bold text-gray-900">
                {(metrics?.corrections_per_review || 0).toFixed(1)}
              </p>
              <p className="text-xs text-gray-500">changes per review</p>
            </div>
          </div>
        </div>
      </div>

      {/* Reviews Content */}
      {activeTab === 'recommended' ? (
        /* Recommended Reviews - Temporarily Disabled */
        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">{getTabTitle()}</h2>
              <p className="mt-1 text-sm text-gray-600">
                {getTabDescription()}
              </p>
            </div>

            {/* Empty state - Feature temporarily disabled */}
            <div className="text-center py-12">
              <div className="text-gray-500">
                <div className="mx-auto h-12 w-12 text-gray-400 mb-4">
                  🎯
                </div>
                <p className="text-lg font-medium">Recommended Reviews Feature</p>
                <p className="text-sm mt-2">
                  This feature is temporarily disabled pending vector search setup.
                </p>
                <p className="text-sm mt-1 text-gray-400">
                  Once enabled, you'll see semantically similar reviews based on your corrections.
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Regular Table View for Random Sample and Completed */
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-medium text-gray-900">{getTabTitle()}</h2>
                <p className="mt-1 text-sm text-gray-600">
                  {getTabDescription()}
                </p>
              </div>
              {activeTab === 'random_sample' && (
                <button
                  onClick={() => refreshSampleMutation.mutate()}
                  disabled={refreshSampleMutation.isPending}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-bloomin-red hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {refreshSampleMutation.isPending ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Refreshing...
                    </>
                  ) : (
                    <>
                      <svg className="-ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      New Sample
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Review
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Categories
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Top Sentiment
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Store
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Flags
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {reviews?.map((review) => {
                  const sentimentSummary = getSentimentSummary(review);
                  return (
                    <tr key={review.response_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="max-w-xs">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {review.question_label}
                          </p>
                          <p className="text-sm text-gray-500 truncate">
                            {review.question_response}
                          </p>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-wrap gap-1">
                          {review.sentiment_analysis.irrelevant ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                              ❌ Irrelevant
                            </span>
                          ) : review.category_sentiments && review.category_sentiments.length > 0 ? (
                            // Show unique category tags
                            Array.from(new Set(review.category_sentiments.map(cs => cs.category))).map((category, index) => (
                              <span
                                key={index}
                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                  category === 'Service' ? 'bg-blue-100 text-blue-800' :
                                  category === 'Food' ? 'bg-green-100 text-green-800' :
                                  category === 'Atmosphere' ? 'bg-purple-100 text-purple-800' :
                                  category === 'Value' ? 'bg-yellow-100 text-yellow-800' :
                                  category === 'General' ? 'bg-gray-100 text-gray-800' :
                                  category === 'Menu Feedback' ? 'bg-orange-100 text-orange-800' :
                                  'bg-pink-100 text-pink-800'
                                }`}
                              >
                                {category}
                              </span>
                            ))
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                              No categories
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col space-y-1">
                          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${sentimentSummary.color}`}>
                            {sentimentSummary.name}
                            {sentimentSummary.score !== null && (
                              <span className="ml-1">({sentimentSummary.score > 0 ? '+' : ''}{sentimentSummary.score.toFixed(1)})</span>
                            )}
                          </span>
                          {sentimentSummary.isCategory && sentimentSummary.categoryCount && sentimentSummary.categoryCount > 1 && (
                            <span className="text-xs text-gray-500">
                              +{sentimentSummary.categoryCount - 1} more categories
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {review.store_id || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex space-x-1">
                          {review.profane && (
                            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">
                              🚫 Profane
                            </span>
                          )}
                          {activeTab === 'completed' && (
                            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                              ✅ Validated
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link
                          to={`/review/${review.response_id}?tab=${activeTab}`}
                          className="text-bloomin-red hover:text-red-700 transition-colors"
                        >
                          {activeTab === 'completed' ? 'View →' : 'Review →'}
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {(!reviews || reviews.length === 0) && (
            <div className="text-center py-12">
              <div className="text-gray-500">
                <p className="text-lg font-medium">
                  {activeTab === 'completed' ? 'No completed reviews yet' : 'No reviews in random sample'}
                </p>
                <p className="text-sm">
                  {activeTab === 'completed' ? 'Start validating reviews to see them here!' : 'Check back later for new reviews to validate'}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
