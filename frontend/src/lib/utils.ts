/**
 * Simple utility function to merge CSS class names
 * Filters out falsy values and joins with space separator
 */
export function cn(...inputs: (string | undefined | null | false)[]): string {
  return inputs.filter(Boolean).join(' ');
}
