import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Box, 
  Typography, 
  Paper, 
  Alert,
  Button,
  CircularProgress,
  Snackbar,
} from '@mui/material';
import CreateNewDraftTab from '../tabs/CreateNewDraftTab';
import testDraftService from '../../services/testDraftService';

// Static data for the form
const LANGUAGES = [
  'English', 'Hindi', 'Bengali', 'Tamil', 'Telugu', 
  'Kannada', 'Malayalam', 'Gujarati', 'Marathi', 'Punjabi'
];

const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand',
  'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur',
  'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
  'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
  'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Andaman and Nicobar Islands',
  'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu', 'Delhi',
  'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry'
];

const TestAIDrafting = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('English');
  const [selectedState, setSelectedState] = useState('');
  const [userQuery, setUserQuery] = useState('');
  const [inputMethod, setInputMethod] = useState('write');
  const [uploadFile, setUploadFile] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [editsRemaining, setEditsRemaining] = useState(3);
  const [showSuccess, setShowSuccess] = useState(false);
  const navigate = useNavigate();

  // Mock data for CreateNewDraftTab
  const filterData = {
    states: INDIAN_STATES,
    districts: [],
    courts: [],
    case_client_map: {},
    clientIds_without_case: []
  };

  const handleFileUpload = (acceptedFiles) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      setUploadFile(acceptedFiles[0]);
      setInputMethod('upload');
    }
  };

  const handleGenerateDraft = async (draftData) => {
    try {
      setLoading(true);
      setError('');
      
      const response = await testDraftService.createDraft({
        user_query: userQuery,
        language: selectedLanguage,
        state: selectedState,
        ...draftData
      });

      setSessionId(response.session_id);
      setEditsRemaining(response.edits_remaining);
      setShowSuccess(true);
      
      // Navigate to draft preview with the test draft data
      navigate(`/draft-preview/${response.session_id}`, { 
        state: {
          isTest: true,
          draftSections: response.draft_sections,
          editsRemaining: response.edits_remaining,
          expiresIn: response.expires_in_minutes
        }
      });
      
    } catch (err) {
      console.error('Error generating test draft:', err);
      setError(err.error || 'Failed to generate draft. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCloseError = () => {
    setError('');
  };

  const handleCloseSuccess = () => {
    setShowSuccess(false);
  };

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error" onClose={handleCloseError}>
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box maxWidth={1000} margin="0 auto" p={3}>
      <Typography 
        variant="h5" 
        align="center" 
        gutterBottom
        onClick={() => navigate('/')}
        sx={{
          marginBottom: 4,
          cursor: 'pointer',
          color: 'primary.main',
          textDecoration: 'none',
          fontWeight: 700, 
          fontSize: '2rem', 
          letterSpacing: '0.5px',
          transition: 'all 0.2s ease-in-out', 
          display: 'inline-block', 
          padding: '0.5rem 1rem', 
          borderRadius: '4px', 
          '&:hover': {
            color: 'primary.dark',
            textDecoration: 'none',
            backgroundColor: 'rgba(25, 118, 210, 0.04)', 
            transform: 'translateY(-1px)', 
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)' 
          },
          '&:active': {
            transform: 'translateY(0)', 
            boxShadow: 'none'
          }
        }}
      >
        Mamla.Ai
      </Typography>
      <Typography variant="h4" align='center' gutterBottom sx={{ mb: 4 }}>
        Test AI Drafting
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        This is a preview of our AI Drafting feature. You can test creating a draft,
        but your work will not be saved. To save your drafts and access all features,
        please sign up.
      </Alert>

      <Snackbar
        open={showSuccess}
        autoHideDuration={6000}
        onClose={handleCloseSuccess}
        message="Draft created successfully!"
      />

      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>

        <CreateNewDraftTab
          filterData={filterData}
          languages={LANGUAGES}
          selectedLanguage={selectedLanguage}
          setSelectedLanguage={setSelectedLanguage}
          onSubmit={handleGenerateDraft}
          isTestMode={true}
          isClientUser={true}
          filterDataState={filterData}
          statesList={INDIAN_STATES}
          districtsList={[]}
          courtsList={[]}
          selectedState={selectedState}
          selectedDistrict=""
          selectedCourt=""
          handleSelectState={setSelectedState}
          handleSelectDistrict={() => {}}
          handleSelectCourt={() => {}}
          setErrorMessage={setError}
          languagesList={LANGUAGES}
          userQuery={userQuery}
          setUserQuery={setUserQuery}
          inputMethod={inputMethod}
          setInputMethod={setInputMethod}
          uploadFile={uploadFile}
          setUploadFile={handleFileUpload}
          handleSubmitQuery={handleGenerateDraft}
          downloadTemplate={() => {}}
          loading={loading}
        />

        {loading && (
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <CircularProgress />
            <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
              Generating your test draft...
            </Typography>
          </Box>
        )}

        <Box sx={{ mt: 3, textAlign: 'center' }}>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={() => window.location.href = '/signup'}
            disabled={loading}
            sx={{ minWidth: 200 }}
          >
            Sign Up to Save Your Work
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default TestAIDrafting;