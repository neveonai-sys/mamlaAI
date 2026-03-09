import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, CardActionArea, CardContent, Box, Typography, Chip, Stack,
} from '@mui/material';
import { OpenInNew as OpenIcon } from '@mui/icons-material';

const STATUS_COLORS = {
  PENDING: 'warning',
  DISPOSED: 'success',
  TRANSFERRED: 'info',
  WITHDRAWN: 'default',
};

export default function CaseCard({ caseData }) {
  const navigate = useNavigate();
  const {
    cnr, case_title, case_type, case_status, judges = [],
    petitioner_advocates = [], respondent_advocates = [],
    court_name, court_code, state_name, district_name,
    filing_date, next_hearing_date,
    acts_and_sections,
  } = caseData;

  const statusColor = STATUS_COLORS[case_status] || 'default';

  return (
    <Card
      elevation={0}
      sx={{
        border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 2,
        '&:hover': { boxShadow: 3, borderColor: 'primary.light' },
        transition: 'all 0.2s',
      }}
    >
      <CardActionArea onClick={() => navigate(`/ecourts/case/${cnr}`)}>
        <CardContent sx={{ p: 2.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }} noWrap={false}>
                {case_title || cnr}
              </Typography>

              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
                {case_status && (
                  <Chip label={case_status} size="small" color={statusColor} variant="outlined" />
                )}
                {case_type && <Chip label={case_type} size="small" variant="outlined" />}
              </Stack>

              <Stack spacing={0.5}>
                {judges.length > 0 && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>Judge:</strong> {judges.join(', ')}
                  </Typography>
                )}
                {(court_name || court_code) && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>Court:</strong> {court_name || court_code}
                    {state_name && district_name ? ` — ${district_name}, ${state_name}` :
                     state_name ? ` — ${state_name}` : ''}
                  </Typography>
                )}
                {(petitioner_advocates.length > 0 || respondent_advocates.length > 0) && (
                  <Typography variant="body2" color="text.secondary">
                    {petitioner_advocates.length > 0 && (
                      <><strong>Petitioner Adv:</strong> {petitioner_advocates.join(', ')}  </>
                    )}
                    {respondent_advocates.length > 0 && (
                      <><strong>Respondent Adv:</strong> {respondent_advocates.join(', ')}</>
                    )}
                  </Typography>
                )}
                {acts_and_sections && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>Acts & Sections:</strong>{' '}
                    {Array.isArray(acts_and_sections) ? acts_and_sections.join(', ') : acts_and_sections}
                  </Typography>
                )}
              </Stack>
            </Box>

            <Box sx={{ textAlign: 'right', ml: 2, flexShrink: 0 }}>
              {filing_date && (
                <Typography variant="caption" color="text.secondary" display="block">
                  Filed: {filing_date}
                </Typography>
              )}
              {next_hearing_date && (
                <Typography variant="caption" color="primary" display="block" sx={{ fontWeight: 600 }}>
                  Next: {next_hearing_date}
                </Typography>
              )}
              <Box sx={{ mt: 0.5, color: 'action.active', display: 'flex', pointerEvents: 'none' }}>
                <OpenIcon fontSize="small" />
              </Box>
            </Box>
          </Box>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}
