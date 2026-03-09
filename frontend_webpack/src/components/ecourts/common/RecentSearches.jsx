import React from 'react';
import { Box, Typography, Chip, Stack, IconButton, Tooltip } from '@mui/material';
import { History as HistoryIcon, Close as CloseIcon } from '@mui/icons-material';

export default function RecentSearches({ recent = [], onSelect, onClear }) {
  if (recent.length === 0) return null;

  return (
    <Box sx={{ mb: 2.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <HistoryIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
            Recent Searches
          </Typography>
        </Box>
        {onClear && (
          <Tooltip title="Clear recent searches">
            <IconButton size="small" onClick={onClear} sx={{ color: 'text.secondary' }}>
              <CloseIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        )}
      </Box>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {recent.map((item) => (
          <Chip
            key={item.query}
            label={item.query}
            icon={<HistoryIcon sx={{ fontSize: '16px !important' }} />}
            onClick={() => onSelect(item.query, item.meta)}
            variant="outlined"
            size="small"
            sx={{
              borderRadius: '16px',
              cursor: 'pointer',
              '&:hover': { bgcolor: 'primary.50', borderColor: 'primary.main' },
            }}
          />
        ))}
      </Stack>
    </Box>
  );
}
