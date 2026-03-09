import React, { Suspense, lazy } from 'react';
import { CircularProgress, Box } from '@mui/material';

// Lazy load the heavy DataGrid component
const DataGrid = lazy(() => import('@mui/x-data-grid').then(module => ({
  default: module.DataGrid
})));

const LoadingFallback = () => (
  <Box 
    display="flex" 
    justifyContent="center" 
    alignItems="center" 
    minHeight={200}
  >
    <CircularProgress />
  </Box>
);

const LazyDataGrid = (props) => {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <DataGrid {...props} />
    </Suspense>
  );
};

export default LazyDataGrid;
