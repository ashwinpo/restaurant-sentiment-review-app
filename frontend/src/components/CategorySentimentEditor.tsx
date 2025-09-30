import React, { useState } from 'react';
import type { CategorySentiment } from '../types/api';

interface CategorySentimentEditorProps {
  sentiments: CategorySentiment[];
  onChange: (sentiments: CategorySentiment[]) => void;
  disabled?: boolean;
}

const CategorySentimentEditor: React.FC<CategorySentimentEditorProps> = ({
  sentiments,
  onChange,
  disabled = false
}) => {
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  const updateSentiment = (index: number, updates: Partial<CategorySentiment>) => {
    const newSentiments = [...sentiments];
    newSentiments[index] = { ...newSentiments[index], ...updates };
    onChange(newSentiments);
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

  const formatScore = (score: number) => score.toFixed(1);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">
          Category Sentiment Editing ({sentiments.length})
        </h3>
        <div className="text-xs text-gray-500">
          Adjust category and subcategory sentiment scores (-2 to +2)
        </div>
      </div>

      {sentiments.map((sentiment, index) => (
        <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
          {/* Category Header */}
          <div 
            className="p-4 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
            onClick={() => setExpandedCategory(
              expandedCategory === `${index}` ? null : `${index}`
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="font-semibold text-gray-900">
                  {sentiment.category}
                </span>
                <span className="text-sm text-gray-600">
                  → {sentiment.subcategory}
                </span>
              </div>
              <div className="flex items-center space-x-3">
                <span className={`px-2 py-1 rounded text-sm font-medium ${getScoreColor(sentiment.category_sentiment_score)}`}>
                  Cat: {formatScore(sentiment.category_sentiment_score)}
                </span>
                <span className={`px-2 py-1 rounded text-sm font-medium ${getScoreColor(sentiment.subcategory_sentiment_score)}`}>
                  Sub: {formatScore(sentiment.subcategory_sentiment_score)}
                </span>
                <span className="text-gray-400 text-sm">
                  {expandedCategory === `${index}` ? '▲' : '▼'}
                </span>
              </div>
            </div>
          </div>

          {/* Expanded Editing Panel */}
          {expandedCategory === `${index}` && (
            <div className="p-4 bg-white border-t border-gray-200 space-y-4">
              {/* Category Sentiment Editing */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Category Sentiment: {sentiment.category}
                </label>
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-gray-500 w-8">-2</span>
                  <input
                    type="range"
                    min="-2"
                    max="2"
                    step="0.1"
                    value={sentiment.category_sentiment_score}
                    onChange={(e) => updateSentiment(index, {
                      category_sentiment_score: parseFloat(e.target.value)
                    })}
                    disabled={disabled}
                    className={`flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer ${getSliderColor(sentiment.category_sentiment_score)}`}
                  />
                  <span className="text-sm text-gray-500 w-8">+2</span>
                  <input
                    type="number"
                    min="-2"
                    max="2"
                    step="0.1"
                    value={sentiment.category_sentiment_score}
                    onChange={(e) => updateSentiment(index, {
                      category_sentiment_score: parseFloat(e.target.value) || 0
                    })}
                    disabled={disabled}
                    className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">Label:</span>
                  <select
                    value={sentiment.category_sentiment_label}
                    onChange={(e) => updateSentiment(index, {
                      category_sentiment_label: e.target.value
                    })}
                    disabled={disabled}
                    className="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="Positive">Positive</option>
                    <option value="Negative">Negative</option>
                    <option value="Neutral">Neutral</option>
                  </select>
                </div>
              </div>

              {/* Subcategory Sentiment Editing */}
              <div className="space-y-2 pt-4 border-t border-gray-100">
                <label className="block text-sm font-medium text-gray-700">
                  Subcategory Sentiment: {sentiment.subcategory}
                </label>
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-gray-500 w-8">-2</span>
                  <input
                    type="range"
                    min="-2"
                    max="2"
                    step="0.1"
                    value={sentiment.subcategory_sentiment_score}
                    onChange={(e) => updateSentiment(index, {
                      subcategory_sentiment_score: parseFloat(e.target.value)
                    })}
                    disabled={disabled}
                    className={`flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer ${getSliderColor(sentiment.subcategory_sentiment_score)}`}
                  />
                  <span className="text-sm text-gray-500 w-8">+2</span>
                  <input
                    type="number"
                    min="-2"
                    max="2"
                    step="0.1"
                    value={sentiment.subcategory_sentiment_score}
                    onChange={(e) => updateSentiment(index, {
                      subcategory_sentiment_score: parseFloat(e.target.value) || 0
                    })}
                    disabled={disabled}
                    className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">Label:</span>
                  <select
                    value={sentiment.subcategory_sentiment_label}
                    onChange={(e) => updateSentiment(index, {
                      subcategory_sentiment_label: e.target.value
                    })}
                    disabled={disabled}
                    className="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="Positive">Positive</option>
                    <option value="Negative">Negative</option>
                    <option value="Neutral">Neutral</option>
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}

      {sentiments.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No category sentiments available</p>
          <p className="text-sm">This review may be using the legacy aspect system</p>
        </div>
      )}
    </div>
  );
};

export default CategorySentimentEditor;
