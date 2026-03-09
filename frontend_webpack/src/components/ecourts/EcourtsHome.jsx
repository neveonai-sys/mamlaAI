import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, TextField, InputAdornment, IconButton, Paper,
  Grid, Card, CardContent, CardActionArea, Tabs, Tab, Fade,
  Chip, Stack,
} from '@mui/material';
import {
  Search as SearchIcon,
  Gavel as GavelIcon,
  People as PeopleIcon,
  Person as PersonIcon,
  AccountBalance as CourtIcon,
  ListAlt as ListIcon,
  Description as OrderIcon,
  History as HistoryIcon,
} from '@mui/icons-material';

const CATEGORIES = [
  { key: 'general', label: 'Cases' },
  { key: 'advocate', label: 'Lawyers' },
  { key: 'litigant', label: 'Litigants' },
  { key: 'judge', label: 'Judges' },
  { key: 'causelist', label: 'Cause Lists' },
];

const FEATURES = [
  { icon: <GavelIcon />, title: 'Case Records', desc: 'Search across all Indian court case records with full details, hearing history, and orders.', path: '/ecourts/search' },
  { icon: <PeopleIcon />, title: 'Lawyer Directory', desc: 'Find advocates by name and view their case history across all courts.', path: '/ecourts/lawyers' },
  { icon: <PersonIcon />, title: 'Litigant Search', desc: 'Search cases by party name — petitioners, respondents, and litigants.', path: '/ecourts/litigants' },
  { icon: <CourtIcon />, title: 'Court Directory', desc: 'Browse the complete court hierarchy — States, Districts, Complexes, and Courts.', path: '/ecourts/causelist' },
  { icon: <ListIcon />, title: 'Cause Lists', desc: 'Real-time access to daily cause lists. Filter by court, judge, or party name.', path: '/ecourts/causelist' },
  { icon: <OrderIcon />, title: 'Court Orders', desc: 'Access and download certified true-copy court orders and judgments.', path: '/ecourts/search' },
];

const CYCLING_WORDS = ['Cases', 'Lawyers', 'Litigants', 'Judges', 'Cause Lists'];

const SECTION_ROUTES = {
  cases: '/ecourts/search',
  lawyers: '/ecourts/lawyers',
  litigants: '/ecourts/litigants',
  causelist: '/ecourts/causelist',
};

const SECTION_LABELS = {
  cases: 'Case',
  lawyers: 'Lawyer',
  litigants: 'Litigant',
  causelist: 'Cause List',
};

function loadAllRecent() {
  try {
    const all = JSON.parse(localStorage.getItem('ecourts_recent_searches')) || {};
    const merged = [];
    for (const [section, items] of Object.entries(all)) {
      for (const item of items) {
        merged.push({ ...item, section });
      }
    }
    merged.sort((a, b) => b.timestamp - a.timestamp);
    return merged.slice(0, 6);
  } catch {
    return [];
  }
}

export default function EcourtsHome() {
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [query, setQuery] = useState('');
  const [wordIdx, setWordIdx] = useState(0);
  const [fadeIn, setFadeIn] = useState(true);
  const allRecent = useMemo(loadAllRecent, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setFadeIn(false);
      setTimeout(() => {
        setWordIdx((prev) => (prev + 1) % CYCLING_WORDS.length);
        setFadeIn(true);
      }, 400);
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  const handleSearch = useCallback(() => {
    if (!query.trim()) return;
    const cat = CATEGORIES[tab];
    if (cat.key === 'causelist') {
      navigate(`/ecourts/causelist?q=${encodeURIComponent(query)}`);
    } else if (cat.key === 'advocate') {
      navigate(`/ecourts/lawyers?q=${encodeURIComponent(query)}`);
    } else if (cat.key === 'litigant') {
      navigate(`/ecourts/litigants?q=${encodeURIComponent(query)}`);
    } else {
      navigate(`/ecourts/search?q=${encodeURIComponent(query)}&type=${cat.key}`);
    }
  }, [query, tab, navigate]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 2, md: 3 }, py: 4 }}>
      {/* Hero */}
      <Box sx={{ textAlign: 'center', mb: 5 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary', mb: 1 }}>
          Search{' '}
          <Fade in={fadeIn} timeout={400}>
            <Box component="span" sx={{ color: 'primary.main', display: 'inline' }}>
              {CYCLING_WORDS[wordIdx]}
            </Box>
          </Fade>
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Instant search across all Indian courts — cases, lawyers, litigants, judges & cause lists.
        </Typography>

        {/* Category tabs */}
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
          <Tabs
            value={tab}
            onChange={(_, v) => setTab(v)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              '& .MuiTab-root': { textTransform: 'none', fontWeight: 500, minWidth: 90 },
            }}
          >
            {CATEGORIES.map((c) => (
              <Tab key={c.key} label={c.label} />
            ))}
          </Tabs>
        </Box>

        {/* Search bar */}
        <Box sx={{ maxWidth: 720, mx: 'auto' }}>
          <Paper
            elevation={3}
            sx={{ display: 'flex', alignItems: 'center', borderRadius: 2, overflow: 'hidden' }}
          >
            <TextField
              fullWidth
              placeholder={`Search ${CATEGORIES[tab].label.toLowerCase()}...`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  '& fieldset': { border: 'none' },
                },
              }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={handleSearch}
                      sx={{ bgcolor: 'primary.main', color: 'white', borderRadius: 1, mr: 0.5,
                            '&:hover': { bgcolor: 'primary.dark' } }}
                    >
                      <SearchIcon />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
          </Paper>
        </Box>

        {allRecent.length > 0 && (
          <Box sx={{ maxWidth: 720, mx: 'auto', mt: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.75, mb: 1 }}>
              <HistoryIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                Recent Searches
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap justifyContent="center">
              {allRecent.map((item) => (
                <Chip
                  key={`${item.section}-${item.query}`}
                  label={`${item.query}`}
                  icon={<HistoryIcon sx={{ fontSize: '16px !important' }} />}
                  deleteIcon={
                    <Typography variant="caption" sx={{ fontSize: '0.65rem', opacity: 0.6, ml: 0.5 }}>
                      {SECTION_LABELS[item.section] || item.section}
                    </Typography>
                  }
                  onDelete={() => {}}
                  onClick={() => {
                    const route = SECTION_ROUTES[item.section] || '/ecourts/search';
                    navigate(`${route}?q=${encodeURIComponent(item.query)}`);
                  }}
                  variant="outlined"
                  size="small"
                  sx={{
                    borderRadius: '16px',
                    cursor: 'pointer',
                    '& .MuiChip-deleteIcon': { pointerEvents: 'none' },
                    '&:hover': { bgcolor: 'primary.50', borderColor: 'primary.main' },
                  }}
                />
              ))}
            </Stack>
          </Box>
        )}
      </Box>

      {/* Feature cards */}
      <Typography variant="h5" sx={{ fontWeight: 600, mb: 3, textAlign: 'center' }}>
        Everything Legal, In One Place
      </Typography>

      <Grid container spacing={3}>
        {FEATURES.map((f) => (
          <Grid item xs={12} sm={6} md={4} key={f.title}>
            <Card
              elevation={0}
              sx={{
                border: '1px solid', borderColor: 'divider', borderRadius: 2,
                height: '100%', transition: 'box-shadow 0.2s',
                '&:hover': { boxShadow: 4 },
              }}
            >
              <CardActionArea onClick={() => navigate(f.path)} sx={{ height: '100%' }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{
                    width: 48, height: 48, borderRadius: 2, bgcolor: 'primary.main',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: 'white', mb: 2,
                  }}>
                    {f.icon}
                  </Box>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                    {f.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {f.desc}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
