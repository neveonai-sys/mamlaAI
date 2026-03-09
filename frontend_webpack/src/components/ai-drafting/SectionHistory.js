// src/components/SectionHistory.js

import React, { useState, useEffect } from 'react';
import AxiosInstance from '../common/AxiosInstance';
import {
  Box,
  Typography,
  Snackbar,
  Alert,
  Paper,
  Tooltip,
  Fade,
} from '@mui/material';
import LoadingOverlay from '../common/LoadingOverlay';

function SectionHistory({ sessionId, sectionId }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [noHistory, setNoHistory] = useState(false);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const response = await AxiosInstance.get(`aidrafts/get_section_history`, {
          params: { session_id: sessionId, section_id: sectionId },
        });
        if (
          response.data.history &&
          Array.isArray(response.data.history) &&
          response.data.history.length > 0
        ) {
          setHistory(response.data.history);
          setNoHistory(false);
        } else {
          setHistory([]);
          setNoHistory(true);
        }
      } catch (error) {
        console.error('Error fetching section history:', error);
        setErrorMessage('Failed to fetch section history. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    if (sessionId && sectionId) {
      fetchHistory();
    }
  }, [sessionId, sectionId]);

  return (
    <Box>
      {/* Loading Overlay */}
      <LoadingOverlay open={loading} message="Fetching section history..." />

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

      {/* Section History Content */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="h6" gutterBottom>
          Section History
        </Typography>

        {noHistory ? (
          <Typography variant="body1" color="text.secondary">
            No history available for this section.
          </Typography>
        ) : (
          history.map((entry, index) => (
            <Fade in={true} key={entry.id || index}>
              <Paper
                sx={{
                  padding: 2,
                  mb: 2,
                  backgroundColor: '#fafafa',
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  '&:hover': {
                    transform: 'scale(1.02)',
                    boxShadow: 4,
                  },
                }}
                elevation={2}
                onClick={() => alert('Detailed view can be implemented here.')}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">
                    Version {index + 1}
                  </Typography>
                  <Typography variant="subtitle2" color="text.secondary">
                    {new Date(entry.timestamp).toLocaleString()}
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  sx={{ whiteSpace: 'pre-wrap', fontFamily: 'Roboto, sans-serif' }}
                >
                  {entry.content}
                </Typography>
              </Paper>
            </Fade>
          ))
        )}
      </Box>
    </Box>
  );
}

export default SectionHistory;
