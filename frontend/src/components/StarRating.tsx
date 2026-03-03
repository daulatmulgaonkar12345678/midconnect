'use client';

import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StarRatingProps {
  rating: number;
  maxRating?: number;
  size?: 'sm' | 'md' | 'lg';
  interactive?: boolean;
  onChange?: (rating: number) => void;
  showValue?: boolean;
  className?: string;
}

/**
 * StarRating Component
 * 
 * Displays star ratings with optional interactivity.
 * 
 * @param rating - Current rating value (0-5)
 * @param maxRating - Maximum rating (default 5)
 * @param size - Star size: sm, md, lg
 * @param interactive - Whether user can click to change rating
 * @param onChange - Callback when rating changes (interactive mode)
 * @param showValue - Show numeric value next to stars
 */
export default function StarRating({
  rating,
  maxRating = 5,
  size = 'md',
  interactive = false,
  onChange,
  showValue = false,
  className
}: StarRatingProps) {
  const sizeClasses = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5'
  };

  const handleClick = (value: number) => {
    if (interactive && onChange) {
      onChange(value);
    }
  };

  return (
    <div className={cn('flex items-center gap-0.5', className)}>
      {[...Array(maxRating)].map((_, index) => {
        const starValue = index + 1;
        const isFilled = starValue <= rating;
        const isPartial = !isFilled && starValue - rating < 1 && rating > index;
        
        return (
          <button
            key={index}
            type="button"
            onClick={() => handleClick(starValue)}
            disabled={!interactive}
            className={cn(
              'focus:outline-none transition-colors',
              interactive && 'hover:scale-110 cursor-pointer',
              !interactive && 'cursor-default'
            )}
            aria-label={`${starValue} star${starValue > 1 ? 's' : ''}`}
          >
            <Star
              className={cn(
                sizeClasses[size],
                isFilled 
                  ? 'fill-yellow-400 text-yellow-400' 
                  : isPartial
                    ? 'fill-yellow-200 text-yellow-400'
                    : 'fill-gray-200 text-gray-300'
              )}
            />
          </button>
        );
      })}
      
      {showValue && (
        <span className={cn(
          'ml-1 font-medium text-gray-700',
          size === 'sm' && 'text-xs',
          size === 'md' && 'text-sm',
          size === 'lg' && 'text-base'
        )}>
          {rating > 0 ? rating.toFixed(1) : '-'}
        </span>
      )}
    </div>
  );
}

/**
 * Compact star display for cards
 */
export function StarRatingBadge({ 
  rating, 
  totalReviews,
  className 
}: { 
  rating: number; 
  totalReviews: number;
  className?: string;
}) {
  if (totalReviews === 0) {
    return (
      <span className={cn(
        'text-xs text-gray-400 flex items-center gap-1',
        className
      )}>
        <Star className="h-3 w-3 fill-gray-200 text-gray-300" />
        No reviews yet
      </span>
    );
  }

  return (
    <span className={cn(
      'flex items-center gap-1 text-sm',
      className
    )}>
      <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
      <span className="font-medium text-gray-800">{rating.toFixed(1)}</span>
      <span className="text-gray-400">({totalReviews})</span>
    </span>
  );
}
