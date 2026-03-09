// src/components/ai-drafting/DraftWithAI.js

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import InitialQueryComponent from './InitialQueryComponent';
import DraftViewerComponent from './DraftViewerComponent';
import { Box, Button, Typography, Tooltip, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions } from '@mui/material';
import AxiosInstance from '../common/AxiosInstance';
import { useSelector } from 'react-redux';

function DraftWithAI() {
  const [sessionId, setSessionId] = useState(null);
  const [loadedDraftSections, setLoadedDraftSections] = useState(null);
  const [filterData, setFilterData] = useState(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [loadedDraftName, setLoadedDraftName] = useState('');
  const [loadedSavedDraftId, setLoadedSavedDraftId] = useState('');

  // Get user type from Redux store
  const { user_type } = useSelector((state) => state.user);

  useEffect(() => {
    const fetchFilterData = async () => {
      try {
        const response = await AxiosInstance.get('users/filter_with_details/');
        setFilterData(response.data);
      } catch (error) {
        console.error('Error fetching filter data:', error);
      }
    };

    fetchFilterData();
  }, []);

  /**
   * Whenever a session is started or loaded, call this.
   * If the second argument (draftSections) is provided and non-empty,
   * we already have the sections. Otherwise, we automatically fetch them from the server.
   */
  const handleSessionStarted = useCallback(async (id, draftSections = null, draftName = '', savedDraftId = '') => {
    setSessionId(id);

    if (draftSections && draftSections.length > 0) {
      // If the function was called with the loaded sections (like loading a saved draft),
      // just store them
      setLoadedDraftSections(draftSections);
      setLoadedDraftName(draftName);
      setLoadedSavedDraftId(savedDraftId);
    } else {
      // Otherwise, automatically fetch the sections from the server
      try {
        const response = await AxiosInstance.get('aidrafts/get_draft_sections', {
          params: { session_id: id },
        });
        setLoadedDraftSections(response.data.draft_sections);
        setLoadedDraftName(draftName);
        setLoadedSavedDraftId(savedDraftId);
      } catch (error) {
        console.error('Error fetching draft sections:', error);
      }
    }
  }, []);

  // Reset flow to create a new draft
  const handleCreateNewDraft = useCallback(() => {
    setSessionId(null);
    setLoadedDraftSections(null);
  }, []);

  const handleOpenConfirmDialog = useCallback(() => {
    setConfirmDialogOpen(true);
  }, []);

  const handleCloseConfirmDialog = useCallback(() => {
    setConfirmDialogOpen(false);
  }, []);

  const handleConfirmCreateNewDraft = useCallback(() => {
    handleCreateNewDraft();
    handleCloseConfirmDialog();
  }, [handleCreateNewDraft, handleCloseConfirmDialog]);

  // Memoize components to prevent unnecessary re-renders
  const confirmDialog = useMemo(() => (
    <Dialog
      open={confirmDialogOpen}
      onClose={handleCloseConfirmDialog}
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-description"
    >
      <DialogTitle id="confirm-dialog-title">Confirm New Draft</DialogTitle>
      <DialogContent>
        <DialogContentText id="confirm-dialog-description">
          Are you sure you want to create a new draft? Any unsaved changes will be lost.
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCloseConfirmDialog} color="primary">
          Cancel
        </Button>
        <Button onClick={handleConfirmCreateNewDraft} color="primary" autoFocus>
          OK
        </Button>
      </DialogActions>
    </Dialog>
  ), [confirmDialogOpen, handleCloseConfirmDialog, handleConfirmCreateNewDraft]);

  return (
    <Box sx={{ padding: 3, fontFamily: 'Roboto, sans-serif' }}>
      <Typography variant="h4" gutterBottom align="center">
        Legal Drafting Assistant
      </Typography>

      {/* If a session is in progress, show a "Create New Draft" button to reset */}
      {sessionId && (
        <Tooltip title="Start creating a new legal draft session." arrow>
          <Button
            variant="contained"
            color="primary"
            onClick={handleOpenConfirmDialog}
            sx={{ mb: 2 }}
          >
            Back to draft selection
          </Button>
        </Tooltip>
      )}

      {confirmDialog}

      {/* If no session yet, show the initial query component */}
      {!sessionId && filterData && (
        <InitialQueryComponent 
          onSessionStarted={handleSessionStarted} 
          filterData={filterData}
          userType={user_type}
        />
      )}

      {/* If we have a session and loaded sections, show the draft viewer */}
      {sessionId && loadedDraftSections && (
        <DraftViewerComponent 
          sessionId={sessionId} 
          draftSections={loadedDraftSections} 
          existingDraftName={loadedDraftName} 
          existingSavedDraftId={loadedSavedDraftId} 
        />
      )}
    </Box>
  );
}

export default React.memo(DraftWithAI);
