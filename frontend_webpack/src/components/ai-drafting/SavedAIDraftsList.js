import React, { useState, useEffect } from 'react';
import {
  List,
  ListItem,
  ListItemText,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Snackbar,
  Alert,
} from '@mui/material';
import AxiosInstance from '../common/AxiosInstance';

function SavedDraftsList({ sessionId, onLoadDraft }) {
  const [savedDrafts, setSavedDrafts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [draftToDelete, setDraftToDelete] = useState(null);

  useEffect(() => {
    const fetchSavedDrafts = async () => {
      setLoading(true);
      try {
        const response = await AxiosInstance.get('aidrafts/get_saved_drafts', {
          params: { session_id: sessionId },
        });
        setSavedDrafts(response.data.saved_drafts);
      } catch (error) {
        console.error('Error fetching saved drafts:', error);
        setErrorMessage('Failed to fetch saved drafts.');
      } finally {
        setLoading(false);
      }
    };

    if (sessionId) {
      fetchSavedDrafts();
    }
  }, [sessionId]);

  const handleLoadDraft = (draft) => {
    onLoadDraft(draft.sections);
    setSuccessMessage(`Draft "${draft.draft_name}" loaded successfully.`);
  };

  const handleDeleteDraft = (draft) => {
    setDraftToDelete(draft);
    setConfirmDelete(true);
  };

  const confirmDeleteAction = async () => {
    if (!draftToDelete) return;
    try {
      // Implement delete_draft endpoint similarly to save_draft
      const response = await AxiosInstance.post('aidrafts/delete_saved_draft', {
        session_id: sessionId,
        draft_id: draftToDelete.draft_id,
      });

      if (response.status === 200) {
        setSuccessMessage(`Draft "${draftToDelete.draft_name}" deleted successfully.`);
        setSavedDrafts((prevDrafts) =>
          prevDrafts.filter((d) => d.draft_id !== draftToDelete.draft_id)
        );
      } else {
        setErrorMessage('Failed to delete draft.');
      }
    } catch (error) {
      console.error('Error deleting draft:', error);
      setErrorMessage('Failed to delete draft.');
    } finally {
      setConfirmDelete(false);
      setDraftToDelete(null);
    }
  };

  const cancelDeleteAction = () => {
    setConfirmDelete(false);
    setDraftToDelete(null);
  };

  return (
    <div>
      <List>
        {savedDrafts.map((draft) => (
          <ListItem key={draft.draft_id} secondaryAction={
            <>
              <Button onClick={() => handleLoadDraft(draft)} variant="outlined" color="primary" sx={{ mr: 1 }}>
                Load
              </Button>
              <Button onClick={() => handleDeleteDraft(draft)} variant="outlined" color="error">
                Delete
              </Button>
            </>
          }>
            <ListItemText
              primary={draft.draft_name}
              secondary={`Saved on: ${new Date(draft.saved_at).toLocaleString()}`}
            />
          </ListItem>
        ))}
      </List>

      {/* Confirmation Dialog for Deleting Draft */}
      <Dialog
        open={confirmDelete}
        onClose={cancelDeleteAction}
        aria-labelledby="delete-draft-dialog-title"
        aria-describedby="delete-draft-dialog-description"
      >
        <DialogTitle id="delete-draft-dialog-title">Delete Draft</DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-draft-dialog-description">
            Are you sure you want to delete the draft "{draftToDelete?.draft_name}"? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelDeleteAction}>Cancel</Button>
          <Button onClick={confirmDeleteAction} color="error" autoFocus>
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar
        open={Boolean(successMessage)}
        autoHideDuration={6000}
        onClose={() => setSuccessMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={() => setSuccessMessage('')} severity="success" sx={{ width: '100%' }}>
          {successMessage}
        </Alert>
      </Snackbar>

      {/* Error Snackbar */}
      <Snackbar
        open={Boolean(errorMessage)}
        autoHideDuration={6000}
        onClose={() => setErrorMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={() => setErrorMessage('')} severity="error" sx={{ width: '100%' }}>
          {errorMessage}
        </Alert>
      </Snackbar>
    </div>
  );
}

export default SavedDraftsList;
