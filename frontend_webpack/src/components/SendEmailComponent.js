// src/components/SendEmailComponent.js

import React, { useState } from 'react';
import { Box, Button, TextField, Typography, Grid, Input, FormControl, Snackbar, Alert } from '@mui/material';
import { AttachFile } from '@mui/icons-material';
import AxiosInstance from './common/AxiosInstance';

const SendEmailComponent = () => {
  const [toEmails, setToEmails] = useState('');
  const [ccEmails, setCcEmails] = useState('');
  const [bccEmails, setBccEmails] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleFileChange = (e) => {
    setAttachments([...e.target.files]);
  };

  const handleSendEmail = async () => {
    const formData = new FormData();
    formData.append('to_emails', toEmails.split(','));
    formData.append('cc_emails', ccEmails.split(','));
    formData.append('bcc_emails', bccEmails.split(','));
    formData.append('subject', subject);
    formData.append('body', body);
    attachments.forEach((file) => {
      formData.append('attachments', file);
    });

    try {
      setLoading(true);
      await AxiosInstance.post('utils/send-email/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      showSnackbar('Email sent successfully.', 'success');
    } catch (error) {
      console.error('Error sending email:', error);
      showSnackbar(error.response?.data?.message || 'Failed to send email.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ padding: 2, maxWidth: 800, margin: 'auto' }}>
      <Typography variant="h5" gutterBottom>Send Email</Typography>
      <Grid container spacing={2}>
        {/* <Grid item xs={12}>
          <TextField
            fullWidth
            label="From"
            variant="outlined"
            value={fromEmail}
            onChange={(e) => setFromEmail(e.target.value)}
          />
        </Grid> */}
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="To"
            variant="outlined"
            value={toEmails}
            onChange={(e) => setToEmails(e.target.value)}
            helperText="Separate multiple emails with commas"
          />
        </Grid>
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="CC"
            variant="outlined"
            value={ccEmails}
            onChange={(e) => setCcEmails(e.target.value)}
            helperText="Separate multiple emails with commas"
          />
        </Grid>
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="BCC"
            variant="outlined"
            value={bccEmails}
            onChange={(e) => setBccEmails(e.target.value)}
            helperText="Separate multiple emails with commas"
          />
        </Grid>
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Subject"
            variant="outlined"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        </Grid>
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Body"
            variant="outlined"
            multiline
            rows={4}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </Grid>
        <Grid item xs={12}>
          <FormControl fullWidth>
            <Input
              type="file"
              inputProps={{ multiple: true }}
              onChange={handleFileChange}
              style={{ display: 'none' }}
              id="file-input"
            />
            <label htmlFor="file-input">
              <Button
                variant="contained"
                color="primary"
                component="span"
                startIcon={<AttachFile />}
              >
                Add Attachments
              </Button>
            </label>
            {attachments.length > 0 && (
              <Box>
                <Typography variant="subtitle1">Attachments:</Typography>
                {attachments.map((file, index) => (
                  <Typography key={index} variant="body2">
                    {file.name}
                  </Typography>
                ))}
              </Box>
            )}
          </FormControl>
        </Grid>
        <Grid item xs={12}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleSendEmail}
            disabled={loading}
          >
            {loading ? 'Sending…' : 'Send Email'}
          </Button>
        </Grid>
      </Grid>
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SendEmailComponent;
