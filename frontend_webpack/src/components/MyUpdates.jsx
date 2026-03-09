import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  TextField
} from '@mui/material';

import LoadingOverlay from './common/LoadingOverlay';
import AxiosInstance from './common/AxiosInstance';

/**
 * This page is for Paralegals to manage "My Updates":
 * 1) They can subscribe to courts (max 3).
 * 2) Filter their updates by date range or a single court.
 * 3) See a table of *their own* updates only.
 */
function MyUpdates() {
  const [loading, setLoading] = useState(false);

  // For states/districts/courts - same pattern as "Today's Updates"
  const [stateList, setStateList] = useState([]);
  const [districtList, setDistrictList] = useState([]);
  const [courtList, setCourtList] = useState([]);

  // Selections
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedCourt, setSelectedCourt] = useState('');

  // Subscribed courts (for the paralegal) - max 3
  const [subscribedCourts, setSubscribedCourts] = useState([]);

  // For filtering updates
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [filterCourt, setFilterCourt] = useState('');

  // Fetched updates
  const [myUpdates, setMyUpdates] = useState([]);

  /**
   * On mount, fetch states + paralegal subscriptions
   */
  useEffect(() => {
    fetchStates();
    fetchParalegalSubscriptions();
  }, []);

  /**
   * Get list of states
   */
  const fetchStates = async () => {
    setLoading(true);
    try {
      const res = await AxiosInstance.get('users/get-states/');
      setStateList(res.data.states || []);
    } catch (error) {
      console.error('Error fetching states:', error);
    }
    setLoading(false);
  };

  /**
   * Get paralegal's subscribed courts (max 3)
   */
  const fetchParalegalSubscriptions = async () => {
    setLoading(true);
    try {
      // Suppose your endpoint is /myupdates/get-subscriptions for paralegal
      // or you can reuse todaysupdates if you want, but conceptually it's separate
      const res = await AxiosInstance.get('todaysupdates/get-paralegal-subscriptions/');
      setSubscribedCourts(res.data.subscribed_courts || []);
    } catch (err) {
      console.error('Error fetching paralegal subscriptions:', err);
    }
    setLoading(false);
  };

  /**
   * State -> District
   */
  const handleStateChange = async (e) => {
    const st = e.target.value;
    setSelectedState(st);
    setSelectedDistrict('');
    setCourtList([]);
    if (!st) return;

    setLoading(true);
    try {
      const res = await AxiosInstance.get(`users/get-districts/?state=${st}`);
      setDistrictList(res.data.districts || []);
    } catch (err) {
      console.error('Error fetching districts:', err);
    }
    setLoading(false);
  };

  /**
   * District -> Courts
   */
  const handleDistrictChange = async (e) => {
    const dist = e.target.value;
    setSelectedDistrict(dist);
    setCourtList([]);
    if (!dist) return;

    setLoading(true);
    try {
      const res = await AxiosInstance.get(
        `users/get-courts/?state=${selectedState}&district=${dist}`
      );
      setCourtList(res.data.courts || []);
    } catch (err) {
      console.error('Error fetching courts:', err);
    }
    setLoading(false);
  };

  /**
   * Subscribing to a new court (max 3)
   */
  const subscribeToCourt = async () => {
    if (subscribedCourts.length >= 3) {
      alert('You cannot subscribe to more than 3 courts.');
      return;
    }
    if (!selectedCourt) {
      alert('Please select a valid court before subscribing.');
      return;
    }

    setLoading(true);
    try {
      // Suppose the endpoint is /myupdates/subscribe-court/
      const payload = { court: selectedCourt };
      await AxiosInstance.post('todaysupdates/paralegal-subscribe-court/', payload);
      // Re-fetch
      await fetchParalegalSubscriptions();
    } catch (err) {
      console.error('Error subscribing to court:', err);
    }
    setLoading(false);
  };

  /**
   * Unsubscribe from a court
   */
  const removeSubscription = async (courtName) => {
    setLoading(true);
    try {
      await AxiosInstance.post('todaysupdates/paralegal-unsubscribe-court/', { court: courtName });
      await fetchParalegalSubscriptions();
    } catch (err) {
      console.error('Error unsubscribing from court:', err);
    }
    setLoading(false);
  };

  /**
   * Fetch *my* (paralegal) updates
   */
  const fetchMyUpdates = async () => {
    setLoading(true);
    try {
      // e.g. /myupdates/fetch-my-updates
      // We pass optional start_date, end_date, and filterCourt
      const payload = {};
      if (startDate) payload.start_date = startDate;
      if (endDate) payload.end_date = endDate;
      if (filterCourt) payload.court = filterCourt;

      const res = await AxiosInstance.post('todaysupdates/fetch-paralegal-updates/', payload);
      setMyUpdates(res.data.updates || []);
    } catch (err) {
      console.error('Error fetching MY updates:', err);
    }
    setLoading(false);
  };

  return (
    <Box sx={{ p: 2, position: 'relative' }}>
      <LoadingOverlay open={loading} message="Loading..." />

      <Typography variant="h5" sx={{ mb: 2 }}>
        My Updates (Paralegal)
      </Typography>

      {/* Subscription Section */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6">Subscribe to a Court (max 3)</Typography>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mt: 2 }}>
          {/* State */}
          <FormControl sx={{ minWidth: 150 }}>
            <InputLabel>State</InputLabel>
            <Select value={selectedState} label="State" onChange={handleStateChange}>
              <MenuItem value="">
                <em>-- Select State --</em>
              </MenuItem>
              {stateList.map((st) => (
                <MenuItem key={st} value={st}>
                  {st}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* District */}
          <FormControl sx={{ minWidth: 150 }}>
            <InputLabel>District</InputLabel>
            <Select
              value={selectedDistrict}
              label="District"
              onChange={handleDistrictChange}
              disabled={!selectedState}
            >
              <MenuItem value="">
                <em>-- Select District --</em>
              </MenuItem>
              {districtList.map((dist) => (
                <MenuItem key={dist} value={dist}>
                  {dist}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Court */}
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Court</InputLabel>
            <Select
              value={selectedCourt}
              label="Court"
              onChange={(e) => setSelectedCourt(e.target.value)}
              disabled={!selectedDistrict}
            >
              <MenuItem value="">
                <em>-- Select Court --</em>
              </MenuItem>
              {courtList.map((court) => (
                <MenuItem key={court} value={court}>
                  {court}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button variant="contained" onClick={subscribeToCourt}>
            Subscribe
          </Button>
        </Box>
      </Box>

      {/* Display Subscribed Courts */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="body1" sx={{ mb: 1 }}>
          <strong>Your Subscribed Courts (max 3):</strong>
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {subscribedCourts.map((courtName) => (
            <Box
              key={courtName}
              sx={{
                border: '1px solid #ccc',
                borderRadius: 2,
                padding: '4px 8px',
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}
            >
              <Typography variant="body2">{courtName}</Typography>
              <IconButton
                size="small"
                color="error"
                onClick={() => removeSubscription(courtName)}
              >
                X
              </IconButton>
            </Box>
          ))}
        </Box>
      </Box>

      {/* Filter + Fetch My Updates */}
      <Typography variant="h6">View My Updates</Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2, mt: 2 }}>
        <TextField
          label="Start Date"
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          sx={{ width: 200 }}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="End Date"
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          sx={{ width: 200 }}
          InputLabelProps={{ shrink: true }}
        />

        {/* Filter by a single subscribed court or see all */}
        <FormControl sx={{ minWidth: 220 }}>
          <InputLabel>Filter by Court (optional)</InputLabel>
          <Select
            value={filterCourt}
            label="Filter by Court (optional)"
            onChange={(e) => setFilterCourt(e.target.value)}
          >
            <MenuItem value="">
              <em>-- All Subscribed Courts --</em>
            </MenuItem>
            {subscribedCourts.map((court) => (
              <MenuItem key={court} value={court}>
                {court}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Button variant="outlined" onClick={fetchMyUpdates}>
          Refresh My Updates
        </Button>
      </Box>

      {/* Show My Updates in a table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Court</strong></TableCell>
              <TableCell><strong>Type</strong></TableCell>
              <TableCell><strong>Content</strong></TableCell>
              <TableCell><strong>Transcription</strong></TableCell>
              <TableCell><strong>Time</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {myUpdates.map((upd, idx) => (
              <TableRow key={idx}>
                <TableCell>{upd.court}</TableCell>
                <TableCell>{upd.message_type === 'record' ? 'Audio' : 'Text'}</TableCell>
                <TableCell>
                  {upd.message_type === 'record' && upd.audio_url ? (
                    <audio controls controlsList="nodownload">
                      <source src={upd.audio_url} type="audio/ogg" />
                      Your browser does not support the audio element.
                    </audio>
                  ) : (
                    upd.update
                  )}
                </TableCell>
                <TableCell>{upd.transcription || ''}</TableCell>
                <TableCell>
                  {upd.time ? new Date(upd.time).toLocaleString() : 'No time'}
                </TableCell>
              </TableRow>
            ))}
            {myUpdates.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No updates found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

export default MyUpdates;
