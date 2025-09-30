import React, { useState } from 'react';
import type { CategorySentiment } from '../types/api';

interface UnifiedCategoryEditorProps {
  sentiments: CategorySentiment[];
  onChange: (sentiments: CategorySentiment[]) => void;
  disabled?: boolean;
}

// Define the complete category structure (from AI Sentiment Category.xlsx)
const CATEGORY_STRUCTURE = {
  'Atmosphere': ['Atmosphere'],
  'Food': ['Flavor', 'Food Preparation', 'Quality'],
  'General': ['General'],
  'Menu Feedback': ['Menu Feedback'],
  'Other': ['Other'],
  'Service': ['Service Personnel', 'Slow Service- After seating delays', 'Wait Time- Prior to seating ', 'Missing Items'],
  'Value': ['Loyalty/Offers', 'Price']
};

const UnifiedCategoryEditor: React.FC<UnifiedCategoryEditorProps> = ({
  sentiments,
  onChange,
  disabled = false
}) => {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  // Independent category scores - not tied to subcategory data
  const [categorySentimentScores, setCategorySentimentScores] = useState<Record<string, number>>({});

  // Auto-expand categories that have sentiments on initial load
  React.useEffect(() => {
    const categoriesWithSentiments = new Set<string>();
    const newCategoryScores: Record<string, number> = {};
    
    sentiments.forEach(sentiment => {
      categoriesWithSentiments.add(sentiment.category);
      // Initialize category score from first occurrence if not already set
      if (!(sentiment.category in newCategoryScores)) {
        newCategoryScores[sentiment.category] = sentiment.category_sentiment_score;
      }
    });
    
    setExpandedCategories(categoriesWithSentiments);
    setCategorySentimentScores(prev => {
      // Only add scores for categories that don't already have independent scores
      const updatedScores = { ...prev };
      Object.entries(newCategoryScores).forEach(([category, score]) => {
        if (!(category in prev)) {
          updatedScores[category] = score;
        }
      });
      return updatedScores;
    });
  }, [sentiments]);

  // Get all available top-level categories
  const allCategories = Object.keys(CATEGORY_STRUCTURE);
  
  // Create a map of existing sentiments for quick lookup
  const existingSentimentsMap = new Map<string, CategorySentiment>();
  sentiments.forEach(sentiment => {
    const key = `${sentiment.category}-${sentiment.subcategory}`;
    existingSentimentsMap.set(key, sentiment);
  });

  // Check if a category is selected (has any subcategories with sentiments)
  const isCategorySelected = (category: string): boolean => {
    return sentiments.some(sentiment => sentiment.category === category);
  };

  // Get selected subcategories for a category
  const getSelectedSubcategories = (category: string): string[] => {
    const subcategories = CATEGORY_STRUCTURE[category as keyof typeof CATEGORY_STRUCTURE];
    return subcategories.filter(subcategory => {
      const key = `${category}-${subcategory}`;
      return existingSentimentsMap.has(key);
    });
  };

  // Toggle category selection
  const toggleCategory = (category: string, selected: boolean) => {
    let newSentiments = [...sentiments];

    if (selected) {
      // Add the first subcategory as a placeholder to make the category "selected"
      // User can then choose which specific subcategories they want
      const subcategories = CATEGORY_STRUCTURE[category as keyof typeof CATEGORY_STRUCTURE];
      const firstSubcategory = subcategories[0];
      
      newSentiments.push({
        category,
        category_sentiment_label: 'Neutral',
        category_sentiment_score: 0,
        subcategory: firstSubcategory,
        subcategory_sentiment_label: 'Neutral',
        subcategory_sentiment_score: 0
      });
      
      // Expand the category and update sentiments
      setExpandedCategories(prev => new Set([...prev, category]));
      // Initialize independent category score
      setCategorySentimentScores(prev => ({
        ...prev,
        [category]: 0
      }));
      onChange(newSentiments);
    } else {
      // Remove all subcategories for this category
      newSentiments = newSentiments.filter(sentiment => sentiment.category !== category);
      // Collapse when category is deselected
      setExpandedCategories(prev => {
        const newExpanded = new Set(prev);
        newExpanded.delete(category);
        return newExpanded;
      });
      // Remove independent category score
      setCategorySentimentScores(prev => {
        const newScores = { ...prev };
        delete newScores[category];
        return newScores;
      });
      onChange(newSentiments);
    }
  };

  // Toggle subcategory selection
  const toggleSubcategory = (category: string, subcategory: string, selected: boolean) => {
    let newSentiments = [...sentiments];
    const key = `${category}-${subcategory}`;

    if (selected) {
      // Add this specific subcategory
      if (!existingSentimentsMap.has(key)) {
        newSentiments.push({
          category,
          category_sentiment_label: 'Neutral',
          category_sentiment_score: categorySentimentScores[category] ?? 0, // Use current category score
          subcategory,
          subcategory_sentiment_label: 'Neutral',
          subcategory_sentiment_score: 0
        });
      }
    } else {
      // Remove this specific subcategory
      newSentiments = newSentiments.filter(sentiment => 
        !(sentiment.category === category && sentiment.subcategory === subcategory)
      );
    }

    onChange(newSentiments);
  };

  // Update sentiment values
  const updateSentiment = (category: string, subcategory: string, updates: Partial<CategorySentiment>) => {
    const newSentiments = sentiments.map(sentiment => {
      if (sentiment.category === category && sentiment.subcategory === subcategory) {
        return { ...sentiment, ...updates };
      }
      return sentiment;
    });
    onChange(newSentiments);
  };

  // Toggle category expansion
  const toggleExpansion = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const getScoreColor = (score: number) => {
    if (score > 0.5) return 'text-green-600 bg-green-50';
    if (score < -0.5) return 'text-red-600 bg-red-50';
    return 'text-yellow-600 bg-yellow-50';
  };

  const getSliderColor = (score: number) => {
    if (score > 0.5) return 'accent-green-500';
    if (score < -0.5) return 'accent-red-500';
    return 'accent-yellow-500';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">
          Category Selection & Rating
        </h3>
        <div className="text-xs text-gray-500">
          Select categories (-3 to +3) and subcategories (-1 to +1)
        </div>
      </div>

      {allCategories.map(category => {
        const isSelected = isCategorySelected(category);
        const selectedSubcategories = getSelectedSubcategories(category);
        const isExpanded = expandedCategories.has(category);
        const subcategories = CATEGORY_STRUCTURE[category as keyof typeof CATEGORY_STRUCTURE];
        
        // Get the current category sentiment score from independent state
        const currentCategoryScore = categorySentimentScores[category] ?? 0;

        return (
          <div key={category} className="border border-gray-200 rounded-lg overflow-hidden">
            {/* Category Header */}
            <div className="p-4 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => toggleCategory(category, e.target.checked)}
                      disabled={disabled}
                      className="h-4 w-4 text-bloomin-red focus:ring-bloomin-red border-gray-300 rounded"
                    />
                    <span className="font-semibold text-gray-900 text-lg">
                      {category}
                    </span>
                  </label>
                  {isSelected && (
                    <span className="text-sm text-gray-600 bg-gray-200 px-2 py-1 rounded">
                      {selectedSubcategories.length}/{subcategories.length} selected
                    </span>
                  )}
                </div>
                {isSelected && (
                  <button
                    onClick={() => toggleExpansion(category)}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                    disabled={disabled}
                  >
                    <span className="text-sm">
                      {isExpanded ? '▲ Collapse' : '▼ Expand'}
                    </span>
                  </button>
                )}
              </div>
              
              {/* Category-level slider (always visible when selected) */}
              {isSelected && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Category Sentiment Score: {category}
                  </label>
                  <div className="flex items-center space-x-3">
                    <span className="text-xs text-gray-500 w-6">-3</span>
                    <input
                      type="range"
                      min="-3"
                      max="3"
                      step="0.1"
                      value={currentCategoryScore}
                      onChange={(e) => {
                        const score = parseFloat(e.target.value);
                        // Update independent category score state
                        setCategorySentimentScores(prev => ({
                          ...prev,
                          [category]: score
                        }));
                        // Update all subcategories for this category
                        selectedSubcategories.forEach(subcategory => {
                          updateSentiment(category, subcategory, {
                            category_sentiment_score: score
                          });
                        });
                      }}
                      disabled={disabled}
                      className={`flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer ${
                        getSliderColor(currentCategoryScore)
                      }`}
                    />
                    <span className="text-xs text-gray-500 w-6">+3</span>
                    <input
                      type="number"
                      min="-3"
                      max="3"
                      step="0.1"
                      value={currentCategoryScore}
                      onChange={(e) => {
                        const score = parseFloat(e.target.value) || 0;
                        // Update independent category score state
                        setCategorySentimentScores(prev => ({
                          ...prev,
                          [category]: score
                        }));
                        // Update all subcategories for this category
                        selectedSubcategories.forEach(subcategory => {
                          updateSentiment(category, subcategory, {
                            category_sentiment_score: score
                          });
                        });
                      }}
                      disabled={disabled}
                      className="w-16 px-2 py-1 text-xs border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  {selectedSubcategories.length > 0 && (
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-gray-600">Current Score:</span>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getScoreColor(currentCategoryScore)}`}>
                        {currentCategoryScore.toFixed(1)}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Subcategories */}
            {isSelected && isExpanded && (
              <div className="p-4 bg-white space-y-4">
                {subcategories.map(subcategory => {
                  const key = `${category}-${subcategory}`;
                  const isSubcategorySelected = existingSentimentsMap.has(key);
                  const sentiment = existingSentimentsMap.get(key);

                  return (
                    <div key={subcategory} className="space-y-3 p-3 bg-gray-50 rounded-lg">
                      {/* Subcategory Header */}
                      <div className="flex items-center justify-between">
                        <label className="flex items-center space-x-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={isSubcategorySelected}
                            onChange={(e) => toggleSubcategory(category, subcategory, e.target.checked)}
                            disabled={disabled}
                            className="h-4 w-4 text-bloomin-blue focus:ring-bloomin-blue border-gray-300 rounded"
                          />
                          <span className="font-medium text-gray-800">
                            {subcategory}
                          </span>
                        </label>
                        {sentiment && (
                          <div className="flex space-x-2">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${getScoreColor(sentiment.subcategory_sentiment_score)}`}>
                              {sentiment.subcategory_sentiment_score.toFixed(1)}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Subcategory Sentiment Control */}
                      {isSubcategorySelected && sentiment && (
                        <div className="space-y-2 pl-6">
                          <label className="block text-sm font-medium text-gray-700">
                            Subcategory Sentiment: {subcategory}
                          </label>
                          <div className="flex items-center space-x-3">
                            <span className="text-xs text-gray-500 w-6">-1</span>
                            <input
                              type="range"
                              min="-1"
                              max="1"
                              step="0.1"
                              value={sentiment.subcategory_sentiment_score}
                              onChange={(e) => updateSentiment(category, subcategory, {
                                subcategory_sentiment_score: parseFloat(e.target.value)
                              })}
                              disabled={disabled}
                              className={`flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer ${getSliderColor(sentiment.subcategory_sentiment_score)}`}
                            />
                            <span className="text-xs text-gray-500 w-6">+1</span>
                            <input
                              type="number"
                              min="-1"
                              max="1"
                              step="0.1"
                              value={sentiment.subcategory_sentiment_score}
                              onChange={(e) => updateSentiment(category, subcategory, {
                                subcategory_sentiment_score: parseFloat(e.target.value) || 0
                              })}
                              disabled={disabled}
                              className="w-16 px-2 py-1 text-xs border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}

      {sentiments.length === 0 && (
        <div className="text-center py-8 text-gray-500 border-2 border-dashed border-gray-300 rounded-lg">
          <p className="text-lg">No categories selected</p>
          <p className="text-sm">Check categories above to start rating sentiment</p>
        </div>
      )}
    </div>
  );
};

export default UnifiedCategoryEditor;
