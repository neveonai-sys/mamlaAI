import React from 'react';
import {
  Box, Typography, List, ListItemButton, ListItemText, Chip, Divider, Paper,
} from '@mui/material';

/**
 * Faceted filter sidebar.
 * `facets` = { caseType: { values: { CIVIL: 85, ... }, hasMore }, caseStatus: { ... } }
 * `activeFilters` = { caseType: "CIVIL", caseStatus: "PENDING" }
 * `onFilterChange(facetKey, value)` toggles a filter.
 */
export default function FacetSidebar({ facets = {}, activeFilters = {}, onFilterChange, totalHits }) {
  if (!facets || Object.keys(facets).length === 0) return null;

  const labelMap = {
    caseType: 'Case Type',
    case_type: 'Case Type',
    caseStatus: 'Case Status',
    case_status: 'Case Status',
    courtCode: 'Court',
    court_code: 'Court',
    STATECODE: 'State',
    stateCode: 'State',
    state_code: 'State',
    state: 'State',
    DISTRICTCODE: 'District',
    districtCode: 'District',
    district_code: 'District',
    district: 'District',
    judicialSection: 'Judicial Section',
    judicial_section: 'Judicial Section',
  };

  return (
    <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        Advanced
      </Typography>

      {totalHits != null && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {totalHits.toLocaleString()} results
        </Typography>
      )}

      {Object.entries(facets).map(([key, facet]) => {
        const values = facet?.values || {};
        if (Object.keys(values).length === 0) return null;

        const labels = facet?.labels || {};
        const sorted = Object.entries(values).sort((a, b) => b[1] - a[1]);
        const activeVal = activeFilters[key];

        return (
          <Box key={key} sx={{ mb: 2 }}>
            <Divider sx={{ mb: 1 }} />
            <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase', color: 'text.secondary' }}>
              {labelMap[key] || key}
            </Typography>
            <List dense disablePadding sx={{ mt: 0.5 }}>
              {sorted.slice(0, 12).map(([val, count]) => (
                <ListItemButton
                  key={val}
                  selected={activeVal === val}
                  onClick={() => onFilterChange(key, activeVal === val ? null : val)}
                  sx={{ borderRadius: 1, py: 0.25, px: 1 }}
                >
                  <ListItemText
                    primary={labels[val] || val}
                    primaryTypographyProps={{ variant: 'body2', noWrap: true }}
                  />
                  <Chip label={count.toLocaleString()} size="small" variant="outlined" sx={{ ml: 1, height: 20 }} />
                </ListItemButton>
              ))}
            </List>
          </Box>
        );
      })}
    </Paper>
  );
}
