import React from 'react';
import { Box, Button, Typography } from '@mui/material';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '60vh',
            p: 3,
            textAlign: 'center',
          }}
        >
          <Typography variant="h5" gutterBottom>
            Something went wrong
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            We’re sorry. You can try refreshing the page or go back to home.
          </Typography>
          <Button variant="contained" onClick={this.handleRetry}>
            Try again
          </Button>
          <Button sx={{ mt: 1 }} onClick={() => window.location.assign('/')}>
            Go to home
          </Button>
        </Box>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
