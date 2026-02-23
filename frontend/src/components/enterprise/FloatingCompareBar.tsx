'use client';

import { useState, useEffect } from 'react';
import { Scale, X, ChevronUp } from 'lucide-react';

interface FloatingCompareBarProps {
  selectedCount: number;
  maxCount: number;
  onViewCompare: () => void;
  onClearAll: () => void;
}

export default function FloatingCompareBar({
  selectedCount,
  maxCount,
  onViewCompare,
  onClearAll
}: FloatingCompareBarProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);

  // Show bar when scrolled down and items selected
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      setIsVisible(scrollY > 300 && selectedCount > 0);
    };

    // Initial check
    handleScroll();
    
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [selectedCount]);

  // Always show if items selected, regardless of scroll
  useEffect(() => {
    if (selectedCount > 0) {
      setIsVisible(true);
      setIsMinimized(false);
    } else {
      setIsVisible(false);
    }
  }, [selectedCount]);

  if (!isVisible || selectedCount === 0) return null;

  // Minimized state - just a small FAB
  if (isMinimized) {
    return (
      <button
        onClick={() => setIsMinimized(false)}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all flex items-center justify-center group"
        data-testid="floating-compare-fab-minimized"
      >
        <Scale className="h-6 w-6" />
        <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
          {selectedCount}
        </span>
      </button>
    );
  }

  // Expanded state - full bar
  return (
    <div 
      className="fixed bottom-6 right-6 z-40 bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden animate-in slide-in-from-bottom-4 duration-300"
      data-testid="floating-compare-bar"
    >
      {/* Header */}
      <div className="bg-blue-600 text-white px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="h-4 w-4" />
          <span className="font-semibold text-sm">Compare Sellers</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1 hover:bg-blue-500 rounded transition-colors"
            aria-label="Minimize"
          >
            <ChevronUp className="h-4 w-4" />
          </button>
          <button
            onClick={onClearAll}
            className="p-1 hover:bg-blue-500 rounded transition-colors"
            aria-label="Clear all"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Progress indicator */}
        <div className="mb-3">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-gray-600">Selected</span>
            <span className="font-semibold text-gray-900">{selectedCount} / {maxCount}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${(selectedCount / maxCount) * 100}%` }}
            />
          </div>
        </div>

        {/* Slots visualization */}
        <div className="flex gap-2 mb-4">
          {Array.from({ length: maxCount }).map((_, idx) => (
            <div
              key={idx}
              className={`flex-1 h-8 rounded-lg border-2 border-dashed flex items-center justify-center transition-colors ${
                idx < selectedCount 
                  ? 'bg-blue-50 border-blue-300' 
                  : 'bg-gray-50 border-gray-200'
              }`}
            >
              {idx < selectedCount && (
                <span className="text-blue-600 text-xs font-medium">#{idx + 1}</span>
              )}
            </div>
          ))}
        </div>

        {/* Action button */}
        <button
          onClick={onViewCompare}
          disabled={selectedCount < 2}
          className={`w-full py-2.5 rounded-lg font-semibold text-sm transition-colors ${
            selectedCount >= 2
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          }`}
          data-testid="floating-compare-view-btn"
        >
          {selectedCount < 2 
            ? `Select ${2 - selectedCount} more to compare`
            : 'View Comparison'
          }
        </button>

        {selectedCount >= 2 && (
          <p className="text-xs text-gray-500 text-center mt-2">
            Compare specs, pricing & availability
          </p>
        )}
      </div>
    </div>
  );
}
