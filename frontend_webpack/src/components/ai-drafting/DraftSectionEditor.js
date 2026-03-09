// src/components/DraftSectionEditor.js

import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Tooltip,
  Fade,
  Paper,
} from '@mui/material';
import LoadingOverlay from '../common/LoadingOverlay';
import AxiosInstance from '../common/AxiosInstance';

function DraftSectionEditor({
  sessionId,
  section,
  onUpdate,
  onDelete,
  onShowHistory,
  aiSuggestionCount,
  MAX_AI_SUGGESTIONS,
  handleAiSuggestionMade,
}) {
  const [sectionName, setSectionName] = useState(section.section_name);
  const [content, setContent] = useState(section.content);
  const [isEditing, setIsEditing] = useState(false);
  const [suggestion, setSuggestion] = useState('');
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  // **New useEffect to synchronize local state with props**
  useEffect(() => {
    setSectionName(section.section_name);
    setContent(section.content);
  }, [section.section_name, section.content]);

  // Handle Save Section
  const handleSave = async () => {
    if (!sectionName.trim() || !content.trim()) {
      setErrorMessage('Section name and content cannot be empty.');
      return;
    }

    if (sectionName.trim().length < 3) {
      setErrorMessage('Section name must be at least 3 characters long.');
      return;
    }

    if (content.trim().length < 50) {
      setErrorMessage('Section content must be at least 50 characters long.');
      return;
    }

    setLoading(true);
    try {
      // Delegate API call to the parent via onUpdate
      await onUpdate(section.section_id, { section_name: sectionName, content });
      setIsEditing(false);
      setSuccessMessage('Section saved successfully.');
    } catch (error) {
      console.error('Error saving section:', error);
      setErrorMessage('Failed to save section. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle Delete Section
  const handleDelete = () => {
    // Delegate deletion to the parent via onDelete
    onDelete(section.section_id);
  };

  // Handle AI Suggestion
  const handleSuggest = async () => {
    if (!suggestion.trim()) {
      setErrorMessage('Suggestion cannot be empty.');
      return;
    }

    if (suggestion.trim().length < 10) {
      setErrorMessage('Suggestion must be at least 10 characters long.');
      return;
    }

    setLoading(true);
    try {
      const response = await AxiosInstance.post(`aidrafts/suggest_section`, {
        session_id: sessionId,
        section_id: section.section_id,
        suggestion,
      });
      const updatedContent = response.data.updated_content;
      const aiUpdateCount = response.data.ai_update_count;

      if (updatedContent) {
        setAiSuggestion(updatedContent);
        setSuggestion('');
        setSuccessMessage('AI suggestion generated successfully.');

        // Increment AI suggestion count in the parent
        handleAiSuggestionMade();
      } else {
        setErrorMessage('AI could not generate a suggestion. Please try again.');
      }
    } catch (error) {
      console.error('Error getting AI suggestion:', error);
      if (error.response && error.response.status === 400) {
        setErrorMessage('AI suggestion limit reached. Please go Premium for more suggestions.');
      } else {
        setErrorMessage('Failed to generate AI suggestion. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle Keeping AI Suggestion
  const handleKeepSuggestion = async () => {
    if (!aiSuggestion) return;

    setLoading(true);
    try {
      // Delegate API call to update the section with AI suggestion via onUpdate
      await onUpdate(section.section_id, {
        section_name: sectionName,
        content: aiSuggestion,
      });
      setAiSuggestion(null);
      setSuccessMessage('AI suggestion applied successfully.');
    } catch (error) {
      console.error('Error applying AI suggestion:', error);
      setErrorMessage('Failed to apply AI suggestion. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle Discarding AI Suggestion
  const handleDiscardSuggestion = () => {
    setAiSuggestion(null);
    setSuccessMessage('AI suggestion discarded.');
  };

  // Handle Confirm Delete Dialog
  const openConfirmDelete = () => {
    setConfirmDelete(true);
  };

  const closeConfirmDelete = () => {
    setConfirmDelete(false);
  };

  const confirmDeleteAction = () => {
    setConfirmDelete(false);
    handleDelete();
  };

  return (
    <Box>
      {/* Loading Overlay */}
      <LoadingOverlay open={loading} message="Processing your request..." />

      {/* Error Notification Snackbar */}
      <Snackbar
        open={Boolean(errorMessage)}
        autoHideDuration={6000}
        onClose={() => setErrorMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        TransitionComponent={Fade}
      >
        <Alert
          onClose={() => setErrorMessage('')}
          severity="error"
          sx={{ width: '100%' }}
        >
          {errorMessage}
        </Alert>
      </Snackbar>

      {/* Success Notification Snackbar */}
      <Snackbar
        open={Boolean(successMessage)}
        autoHideDuration={6000}
        onClose={() => setSuccessMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        TransitionComponent={Fade}
      >
        <Alert
          onClose={() => setSuccessMessage('')}
          severity="success"
          sx={{ width: '100%' }}
        >
          {successMessage}
        </Alert>
      </Snackbar>

      {/* Confirmation Dialog for Deleting Section */}
      <Dialog
        open={confirmDelete}
        onClose={closeConfirmDelete}
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
      >
        <DialogTitle id="delete-dialog-title">Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-dialog-description">
            Are you sure you want to delete this section? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeConfirmDelete}>Cancel</Button>
          <Button onClick={confirmDeleteAction} color="error" autoFocus>
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Section Name */}
      {isEditing ? (
        <Tooltip title="Enter a meaningful section name (minimum 3 characters).">
          <TextField
            label="Section Name"
            variant="outlined"
            fullWidth
            value={sectionName}
            onChange={(e) => setSectionName(e.target.value)}
            sx={{ mb: 2 }}
            helperText="Minimum 3 characters."
            error={sectionName.trim().length > 0 && sectionName.trim().length < 3}
          />
        </Tooltip>
      ) : (
        <Typography variant="h6" gutterBottom>
          {sectionName}
        </Typography>
      )}

      {/* Section Content */}
      {isEditing ? (
        <Tooltip title="Enter detailed content for the section (minimum 50 characters).">
          <TextField
            label="Content"
            variant="outlined"
            multiline
            rows={6}
            fullWidth
            value={content}
            onChange={(e) => setContent(e.target.value)}
            sx={{ mb: 2 }}
            helperText="Minimum 50 characters."
            error={content.trim().length > 0 && content.trim().length < 50}
          />
        </Tooltip>
      ) : (
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
          {content}
        </Typography>
      )}

      {/* Edit and Delete Buttons */}
      {isEditing ? (
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <Tooltip title="Save your changes to this section.">
            <Button variant="contained" color="primary" onClick={handleSave} disabled={loading}>
              Save Section
            </Button>
          </Tooltip>
          <Tooltip title="Cancel editing and revert changes.">
            <Button variant="outlined" onClick={() => setIsEditing(false)} disabled={loading}>
              Cancel
            </Button>
          </Tooltip>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <Tooltip title="Edit this section.">
            <Button variant="outlined" onClick={() => setIsEditing(true)} disabled={loading}>
              Edit Section
            </Button>
          </Tooltip>
          <Tooltip title="Delete this section.">
            <span> {/* Wrap disabled button with span */}
              <Button
                variant="outlined"
                color="error"
                onClick={openConfirmDelete}
                disabled={loading}
              >
                Delete Section
              </Button>
            </span>
          </Tooltip>
        </Box>
      )}

      {/* AI Suggestion Section */}
      <Box sx={{ mb: 2 }}>
        <Tooltip title="Provide suggestions to improve this section using AI.">
          <TextField
            label="Suggest changes to this section..."
            placeholder="e.g., Add clauses about confidentiality..."
            multiline
            rows={2}
            variant="outlined"
            fullWidth
            value={suggestion}
            onChange={(e) => setSuggestion(e.target.value)}
            disabled={loading || aiSuggestionCount >= MAX_AI_SUGGESTIONS}
            helperText="Minimum 10 characters."
            error={suggestion.trim().length > 0 && suggestion.trim().length < 10}
          />
        </Tooltip>
        <Tooltip title="Generate AI suggestions based on your input.">
          <span> {/* Wrap disabled button with span */}
            <Button
              variant="contained"
              color="secondary"
              onClick={handleSuggest}
              sx={{ mt: 1 }}
              disabled={
                loading ||
                !suggestion.trim() ||
                suggestion.trim().length < 10 ||
                aiSuggestionCount >= MAX_AI_SUGGESTIONS
              }
            >
              AI Suggest
            </Button>
          </span>
        </Tooltip>
      </Box>

      {/* Display AI Suggestion */}
      {aiSuggestion && (
        <Paper sx={{ padding: 2, backgroundColor: '#f0f8ff', mb: 2 }} elevation={3}>
          <Typography variant="subtitle1" gutterBottom>
            AI Suggestion:
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {aiSuggestion}
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
            <Tooltip title="Apply the AI-generated suggestion to this section.">
              <span> {/* Wrap disabled button with span */}
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleKeepSuggestion}
                  disabled={loading}
                >
                  Keep
                </Button>
              </span>
            </Tooltip>
            <Tooltip title="Discard the AI-generated suggestion.">
              <span> {/* Wrap disabled button with span */}
                <Button
                  variant="outlined"
                  color="secondary"
                  onClick={handleDiscardSuggestion}
                  disabled={loading}
                >
                  Discard
                </Button>
              </span>
            </Tooltip>
          </Box>
        </Paper>
      )}

      {/* Show History Button */}
      <Tooltip title="View the history of changes made to this section.">
        <Button variant="text" onClick={() => onShowHistory(section.section_id)} disabled={loading}>
          Show History
        </Button>
      </Tooltip>
    </Box>
  );
}

export default DraftSectionEditor;
