import axios from 'axios';
import React from 'react';

// Create a separate Axios instance for test drafts that doesn't include auth headers
const testDraftAxios = axios.create({
  baseURL: '/api/aidrafts/test/',  // Added leading slash for absolute path
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true  // Important for cookies if using session-based auth
});

// Add request interceptor for logging
testDraftAxios.interceptors.request.use(
  config => {
    console.log('[TestDraftService] Request:', {
      url: config.url,
      method: config.method,
      data: config.data,
      headers: config.headers
    });
    return config;
  },
  error => {
    console.error('[TestDraftService] Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for logging
testDraftAxios.interceptors.response.use(
  response => {
    console.log('[TestDraftService] Response:', {
      url: response.config.url,
      status: response.status,
      data: response.data
    });
    return response;
  },
  error => {
    console.error('[TestDraftService] Response Error:', {
      url: error.config?.url,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    return Promise.reject(error);
  }
);

/**
 * Service for interacting with the test draft API endpoints
 */
const testDraftService = {
  /**
   * Create a new test draft
   * @param {Object} data - Draft data including user_query, language, and state
   * @returns {Promise<Object>} - Response data with session_id and draft sections
   */
  createDraft: async (data) => {
    console.log('[TestDraftService] Creating test draft with data:', data);
    try {
      const response = await testDraftAxios.post('create/', data);
      console.log('[TestDraftService] Draft created successfully:', response.data);
      return response.data;
    } catch (error) {
      console.error('[TestDraftService] Error creating test draft:', {
        error: error.response?.data || error.message,
        status: error.response?.status,
        config: error.config
      });
      throw error.response?.data || { error: 'Failed to create test draft' };
    }
  },

  /**
   * Update a section in a test draft
   * @param {string} sessionId - The session ID of the draft
   * @param {string} sectionId - The ID of the section to update
   * @param {string} content - The new content for the section
   * @returns {Promise<Object>} - Response data with updated sections and remaining edits
   */
  updateSection: async (sessionId, sectionId, content) => {
    console.log(`[TestDraftService] Updating section ${sectionId} for session ${sessionId}`);
    try {
      const response = await testDraftAxios.post('update/', {
        session_id: sessionId,
        section_id: sectionId,
        content
      });
      console.log('[TestDraftService] Section updated successfully:', response.data);
      return response.data;
    } catch (error) {
      console.error('[TestDraftService] Error updating section:', {
        error: error.response?.data || error.message,
        status: error.response?.status
      });
      throw error.response?.data || { error: 'Failed to update section' };
    }
  },

  /**
   * Download a test draft as a document
   * @param {string} sessionId - The session ID of the draft
   * @param {string} format - The format to download (docx or pdf)
   * @returns {Promise<Object>} - Response data with download URL
   */
  downloadDraft: async (sessionId, format = 'docx') => {
    console.log(`[TestDraftService] Downloading draft ${sessionId} in ${format} format`);
    try {
      const response = await testDraftAxios.get('download/', {
        params: { session_id: sessionId, format },
      });
      console.log('[TestDraftService] Draft downloaded successfully:', response.data);
      return response.data;
    } catch (error) {
      console.error('[TestDraftService] Error downloading test draft:', {
        error: error.response?.data || error.message,
        status: error.response?.status
      });
      throw error.response?.data || { error: 'Failed to download draft' };
    }
  },

  /**
   * Get the status of a test draft session
   * @param {string} sessionId - The session ID of the draft
   * @returns {Promise<Object>} - Response data with session status
   */
  getDraftStatus: async (sessionId) => {
    console.log(`[TestDraftService] Getting status for session ${sessionId}`);
    try {
      const response = await testDraftAxios.get(`status/${sessionId}/`);
      console.log('[TestDraftService] Status retrieved successfully:', response.data);
      return response.data;
    } catch (error) {
      console.error('[TestDraftService] Error getting test draft status:', {
        error: error.response?.data || error.message,
        status: error.response?.status
      });
      throw error.response?.data || { error: 'Failed to get draft status' };
    }
  },

  /**
   * Handle document download by creating a temporary anchor element
   * @param {string} url - The download URL
   * @param {string} fileName - The name to save the file as
   */
  handleDownload: (url, fileName = 'document') => {
    console.log(`[TestDraftService] Handling download for ${fileName}`);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },
};

export default testDraftService;
