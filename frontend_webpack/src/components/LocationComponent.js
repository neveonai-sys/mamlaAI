// src/components/LocationComponent.js

import React, { useState, useEffect } from 'react';
import AxiosInstance from '../common/AxiosInstance';
import {
  Box,
  Button,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
} from '@mui/material';
import { State, City } from 'country-state-city';
import LoadingOverlay from './LoadingOverlay'; // Import the LoadingOverlay component

const COUNTRY_CODE = 'IN'; // Assuming India. Change as needed.

function LocationComponent({ sessionId, onDraftGenerated }) {
  const [states, setStates] = useState([]);
  const [cities, setCities] = useState([]);
  const [selectedState, setSelectedState] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [loadingStates, setLoadingStates] = useState(true);
  const [loadingCities, setLoadingCities] = useState(false);
  const [submitting, setSubmitting] = useState(false); // New state for submission
  const [error, setError] = useState('');

  // Fetch all states when the component mounts
  useEffect(() => {
    const fetchStates = () => {
      try {
        const allStates = State.getStatesOfCountry(COUNTRY_CODE);
        setStates(allStates);
      } catch (err) {
        console.error('Error fetching states:', err);
        setError('Failed to load states.');
      } finally {
        setLoadingStates(false);
      }
    };

    fetchStates();
  }, []);

  // Fetch cities when a state is selected
  useEffect(() => {
    if (selectedState) {
      setLoadingCities(true);
      try {
        const allCities = City.getCitiesOfState(COUNTRY_CODE, selectedState);
        setCities(allCities);
      } catch (err) {
        console.error('Error fetching cities:', err);
        setError('Failed to load districts.');
      } finally {
        setLoadingCities(false);
      }
    } else {
      setCities([]);
      setSelectedCity('');
    }
  }, [selectedState]);

  const handleSubmit = () => {
    if (!selectedState || !selectedCity) {
      setError('Please select both state and district.');
      return;
    }

    setError(''); // Clear previous errors
    setSubmitting(true); // Show loading overlay

    AxiosInstance.post(`aidrafts/set_location`, {
      session_id: sessionId,
      state: selectedState,
      district: selectedCity,
    })
      .then((response) => {
        onDraftGenerated();
      })
      .catch((error) => {
        console.error('Error setting location:', error);
        setError('Failed to generate draft. Please try again.');
      })
      .finally(() => {
        setSubmitting(false); // Hide loading overlay
      });
  };

  return (
    <Box sx={{ marginTop: 3 }}>
      {/* Loading Overlay */}
      <LoadingOverlay open={submitting} message="Generating your legal draft with AI assistance..." />

      <Typography variant="h5" gutterBottom>
        Select Location
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, maxWidth: 400 }}>
        {/* State Dropdown */}
        <FormControl fullWidth>
          <InputLabel id="state-select-label">State</InputLabel>
          {loadingStates ? (
            <Box sx={{ display: 'flex', alignItems: 'center', pl: 2 }}>
              <CircularProgress size={24} />
              <Typography sx={{ ml: 2 }}>Loading States...</Typography>
            </Box>
          ) : (
            <Select
              labelId="state-select-label"
              id="state-select"
              value={selectedState}
              label="State"
              onChange={(e) => setSelectedState(e.target.value)}
            >
              {states.length > 0 ? (
                states.map((state) => (
                  <MenuItem key={state.isoCode} value={state.isoCode}>
                    {state.name}
                  </MenuItem>
                ))
              ) : (
                <MenuItem value="" disabled>
                  No States Available
                </MenuItem>
              )}
            </Select>
          )}
        </FormControl>

        {/* District Dropdown */}
        <FormControl fullWidth disabled={!selectedState || loadingCities}>
          <InputLabel id="district-select-label">District</InputLabel>
          {loadingCities ? (
            <Box sx={{ display: 'flex', alignItems: 'center', pl: 2 }}>
              <CircularProgress size={24} />
              <Typography sx={{ ml: 2 }}>Loading Districts...</Typography>
            </Box>
          ) : (
            <Select
              labelId="district-select-label"
              id="district-select"
              value={selectedCity}
              label="District"
              onChange={(e) => setSelectedCity(e.target.value)}
            >
              {cities.length > 0 ? (
                cities.map((city) => (
                  <MenuItem key={city.name} value={city.name}>
                    {city.name}
                  </MenuItem>
                ))
              ) : (
                <MenuItem value="" disabled>
                  No Districts Available
                </MenuItem>
              )}
            </Select>
          )}
        </FormControl>

        {/* Error Message */}
        {error && (
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        )}

        {/* Submit Button */}
        <Button variant="contained" color="primary" onClick={handleSubmit}>
          Generate Draft
        </Button>
      </Box>
    </Box>
  );
}

export default LocationComponent;