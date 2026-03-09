// src/components/LoadingOverlay.js

import React from 'react';
import { Backdrop, Typography, Fade } from '@mui/material';
import MemoryIcon from '@mui/icons-material/Memory';
import GavelIcon from '@mui/icons-material/Gavel';
import { keyframes } from '@mui/system';

// Define keyframes for rotation animation
const rotate = keyframes`
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
`;

function LoadingOverlay({ open, message }) {
  return (
    <Fade in={open}>
      <Backdrop
        sx={{
          color: '#fff',
          zIndex: (theme) => theme.zIndex.drawer + 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        open={open}
      >
        {/* AI Icon */}
        <MemoryIcon
          sx={{
            fontSize: 60,
            mb: 2,
            animation: `${rotate} 2s linear infinite`,
          }}
        />
        {/* Law Icon */}
        <GavelIcon
          sx={{
            fontSize: 60,
            mb: 2,
            animation: `${rotate} 3s linear infinite reverse`,
          }}
        />
        {message && (
          <Typography variant="h6" sx={{ mt: 1, textAlign: 'center' }}>
            {message}
          </Typography>
        )}
      </Backdrop>
    </Fade>
  );
}

export default LoadingOverlay;
