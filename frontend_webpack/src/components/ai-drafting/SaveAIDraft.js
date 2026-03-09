import React, { useState } from 'react';
import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  Snackbar,
  Alert,
} from '@mui/material';
import AxiosInstance from '../common/AxiosInstance';

function SaveDraft({ sessionId, draftSections, draftFor = {}, existingDraftName = '', existingSavedDraftId = '' }) {
  const [open, setOpen] = useState(false);
  const [draftName, setDraftName] = useState(existingDraftName);
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setDraftName('');
  };

  const handleSave = async () => {
    if (!draftName.trim()) {
      setErrorMessage('Draft name cannot be empty.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        session_id: sessionId,
        draft_name: draftName.trim(),
        draft_sections: draftSections,
        draft_for: draftFor, 
      };
      if (existingSavedDraftId) {
        payload.draft_id = existingSavedDraftId; // let the backend know which entry to update
      }

      const response = await AxiosInstance.post('aidrafts/save_draft', payload);

      if (response.status === 200) {
        setSuccessMessage('Draft saved successfully.');
        handleClose();
      } else {
        setErrorMessage('Failed to save draft.');
      }
    } catch (error) {
      console.error('Error saving draft:', error);
      const errMsg = error.response?.data?.error || 'Failed to save draft.';
      setErrorMessage(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>         
      <Button variant="outlined" color="primary" onClick={handleClickOpen}>
        {draftName ? 'Rename / Save Draft' : 'Save Draft'}
      </Button>
      <Dialog open={open} onClose={handleClose}>
        <DialogTitle>Save Draft</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Enter a name for your draft. You can save your progress and continue later.
          </DialogContentText>
          <TextField
            autoFocus
            margin="dense"
            label="Draft Name"
            type="text"
            fullWidth
            variant="standard"
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={loading}>
            {loading ? 'Saving...' : 'Save'}
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

export default SaveDraft;
