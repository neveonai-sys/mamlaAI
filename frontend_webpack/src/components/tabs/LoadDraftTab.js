// src/components/tabs/LoadDraftTab.js

import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';

function LoadDraftTab(props) {
  const {
    draftRows,
    page, setPage,
    pageSize, setPageSize,
    rowCount,
    handleLoadSavedDraft,
    selectedDraftId, setSelectedDraftId,
    selectedDraft, setSelectedDraft,
    draftColumns,
    loading
  } = props;

  const handleRowClick = (params) => {
    setSelectedDraftId(params.id);
    const selected = draftRows.find((draft) => draft.id === params.id);
    setSelectedDraft(selected);
  };

  return (
    <Box>
      <Typography variant="h6">2. Load Your Saved Drafts</Typography>
      <Box sx={{ height: 600, width: '100%', mt: 2 }}>
        <DataGrid
          rows={draftRows}
          columns={draftColumns}
          page={page}
          pageSize={pageSize}
          rowsPerPageOptions={[5, 10, 20, 50]}
          rowCount={rowCount}
          pagination
          paginationMode="server"
          onPageChange={(newPage) => setPage(newPage)}
          onPageSizeChange={(newPageSize) => {
            setPageSize(newPageSize);
            setPage(0);
          }}
          onRowClick={handleRowClick}
          selectionModel={selectedDraftId ? [selectedDraftId] : []}
          disableSelectionOnClick
          getRowId={(row) => row.id}
          components={{ Toolbar: () => null }}
        />
      </Box>
      <Button
        variant="contained"
        color="primary"
        onClick={handleLoadSavedDraft}
        disabled={loading || !selectedDraft}
        sx={{ mt: 2 }}
      >
        Load Selected Draft
      </Button>
    </Box>
  );
}

export default LoadDraftTab;
