/**
 * API Types and Error Handling
 */

export class ApiError extends Error {
  status: number;
  code?: string;
  
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }

  /**
   * Check if error is an authentication error
   */
  isAuthError(): boolean {
    return this.status === 401 || this.status === 403;
  }

  /**
   * Check if error is a network/timeout error
   */
  isNetworkError(): boolean {
    return this.status === 0 || this.status === 408;
  }

  /**
   * Get user-friendly error message
   */
  getUserMessage(): string {
    switch (this.status) {
      case 401:
        return 'Please sign in to continue';
      case 403:
        return 'You do not have permission to perform this action';
      case 404:
        return 'The requested resource was not found';
      case 408:
        return 'Request timed out. Please try again';
      case 429:
        return 'Too many requests. Please wait a moment';
      case 500:
      case 502:
      case 503:
        return 'Server error. Please try again later';
      case 0:
        return 'Network error. Please check your connection';
      default:
        return this.message || 'An error occurred';
    }
  }
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}
