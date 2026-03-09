import axios from 'axios';
import { applySecurityMiddleware } from '../../middleware/securityMiddleware';
import { secureLocalStorage, secureSessionStorage } from '../../utils/securityUtils';

// Create a basic axios instance
const getBaseURL = () => {
  if (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_BASE_URL) {
    return process.env.REACT_APP_API_BASE_URL;
  }
  return window.location.hostname === 'localhost' ? '/api/' : 'https://mamla.ai/api/';
};

const axiosInstance = axios.create({
  baseURL: getBaseURL(),
  withCredentials: true,
});

// Apply security middleware
applySecurityMiddleware(axiosInstance);

// Request interceptor to add auth token
axiosInstance.interceptors.request.use(
  (config) => {
    // Skip auth for test endpoints
    if (config.url && config.url.includes('/test/')) {
      return config;
    }
    
    // Get the token from whichever storage has it first
    const token = secureLocalStorage.getItem('authToken') || secureSessionStorage.getItem('authToken');
    
    // If token exists, add it to the headers; otherwise ensure we don't send stale header
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else if (config.headers && config.headers.Authorization) {
      delete config.headers.Authorization;
    }
    
    if (process.env.NODE_ENV === 'development' && config.method === 'get') {
      config.params = {
        ...config.params,
        _t: new Date().getTime(),
      };
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
export const setupResponseInterceptors = (navigate) => {
  axiosInstance.interceptors.response.use(
    (response) => {
      // Handle successful responses
      return response;
    },
    (error) => {
      // Handle errors
      if (error.response) {
        const { status } = error.response;
        
        // Handle 401 Unauthorized **only** if we actually sent an auth token
        if (status === 401) {
          const hasToken = secureLocalStorage.getItem('authToken') || secureSessionStorage.getItem('authToken');
          if (hasToken) {
            secureLocalStorage.removeItem('authToken');
            secureLocalStorage.removeItem('userData');
            if (window.location.pathname !== '/login') {
              navigate('/login', {
                state: { from: window.location.pathname },
                replace: true
              });
            }
          }
        }
        
        // Handle 403 Forbidden
        if (status === 403) {
          // Redirect to unauthorized page or show a message
          navigate('/unauthorized', { replace: true });
        }
        
        // Handle 500 Internal Server Error
        if (status >= 500) {
          // Log the error or show a generic error message
          console.error('Server error:', error);
        }
      } else if (error.request) {
        // The request was made but no response was received
        console.error('No response received:', error.request);
      } else {
        // Something happened in setting up the request
        console.error('Request error:', error.message);
      }
      
      return Promise.reject(error);
    }
  );
};

export default axiosInstance;
