import React, { useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reviewsApi } from '../api/client';
import UnifiedCategoryEditor from '../components/UnifiedCategoryEditor';
import type { ValidationDecision, ReviewDetail, CategorySentiment } from '../types/api';

const Review = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  
  const params = new URLSearchParams(location.search);
  const returnTab = params.get('tab') || 'random_sample';
  
  const [isIrrelevant, setIsIrrelevant] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [isProfane, setIsProfane] = useState(false);
  const [rewrittenComment, setRewrittenComment] = useState('');
  const [categorySentiments, setCategorySentiments] = useState<CategorySentiment[]>([]);
  const [overallSentimentScore, setOverallSentimentScore] = useState<number | null>(null);
  const [overallSentimentLabel, setOverallSentimentLabel] = useState<string>('');

  const { data: review, isLoading } = useQuery<ReviewDetail>({
    queryKey: ['review', id],
    queryFn: () => reviewsApi.getReviewDetail(id!),
    enabled: !!id,
  });

  // Initialize state when review data changes
  React.useEffect(() => {
    if (review) {
      const sentimentAnalysis = review.sentiment_analysis;
      setIsIrrelevant(sentimentAnalysis.irrelevant);
      setIsProfane(review.profane || false);
      setRewrittenComment(review.rewritten_comment || '');
      
      // Initialize overall sentiment
      setOverallSentimentScore(review.overall_sentiment_score || null);
      setOverallSentimentLabel(review.overall_sentiment_label || '');
      
      // Initialize category sentiments if available
      if (review.category_sentiments && review.category_sentiments.length > 0) {
        setCategorySentiments([...review.category_sentiments]);
      }
    }
  }, [review]);

  const validateMutation = useMutation({
    mutationFn: (data: { decision: ValidationDecision; updated_labels?: any; corrections_made?: number }) =>
      reviewsApi.validateReview(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
      navigate(`/?tab=${returnTab}`);
    },
  });

  const calculateChanges = () => {
    if (!review) return 0;
    
    let changes = 0;
    const original = review.sentiment_analysis;
    
    // Check if irrelevant status changed
    if (isIrrelevant !== original.irrelevant) {
      changes++;
    }
    
    // Check if profanity status changed
    if (isProfane !== review.profane) {
      changes++;
    }
    
    // Check if rewritten comment changed
    if (rewrittenComment !== (review.rewritten_comment || '')) {
      changes++;
    }
    
    // Note: Category sentiment changes are tracked in the unified editor
    // and will be included in the validation payload
    
    return changes;
  };

  const handleAccept = () => {
    validateMutation.mutate({ decision: 'accept', corrections_made: 0 });
  };

  const handleSaveChanges = () => {
    const corrections = calculateChanges();
    const updated_labels = {
      sentiment_analysis: {
        irrelevant: isIrrelevant,
        category_sentiments: !isIrrelevant ? categorySentiments : undefined
      },
      profane: isProfane,
      rewritten_comment: isProfane && rewrittenComment.trim() ? rewrittenComment.trim() : undefined,
      overall_sentiment_score: overallSentimentScore,
      overall_sentiment_label: overallSentimentLabel,
      category_sentiments: !isIrrelevant ? categorySentiments : undefined
    };

    validateMutation.mutate({ 
      decision: 'override',
      updated_labels,
      corrections_made: corrections
    });
  };

  const handleSkip = () => {
    validateMutation.mutate({ decision: 'skip', corrections_made: 0 });
  };


  const handleIrrelevantChange = (irrelevant: boolean) => {
    setIsIrrelevant(irrelevant);
    setHasChanges(true);
    
    if (irrelevant) {
      // Clear category sentiments when marking as irrelevant
      setCategorySentiments([]);
    }
  };

  const handleProfanityChange = (profane: boolean) => {
    setIsProfane(profane);
    setHasChanges(true);
    
    if (!profane) {
      // Clear rewritten comment if no longer profane
      setRewrittenComment('');
    } else if (!rewrittenComment && review?.rewritten_comment) {
      // Restore original rewritten comment if marking as profane
      setRewrittenComment(review.rewritten_comment);
    }
  };

  const handleRewrittenCommentChange = (comment: string) => {
    setRewrittenComment(comment);
    setHasChanges(true);
  };

  const handleCategorySentimentsChange = (newCategorySentiments: CategorySentiment[]) => {
    setCategorySentiments(newCategorySentiments);
    setHasChanges(true);
  };

  const handleOverallSentimentChange = (score: number) => {
    const roundedScore = Math.round(score);
    setOverallSentimentScore(roundedScore);
    // Auto-update label based on score: 1-2=Negative, 3=Neutral, 4-5=Positive
    let label = 'Neutral';
    if (roundedScore >= 4) {
      label = 'Positive';
    } else if (roundedScore <= 2) {
      label = 'Negative';
    } else {
      label = 'Neutral'; // score === 3
    }
    setOverallSentimentLabel(label);
    setHasChanges(true);
  };

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="bg-white rounded-lg shadow p-6 mb-6 h-48"></div>
        <div className="bg-white rounded-lg shadow p-6 h-96"></div>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="text-center py-12">
        <p className="text-lg text-gray-500">Review not found</p>
        <button
          onClick={() => navigate(`/?tab=${returnTab}`)}
          className="mt-4 px-4 py-2 bg-bloomin-red text-white rounded hover:bg-red-700"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }


  return (
    <div className="flex flex-col lg:flex-row gap-6 min-h-screen">
      {/* Left Column - Sticky Comment and Info */}
      <div className="lg:w-1/3 lg:sticky lg:top-6 lg:self-start">
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          {/* Header */}
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <h1 className="text-lg font-bold text-gray-900">Review</h1>
              <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700">
                #{review.response_id}
              </span>
            </div>
            <div className="space-y-1">
              {review.store_id && (
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Store:</span> {review.store_id}
                </p>
              )}
              {review.created_at && (
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Visit:</span> {new Date(review.created_at).toLocaleDateString('en-US', {
                    weekday: 'short',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                  })} at {new Date(review.created_at).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
              )}
            </div>
            {hasChanges && (
              <p className="text-sm text-bloomin-red font-medium mt-2">
                Changes made
              </p>
            )}
          </div>

          {/* Status Badges */}
          <div className="flex flex-wrap gap-2">
            {(review.profane || isProfane) && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
                🚫 Contains Profanity
              </span>
            )}
            {review.sentiment_analysis.irrelevant && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
                ❌ Irrelevant
              </span>
            )}
            {returnTab === 'completed' && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                ✅ Completed
              </span>
            )}
          </div>

          {/* Original Comment */}
          <div className="border-l-4 border-bloomin-red pl-6 bg-gray-50 rounded-r-lg p-4">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Customer Comment</h3>
            <p className="text-gray-700 text-xl leading-relaxed font-medium">
              "{review.question_response}"
            </p>
          </div>

          {/* Overall Sentiment Display */}
          {(overallSentimentLabel || overallSentimentScore || review.overall_sentiment_label || review.overall_sentiment_score) && (
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h3 className="text-lg font-medium text-gray-900 mb-2">Overall Sentiment Analysis</h3>
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-600">Label:</span>
                  {overallSentimentLabel && overallSentimentLabel !== (review.overall_sentiment_label || 'Neutral') ? (
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600 line-through">
                        {review.overall_sentiment_label || 'Neutral'}
                      </span>
                      <span className="text-xs text-gray-400">→</span>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium border-2 border-orange-300 ${
                        overallSentimentLabel === 'Positive' ? 'bg-green-100 text-green-800' :
                        overallSentimentLabel === 'Negative' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {overallSentimentLabel} ✨
                      </span>
                    </div>
                  ) : (
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      (overallSentimentLabel || review.overall_sentiment_label) === 'Positive' ? 'bg-green-100 text-green-800' :
                      (overallSentimentLabel || review.overall_sentiment_label) === 'Negative' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {overallSentimentLabel || review.overall_sentiment_label || 'Neutral'}
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-600">Score:</span>
                  {overallSentimentScore && overallSentimentScore !== (review?.overall_sentiment_score || 3) ? (
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600 line-through">
                        {review?.overall_sentiment_score || 3}/5
                      </span>
                      <span className="text-xs text-gray-400">→</span>
                      <span className={`px-2 py-1 rounded text-sm font-medium border-2 border-orange-300 ${
                        overallSentimentScore >= 4 ? 'bg-green-100 text-green-800' :
                        overallSentimentScore <= 2 ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {overallSentimentScore}/5 ✨
                      </span>
                    </div>
                  ) : (
                    <span className={`px-2 py-1 rounded text-sm font-medium ${
                      (overallSentimentScore || review.overall_sentiment_score || 3) >= 4 ? 'bg-green-100 text-green-800' :
                      (overallSentimentScore || review.overall_sentiment_score || 3) <= 2 ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {overallSentimentScore || review.overall_sentiment_score || 3}/5
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Category Sentiments Display */}
          {((review.category_sentiments && review.category_sentiments.length > 0) || categorySentiments.length > 0) && (
            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
              <h3 className="text-lg font-medium text-gray-900 mb-3">
                Category Analysis 
                {categorySentiments.length !== (review.category_sentiments?.length || 0) && (
                  <span className="ml-2 text-sm text-orange-600">
                    (Modified ✨)
                  </span>
                )}
              </h3>
              <div className="space-y-3">
                {/* Group sentiments by category and show them together */}
                {(() => {
                  const currentSentiments = categorySentiments.length > 0 ? categorySentiments : review.category_sentiments || [];
                  const originalSentiments = review.category_sentiments || [];
                  const isModified = categorySentiments.length > 0;
                  
                  // Group by category
                  const groupedByCategory = currentSentiments.reduce((acc, sentiment) => {
                    if (!acc[sentiment.category]) {
                      acc[sentiment.category] = [];
                    }
                    acc[sentiment.category].push(sentiment);
                    return acc;
                  }, {} as Record<string, typeof currentSentiments>);

                  return Object.entries(groupedByCategory).map(([category, categoryItems]) => {
                    const originalCategoryItems = originalSentiments.filter(orig => orig.category === category);
                    const hasNewSubcategories = isModified && categoryItems.some(item => 
                      !originalCategoryItems.find(orig => orig.subcategory === item.subcategory)
                    );
                    const hasModifiedSubcategories = isModified && categoryItems.some(item => {
                      const original = originalCategoryItems.find(orig => orig.subcategory === item.subcategory);
                      return original && (
                        Math.abs(original.category_sentiment_score - item.category_sentiment_score) > 0.1 ||
                        Math.abs(original.subcategory_sentiment_score - item.subcategory_sentiment_score) > 0.1
                      );
                    });
                    const isNewCategory = isModified && originalCategoryItems.length === 0;

                    return (
                      <div key={category} className={`bg-white p-3 rounded-md border ${
                        isNewCategory ? 'border-green-300 bg-green-50' : 
                        hasNewSubcategories || hasModifiedSubcategories ? 'border-orange-300 bg-orange-50' : 
                        'border-purple-100'
                      }`}>
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-2">
                            <span className="font-semibold text-gray-900 text-lg">{category}</span>
                            {isNewCategory && <span className="text-xs text-green-600">NEW CATEGORY ✨</span>}
                            {(hasNewSubcategories || hasModifiedSubcategories) && !isNewCategory && (
                              <span className="text-xs text-orange-600">MODIFIED ✨</span>
                            )}
                          </div>
                          {/* Show category score once per category */}
                          <span className={`px-3 py-1 rounded text-sm font-medium ${
                            categoryItems[0].category_sentiment_score > 0.5 ? 'bg-green-100 text-green-800' :
                            categoryItems[0].category_sentiment_score < -0.5 ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            Category: {categoryItems[0].category_sentiment_score.toFixed(1)}
                            {(() => {
                              const originalCategoryScore = originalCategoryItems.length > 0 ? originalCategoryItems[0].category_sentiment_score : null;
                              const hasScoreChange = isModified && originalCategoryScore !== null && 
                                Math.abs(originalCategoryScore - categoryItems[0].category_sentiment_score) > 0.1;
                              return hasScoreChange ? (
                                <span className="ml-1 text-xs text-gray-500">
                                  (was {originalCategoryScore.toFixed(1)})
                                </span>
                              ) : null;
                            })()}
                          </span>
                        </div>
                        
                        {/* Subcategories within this category */}
                        <div className="space-y-2 pl-4">
                          {categoryItems.map((sentiment, subIndex) => {
                            const originalSentiment = originalCategoryItems.find(
                              orig => orig.subcategory === sentiment.subcategory
                            );
                            const isNewSubcategory = isModified && !originalSentiment;
                            const hasSubcategoryChanges = isModified && originalSentiment && (
                              Math.abs(originalSentiment.category_sentiment_score - sentiment.category_sentiment_score) > 0.1 ||
                              Math.abs(originalSentiment.subcategory_sentiment_score - sentiment.subcategory_sentiment_score) > 0.1
                            );

                            return (
                              <div key={subIndex} className={`p-2 rounded border ${
                                isNewSubcategory ? 'border-green-200 bg-green-25' : 
                                hasSubcategoryChanges ? 'border-orange-200 bg-orange-25' : 
                                'border-gray-100 bg-gray-25'
                              }`}>
                                <div className="flex items-center justify-between mb-1">
                                  <div className="flex items-center space-x-2">
                                    <span className="text-purple-700 font-medium">→ {sentiment.subcategory}</span>
                                    {isNewSubcategory && <span className="text-xs text-green-600">NEW ✨</span>}
                                    {hasSubcategoryChanges && <span className="text-xs text-orange-600">MODIFIED ✨</span>}
                                  </div>
                                </div>
                                <div className="flex items-center justify-between text-sm">
                                  <span className="text-gray-600">Score:</span>
                                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                                    sentiment.subcategory_sentiment_score > 0.5 ? 'bg-green-100 text-green-800' :
                                    sentiment.subcategory_sentiment_score < -0.5 ? 'bg-red-100 text-red-800' :
                                    'bg-gray-100 text-gray-800'
                                  }`}>
                                    {sentiment.subcategory_sentiment_score.toFixed(1)}
                                    {hasSubcategoryChanges && originalSentiment && (
                                      <span className="ml-1 text-xs text-gray-500">
                                        (was {originalSentiment.subcategory_sentiment_score.toFixed(1)})
                                      </span>
                                    )}
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  });
                })()}
                
                {/* Show removed categories/subcategories */}
                {(() => {
                  if (categorySentiments.length === 0 || !review.category_sentiments) return null;
                  
                  const originalSentiments = review.category_sentiments;
                  const currentSentiments = categorySentiments;
                  
                  // Group removed items by category
                  const removedByCategory = originalSentiments.reduce((acc, originalSentiment) => {
                    const stillExists = currentSentiments.find(
                      current => current.category === originalSentiment.category && current.subcategory === originalSentiment.subcategory
                    );
                    
                    if (!stillExists) {
                      if (!acc[originalSentiment.category]) {
                        acc[originalSentiment.category] = [];
                      }
                      acc[originalSentiment.category].push(originalSentiment);
                    }
                    return acc;
                  }, {} as Record<string, typeof originalSentiments>);

                  return Object.entries(removedByCategory).map(([category, removedItems]) => {
                    const categoryStillHasItems = currentSentiments.some(current => current.category === category);
                    const wholeCategoryRemoved = !categoryStillHasItems;

                    return (
                      <div key={`removed-${category}`} className="bg-red-50 p-3 rounded-md border border-red-200 opacity-75">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-2">
                            <span className={`font-semibold text-gray-600 text-lg ${wholeCategoryRemoved ? 'line-through' : ''}`}>
                              {category}
                            </span>
                            <span className="text-xs text-red-600">
                              {wholeCategoryRemoved ? 'CATEGORY REMOVED' : 'SUBCATEGORIES REMOVED'}
                            </span>
                          </div>
                          {/* Show removed category score */}
                          <span className="px-3 py-1 rounded text-sm font-medium bg-gray-100 text-gray-500 line-through">
                            Category: {removedItems[0].category_sentiment_score.toFixed(1)}
                          </span>
                        </div>
                        
                        {/* Removed subcategories */}
                        <div className="space-y-2 pl-4">
                          {removedItems.map((removedSentiment, subIndex) => (
                            <div key={subIndex} className="p-2 rounded border border-red-200 bg-red-25">
                              <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center space-x-2">
                                  <span className="text-purple-700 font-medium line-through">→ {removedSentiment.subcategory}</span>
                                  <span className="text-xs text-red-600">REMOVED</span>
                                </div>
                              </div>
                              <div className="flex items-center justify-between text-sm">
                                <span className="text-gray-500">Score:</span>
                                <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-500 line-through">
                                  {removedSentiment.subcategory_sentiment_score.toFixed(1)}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          )}

          {/* Rewritten Comment (if profane and has content) */}
          {((review.profane && review.rewritten_comment) || (isProfane && rewrittenComment)) && (
            <div className="border-l-4 border-bloomin-green pl-6 bg-green-50 rounded-r-lg p-4">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {isProfane && rewrittenComment !== review.rewritten_comment ? 
                  'Your Rewritten Version' : 
                  'AI Rewritten (Clean) Version'
                }
              </h3>
              <p className="text-gray-700 text-xl leading-relaxed font-medium">
                "{isProfane && rewrittenComment ? rewrittenComment : review.rewritten_comment}"
              </p>
              {isProfane && rewrittenComment !== review.rewritten_comment && review.rewritten_comment && (
                <div className="mt-3 pt-3 border-t border-green-200">
                  <p className="text-sm text-gray-600 mb-1">Original AI version:</p>
                  <p className="text-gray-600 italic">"{review.rewritten_comment}"</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right Column - Validation Interface */}
      <div className="lg:w-2/3 space-y-6">

        {/* Main Validation Interface */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">Validation</h2>
            <div className="text-sm text-gray-500">
              Select relevant categories and rate sentiment from -2 (very negative) to +2 (very positive)
            </div>
          </div>

          {/* Control Toggles */}
          <div className="space-y-4 mb-6">
            {/* Irrelevant Toggle */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isIrrelevant}
                  onChange={(e) => handleIrrelevantChange(e.target.checked)}
                  className="h-5 w-5 text-bloomin-red focus:ring-bloomin-red border-gray-300 rounded"
                />
                <div>
                  <span className="text-lg font-medium text-gray-900">
                    Mark this review as irrelevant
                  </span>
                  <p className="text-sm text-gray-600">
                    Check this if the comment is not about the restaurant experience (e.g., questions about hours, directions, etc.)
                  </p>
                </div>
              </label>
            </div>

            {/* Profanity Toggle */}
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isProfane}
                  onChange={(e) => handleProfanityChange(e.target.checked)}
                  className="h-5 w-5 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                />
                <div>
                  <span className="text-lg font-medium text-gray-900">
                    Mark this review as containing profanity
                  </span>
                  <p className="text-sm text-gray-600">
                    Check this if the comment contains inappropriate language that should be rewritten
                  </p>
                </div>
              </label>

              {/* Rewritten Comment Input */}
              {isProfane && (
                <div className="mt-4 pt-4 border-t border-red-200">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Rewritten Comment (Clean Version)
                  </label>
                  <textarea
                    value={rewrittenComment}
                    onChange={(e) => handleRewrittenCommentChange(e.target.value)}
                    placeholder="Enter a clean version of the comment..."
                    className="w-full p-3 border border-gray-300 rounded-md focus:ring-bloomin-red focus:border-bloomin-red"
                    rows={3}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Provide a clean, professional version of the customer's comment while preserving the original meaning.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Overall Sentiment Editor */}
          {!isIrrelevant && (
            <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Overall Sentiment Score</h3>
              <div className="space-y-2">
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-gray-500 w-8">1</span>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    value={Math.round(overallSentimentScore || review?.overall_sentiment_score || 3)}
                    onChange={(e) => handleOverallSentimentChange(parseInt(e.target.value))}
                    disabled={isIrrelevant}
                    className={`flex-1 h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer ${
                      (overallSentimentScore || review?.overall_sentiment_score || 3) >= 4 ? 'accent-green-500' :
                      (overallSentimentScore || review?.overall_sentiment_score || 3) <= 2 ? 'accent-red-500' :
                      'accent-yellow-500'
                    }`}
                  style={{
                    background: `linear-gradient(to right, 
                      #ef4444 0%, #ef4444 40%, 
                      #eab308 40%, #eab308 60%, 
                      #22c55e 60%, #22c55e 100%)`
                  }}
                  />
                  <span className="text-sm text-gray-500 w-8">5</span>
                  <select
                    value={Math.round(overallSentimentScore || review?.overall_sentiment_score || 3)}
                    onChange={(e) => handleOverallSentimentChange(parseInt(e.target.value))}
                    disabled={isIrrelevant}
                    className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={3}>3</option>
                    <option value={4}>4</option>
                    <option value={5}>5</option>
                  </select>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">Auto-generated Label:</span>
                  <span className={`px-2 py-1 rounded text-sm font-medium ${
                    (overallSentimentLabel || review?.overall_sentiment_label) === 'Positive' ? 'bg-green-100 text-green-800' :
                    (overallSentimentLabel || review?.overall_sentiment_label) === 'Negative' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {overallSentimentLabel || review?.overall_sentiment_label || 'Neutral'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Unified Category System */}
          {!isIrrelevant && (
            <div className="space-y-4">
              <UnifiedCategoryEditor
                sentiments={categorySentiments}
                onChange={handleCategorySentimentsChange}
                disabled={isIrrelevant}
              />
            </div>
          )}

          {isIrrelevant && (
            <div className="text-center py-8 text-gray-500">
              <p className="text-lg">Review marked as irrelevant</p>
              <p className="text-sm">No aspect ratings needed</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate(`/?tab=${returnTab}`)}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors flex items-center space-x-2"
            >
              <span>←</span>
              <span>Back to {returnTab.replace('_', ' ')}</span>
            </button>
            
            <div className="flex space-x-3">
              <button
                onClick={handleSkip}
                disabled={validateMutation.isPending}
                className="px-6 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                Skip
              </button>
              
              {hasChanges ? (
                <button
                  onClick={handleSaveChanges}
                  disabled={validateMutation.isPending}
                  className="px-8 py-2 bg-bloomin-blue text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium"
                >
                  {validateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              ) : (
                <button
                  onClick={handleAccept}
                  disabled={validateMutation.isPending}
                  className="px-8 py-2 bg-bloomin-green text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors font-medium"
                >
                  {validateMutation.isPending ? 'Accepting...' : 'Accept as Correct'}
                </button>
              )}
            </div>
          </div>
          
          {/* Keyboard Shortcuts Hint */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-500">
              💡 Tip: Select relevant categories, expand to see subcategories, use sliders to adjust sentiment ratings, or mark entire review as irrelevant
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Review;
