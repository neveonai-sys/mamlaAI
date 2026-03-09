/**
 * Security Middleware
 * 
 * This middleware adds security headers and request/response transformations
 * to protect sensitive data in API calls.
 */

// List of sensitive endpoints that should be protected
const SENSITIVE_ENDPOINTS = [
  '/auth/',
  '/users/',
  '/profile/',
  '/billing/',
  '/api/'
];

// List of headers to remove from responses for security
const SENSITIVE_HEADERS = [
  'x-powered-by',
  'server',
  'x-aspnet-version',
  'x-aspnetmvc-version'
];

/**
 * Checks if the URL contains any sensitive endpoint
 */
const isSensitiveEndpoint = (url = '') => {
  if (!url) return false;
  return SENSITIVE_ENDPOINTS.some(endpoint => 
    url.toLowerCase().includes(endpoint.toLowerCase())
  );
};

/**
 * Removes sensitive headers from the response
 */
const removeSensitiveHeaders = (headers = {}) => {
  const cleanHeaders = { ...headers };
  SENSITIVE_HEADERS.forEach(header => {
    delete cleanHeaders[header];
  });
  return cleanHeaders;
};

/**
 * Security middleware for Axios
 */
export const securityMiddleware = (config) => {
  // Skip for non-sensitive endpoints
  if (!isSensitiveEndpoint(config.url)) {
    return config;
  }

  // Add security headers (only headers appropriate for requests)
  const securityHeaders = {};

  // Add CSRF token if available
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
  if (csrfToken) {
    securityHeaders['X-CSRF-Token'] = csrfToken;
  }

  // Add security headers to the request (only if we have any)
  if (Object.keys(securityHeaders).length > 0) {
    config.headers = {
      ...config.headers,
      ...securityHeaders
    };
  }

  // Add timestamp to prevent caching
  if (config.method === 'get') {
    config.params = {
      ...config.params,
      _: new Date().getTime()
    };
  }

  return config;
};

/**
 * Response interceptor to handle security-related response headers
 */
export const securityResponseInterceptor = (response) => {
  // Remove sensitive headers from the response
  if (response?.headers) {
    response.headers = removeSensitiveHeaders(response.headers);
  }
  
  // Handle any security-related response transformations here
  return response;
};

/**
 * Error interceptor for security-related error handling
 */
export const securityErrorInterceptor = (error) => {
  // Log security-related errors
  if (error.response) {
    const { status, config } = error.response;
    
    // Handle specific security-related status codes
    if (status === 401) {
      // Handle unauthorized access
      console.warn('Unauthorized access attempt:', config.url);
      // Redirect to login or handle as needed
    } else if (status === 403) {
      // Handle forbidden access
      console.warn('Forbidden access attempt:', config.url);
    } else if (status >= 500) {
      // Log server errors
      console.error('Server error on:', config.url, error.response.data);
    }
    
    // Remove sensitive data from error response
    if (error.response.data) {
      // Ensure sensitive data isn't leaked in error messages
      const sanitizedError = { ...error };
      if (sanitizedError.response?.data?.message?.includes('password')) {
        sanitizedError.response.data.message = 'Authentication failed. Please check your credentials.';
      }
      return Promise.reject(sanitizedError);
    }
  }
  
  return Promise.reject(error);
};

/**
 * Apply security middleware to an Axios instance
 */
export const applySecurityMiddleware = (axiosInstance) => {
  // Request interceptor
  axiosInstance.interceptors.request.use(
    securityMiddleware,
    error => Promise.reject(error)
  );
  
  // Response interceptor
  axiosInstance.interceptors.response.use(
    securityResponseInterceptor,
    securityErrorInterceptor
  );
  
  return axiosInstance;
};

export default {
  securityMiddleware,
  securityResponseInterceptor,
  securityErrorInterceptor,
  applySecurityMiddleware
};
