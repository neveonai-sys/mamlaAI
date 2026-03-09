// src/components/Feedback.js

import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Rating,
  IconButton,
  Divider,
} from '@mui/material';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import AxiosInstance from './common/AxiosInstance'; // or your axios setup

const Feedback = () => {
  const [overallFeedback, setOverallFeedback] = useState('');
  const [overallRating, setOverallRating] = useState(0);

  // For multiple components feedback
  const [componentsFeedback, setComponentsFeedback] = useState([
    { componentName: '', feedback: '', rating: 0 },
  ]);

  const handleOverallFeedbackChange = (event) => {
    setOverallFeedback(event.target.value);
  };

  const handleOverallRatingChange = (event, newValue) => {
    setOverallRating(newValue);
  };

  // Dynamic addition of component feedback blocks
  const handleAddComponentFeedback = () => {
    setComponentsFeedback((prev) => [
      ...prev,
      { componentName: '', feedback: '', rating: 0 },
    ]);
  };

  // Handler for each feedback item
  const handleComponentFeedbackChange = (index, field, value) => {
    const updated = [...componentsFeedback];
    updated[index][field] = value;
    setComponentsFeedback(updated);
  };

  const handleSubmit = async () => {
    try {
      const payload = {
        overallFeedback,
        overallRating,
        components: componentsFeedback,
      };

      // Assuming your Django endpoint is at /feedback/submit
      // and you have AxiosInstance configured with the correct baseURL
      const response = await AxiosInstance.post('users/submit-feedback/', payload);
      alert('Feedback submitted successfully!');
      // Reset state or do any additional UI updates
      setOverallFeedback('');
      setOverallRating(0);
      setComponentsFeedback([{ componentName: '', feedback: '', rating: 0 }]);
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert('Error submitting feedback, please try again.');
    }
  };

  return (
    <Box sx={{ margin: '2rem' }}>
      <Typography variant="h5" gutterBottom>
        Overall Feedback
      </Typography>
      <TextField
        label="Share your feedback or suggestions"
        multiline
        rows={4}
        value={overallFeedback}
        onChange={handleOverallFeedbackChange}
        variant="outlined"
        fullWidth
        sx={{ mb: 2 }}
      />

      <Typography component="legend">Overall Rating (Out of 10)</Typography>
      <Rating
        name="overall-rating"
        max={10}
        value={overallRating}
        onChange={handleOverallRatingChange}
      />

      <Divider sx={{ my: 3 }} />

      <Typography variant="h6" gutterBottom>
        Component-wise Feedback
      </Typography>

      {componentsFeedback.map((comp, index) => (
        <Box key={index} sx={{ mb: 3 }}>
          <TextField
            label="Component Name"
            value={comp.componentName}
            onChange={(e) =>
              handleComponentFeedbackChange(index, 'componentName', e.target.value)
            }
            variant="outlined"
            fullWidth
            sx={{ mb: 1 }}
          />

          <TextField
            label="Feedback / Suggestions"
            multiline
            rows={3}
            value={comp.feedback}
            onChange={(e) =>
              handleComponentFeedbackChange(index, 'feedback', e.target.value)
            }
            variant="outlined"
            fullWidth
            sx={{ mb: 1 }}
          />

          <Typography component="legend">Rating (Out of 10)</Typography>
          <Rating
            name={`component-rating-${index}`}
            max={10}
            value={comp.rating}
            onChange={(event, newValue) =>
              handleComponentFeedbackChange(index, 'rating', newValue)
            }
          />
        </Box>
      ))}

      <IconButton
        color="primary"
        onClick={handleAddComponentFeedback}
        aria-label="add more component feedback"
      >
        <AddCircleIcon />
      </IconButton>
      <Typography variant="body2">Add another component</Typography>

      <Divider sx={{ my: 3 }} />

      <Button variant="contained" color="primary" onClick={handleSubmit}>
        Submit Feedback
      </Button>
    </Box>
  );
};

export default Feedback;
