import { useState, useRef, useEffect } from 'react';

interface AspectSliderProps {
  aspect: string;
  value: number | null;
  enabled: boolean;
  onChange: (value: number | null, enabled: boolean) => void;
}

const AspectSlider = ({ aspect, value, enabled, onChange }: AspectSliderProps) => {
  const [inputValue, setInputValue] = useState<string>('');
  const [showInput, setShowInput] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (value !== null) {
      setInputValue(value.toFixed(1));
    }
  }, [value]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseFloat(e.target.value);
    onChange(newValue, enabled);
  };

  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newEnabled = e.target.checked;
    if (!newEnabled) {
      onChange(null, false);
    } else {
      onChange(value || 0, true);
    }
  };

  const handleInputSubmit = () => {
    const numValue = parseFloat(inputValue);
    if (!isNaN(numValue) && numValue >= -1 && numValue <= 1) {
      onChange(numValue, enabled);
    } else {
      // Reset to current value if invalid
      setInputValue(value?.toFixed(1) || '0.0');
    }
    setShowInput(false);
  };

  const handleInputKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleInputSubmit();
    } else if (e.key === 'Escape') {
      setInputValue(value?.toFixed(1) || '0.0');
      setShowInput(false);
    }
  };

  const increment = () => {
    const currentValue = value || 0;
    const newValue = Math.min(1, Math.round((currentValue + 0.1) * 10) / 10);
    onChange(newValue, enabled);
  };

  const decrement = () => {
    const currentValue = value || 0;
    const newValue = Math.max(-1, Math.round((currentValue - 0.1) * 10) / 10);
    onChange(newValue, enabled);
  };

  const getValueColor = (val: number | null) => {
    if (val === null) return 'text-gray-400';
    if (val > 0.3) return 'text-green-600';
    if (val < -0.3) return 'text-red-600';
    return 'text-yellow-600';
  };

  const getSliderColor = (val: number | null) => {
    if (val === null) return 'accent-gray-400';
    if (val > 0.3) return 'accent-green-500';
    if (val < -0.3) return 'accent-red-500';
    return 'accent-yellow-500';
  };

  return (
    <div className="flex items-center space-x-4 py-3 border-b border-gray-100 last:border-b-0">
      {/* Checkbox */}
      <input
        type="checkbox"
        checked={enabled}
        onChange={handleCheckboxChange}
        className="h-4 w-4 text-bloomin-red focus:ring-bloomin-red border-gray-300 rounded"
      />

      {/* Aspect Label */}
      <div className="w-32 text-sm font-medium text-gray-700">
        {aspect}
      </div>

      {/* Slider Controls */}
      <div className="flex-1 flex items-center space-x-3">
        {enabled ? (
          <>
            {/* Decrement Button */}
            <button
              onClick={decrement}
              className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-gray-600 font-bold transition-colors"
              disabled={!enabled || (value !== null && value <= -1)}
            >
              −
            </button>

            {/* Slider */}
            <div className="flex-1 relative">
              <input
                type="range"
                min="-1"
                max="1"
                step="0.1"
                value={value || 0}
                onChange={handleSliderChange}
                disabled={!enabled}
                className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer ${getSliderColor(value)} disabled:opacity-50`}
              />
              {/* Center mark */}
              <div className="absolute top-0 left-1/2 transform -translate-x-px w-0.5 h-2 bg-gray-400 pointer-events-none"></div>
            </div>

            {/* Increment Button */}
            <button
              onClick={increment}
              className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-gray-600 font-bold transition-colors"
              disabled={!enabled || (value !== null && value >= 1)}
            >
              +
            </button>

            {/* Value Display/Input */}
            <div className="w-16 text-right">
              {showInput ? (
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onBlur={handleInputSubmit}
                  onKeyDown={handleInputKeyPress}
                  className="w-full text-sm text-center border border-gray-300 rounded px-1 py-0.5 focus:ring-bloomin-red focus:border-bloomin-red"
                  autoFocus
                />
              ) : (
                <button
                  onClick={() => {
                    setShowInput(true);
                    setTimeout(() => inputRef.current?.focus(), 0);
                  }}
                  className={`text-sm font-medium hover:underline ${getValueColor(value)}`}
                >
                  {value !== null ? value.toFixed(1) : '0.0'}
                </button>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 text-sm text-gray-400 italic">
            Not relevant (uncheck to enable)
          </div>
        )}
      </div>
    </div>
  );
};

export default AspectSlider;
