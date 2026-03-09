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

import LoadingOverlay from './common/LoadingOverlay'; // Your shared loader
import AxiosInstance from './common/AxiosInstance';   // Your axios config

function TodaysUpdates() {
  const [loading, setLoading] = useState(false);

  // State/District/Court dropdowns
  const [stateList, setStateList] = useState([]);
  const [districtList, setDistrictList] = useState([]);
  const [courtList, setCourtList] = useState([]);

  // Selected values
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedCourt, setSelectedCourt] = useState('');

  // For date range
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Subscribed courts
  const [subscribedCourts, setSubscribedCourts] = useState([]);

  // Updates
  const [todaysUpdates, setTodaysUpdates] = useState([]);

  /**
   * 1. On mount: Fetch States + Subscriptions
   */
  useEffect(() => {
    fetchStateList();
    fetchUserSubscriptions();
  }, []);

  /**
   * Fetch list of states from backend
   */
  const fetchStateList = async () => {
    setLoading(true);
    try {
      const res = await AxiosInstance.get('users/get-states/');
      setStateList(res.data.states || []);
    } catch (err) {
      console.error('Error fetching states:', err);
    }
    setLoading(false);
  };

  /**
   * Fetch user's subscribed courts
   */
  const fetchUserSubscriptions = async () => {
    setLoading(true);
    try {
      const response = await AxiosInstance.get('todaysupdates/get-subscriptions/');
      setSubscribedCourts(response.data.subscribed_courts || []);
    } catch (error) {
      console.error('Error fetching user subscriptions:', error);
    }
    setLoading(false);
  };

  /**
   * Handle State selection
   */
  const handleStateChange = async (e) => {
    const newState = e.target.value;
    setSelectedState(newState);
    setSelectedDistrict('');
    setDistrictList([]);
    setCourtList([]);
    if (!newState) return;  // user cleared the state dropdown

    setLoading(true);
    try {
      const res = await AxiosInstance.get(`users/get-districts/?state=${newState}`);
      setDistrictList(res.data.districts || []);
    } catch (err) {
      console.error('Error fetching districts:', err);
    }
    setLoading(false);
  };

  /**
   * Handle District selection
   */
  const handleDistrictChange = async (e) => {
    const newDistrict = e.target.value;
    setSelectedDistrict(newDistrict);
    setCourtList([]);
    if (!newDistrict) return;  // user cleared the district dropdown

    setLoading(true);
    try {
      const res = await AxiosInstance.get(
        `users/get-courts/?state=${selectedState}&district=${newDistrict}`
      );
      setCourtList(res.data.courts || []);
    } catch (err) {
      console.error('Error fetching courts:', err);
    }
    setLoading(false);
  };

  /**
   * Handle Court selection
   */
  const handleCourtChange = (e) => {
    setSelectedCourt(e.target.value);
  };

  /**
   * Subscribe to a court (max 4)
   */
  const subscribeToCourt = async () => {
    if (subscribedCourts.length >= 4) {
      alert('You cannot subscribe to more than 4 courts.');
      return;
    }
    if (!selectedCourt) {
      alert('Please select a valid court before subscribing.');
      return;
    }
    setLoading(true);
    try {
      await AxiosInstance.post('todaysupdates/subscribe-court/', { court: selectedCourt });
      // Re-fetch updated subscriptions
      await fetchUserSubscriptions();
    } catch (err) {
      console.error('Error subscribing to court:', err);
    }
    setLoading(false);
  };

  /**
   * Remove subscription from a court
   */
  const removeSubscription = async (court) => {
    setLoading(true);
    try {
      await AxiosInstance.post('todaysupdates/unsubscribe-court/', { court });
      // Re-fetch updated subscriptions
      await fetchUserSubscriptions();
    } catch (err) {
      console.error('Error unsubscribing from court:', err);
    }
    setLoading(false);
  };

  /**
   * Fetch updates for the optional date range & optional single-court filter
   */
  const fetchTodaysUpdates = async () => {
    setLoading(true);
    try {
      const payload = {};
      if (startDate.trim()) payload.start_date = startDate;
      if (endDate.trim()) payload.end_date = endDate;
      if (selectedCourt.trim()) payload.court = selectedCourt.trim();

      const res = await AxiosInstance.post('todaysupdates/fetch-updates/', payload);
      setTodaysUpdates(res.data.updates || []);
    } catch (err) {
      console.error('Error fetching updates:', err);
    }
    setLoading(false);
  };

  return (
    <Box sx={{ p: 2, position: 'relative' }}>
      <LoadingOverlay open={loading} message="Fetching data..." />

      {/* Subscriptions Section */}
      <Typography variant="h5" sx={{ mb: 2 }}>
        Subscribe to a Court
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 3 }}>
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel id="state-select-label">State</InputLabel>
          <Select
            labelId="state-select-label"
            value={selectedState}
            label="State"
            onChange={handleStateChange}
          >
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

        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel id="district-select-label">District</InputLabel>
          <Select
            labelId="district-select-label"
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

        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel id="court-select-label">Court</InputLabel>
          <Select
            labelId="court-select-label"
            value={selectedCourt}
            label="Court"
            onChange={handleCourtChange}
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

      {/* Display Subscribed Courts */}
      <Typography variant="body1" sx={{ mb: 1 }}>
        <strong>Your Subscribed Courts (max 4):</strong>
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 4 }}>
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

      {/* Updates Section */}
      <Typography variant="h5" gutterBottom>
        Today's Updates
      </Typography>

      {/* Date range selection (optional) */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
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

        {/* Filter by Court (optional, from user's subscribed courts) */}
        <FormControl sx={{ minWidth: 220 }}>
          <InputLabel id="filter-court-select-label">Filter by Court (optional)</InputLabel>
          <Select
            labelId="filter-court-select-label"
            label="Filter by Court (optional)"
            value={selectedCourt}
            onChange={(e) => setSelectedCourt(e.target.value)}
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

        <Button variant="outlined" onClick={fetchTodaysUpdates}>
          Refresh Updates
        </Button>
      </Box>

      {/* Display updates */}
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell><strong>Court</strong></TableCell>
                <TableCell><strong>Type</strong></TableCell>
                <TableCell><strong>Content</strong></TableCell>
                <TableCell><strong>Transcription</strong></TableCell>
                <TableCell><strong>Paralegal</strong></TableCell>
                <TableCell><strong>Update Time</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {todaysUpdates.map((upd, idx) => (
                <TableRow key={idx}>
                  {/* Court */}
                  <TableCell>{upd.court}</TableCell>
                  
                  {/* Type (Audio or Text) */}
                  <TableCell>
                    {upd.message_type === 'record' ? 'Audio' : 'Text'}
                  </TableCell>
                  
                  {/* Content (Either <audio> or raw text) */}
                  <TableCell>
                    {upd.message_type === 'record' && upd.audio_url ? (
                      <audio controls controlsList="nodownload">
                        <source src={upd.audio_url} type="audio/ogg" />
                        Your browser does not support audio.
                      </audio>
                    ) : (
                      upd.update
                    )}
                  </TableCell>
                  
                  {/* Transcription (show if provided, else blank) */}
                  <TableCell>
                    {upd.transcription || ''}
                  </TableCell>
                  
                  {/* Paralegal */}
                  <TableCell>{upd.paralegal}</TableCell>
                  
                  {/* Update Time */}
                  <TableCell>
                    {upd.time ? new Date(upd.time).toLocaleString() : 'No time'}
                  </TableCell>
                </TableRow>
              ))}
        
              {/* If no updates found */}
              {todaysUpdates.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} align="center">
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

export default TodaysUpdates;
