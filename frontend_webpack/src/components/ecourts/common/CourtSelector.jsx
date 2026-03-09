import React from 'react';
import {
  Grid, Card, CardActionArea, CardContent, Box, Typography, Chip,
  CircularProgress,
} from '@mui/material';
import {
  LocationOn as LocationIcon,
  AccountBalance as CourtIcon,
} from '@mui/icons-material';

/**
 * Generic grid selector for states / districts / complexes / courts.
 * `items` = [{ code, name, ...extra }]
 * `onSelect(item)` called when user clicks an item.
 */
export default function CourtSelector({ items = [], loading, onSelect, label, icon }) {
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (items.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 2 }}>
        No {label || 'items'} found.
      </Typography>
    );
  }

  return (
    <Grid container spacing={2}>
      {items.map((item) => (
        <Grid item xs={12} sm={6} md={4} key={item.code || item.name}>
          <Card
            elevation={0}
            sx={{
              border: '1px solid', borderColor: 'divider', borderRadius: 2,
              '&:hover': { boxShadow: 3, borderColor: 'primary.light' },
              transition: 'all 0.2s',
            }}
          >
            <CardActionArea onClick={() => onSelect(item)}>
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1.5, px: 2 }}>
                <Box sx={{
                  width: 36, height: 36, borderRadius: '50%', bgcolor: 'primary.main',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  {icon || <LocationIcon sx={{ color: 'white', fontSize: 18 }} />}
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                    {item.name}
                  </Typography>
                  {item.code && (
                    <Typography variant="caption" color="text.secondary">
                      Code: {item.code}
                    </Typography>
                  )}
                  {item.judge_name && (
                    <Typography variant="caption" color="text.secondary" display="block">
                      {item.judge_name}
                    </Typography>
                  )}
                </Box>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
