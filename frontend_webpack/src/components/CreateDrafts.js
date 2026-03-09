import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Backdrop,
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  Grid,
  IconButton,
  Alert,
  Snackbar,
  Paper,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { useSelector } from 'react-redux';
import AxiosInstance from './common/AxiosInstance'; // Ensure AxiosInstance is correctly configured
import DatePicker from 'react-datepicker';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import SearchIcon from '@mui/icons-material/Search';
import SentimentDissatisfiedIcon from '@mui/icons-material/SentimentDissatisfied';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import 'react-datepicker/dist/react-datepicker.css';
import DOMPurify from 'dompurify';
import debounce from 'lodash.debounce';

// Styled Components
const BackgroundBox = styled(Box)(({ theme }) => ({
  padding: theme.spacing(3),
  backgroundColor: '#f0f2f5',
  minHeight: '100vh',
}));

const StyledButton = styled(Button)(({ theme }) => ({
  backgroundColor: '#6a11cb',
  color: '#fff',
  '&:hover': {
    backgroundColor: '#2575fc',
  },
}));

const SaveButton = styled(Button)(({ theme }) => ({
  backgroundColor: '#FFA500',
  color: '#fff',
  '&:hover': {
    backgroundColor: '#FF8C00',
  },
}));

const SearchBox = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  marginBottom: theme.spacing(2),
  gap: theme.spacing(1),
}));

const FormContainer = styled(Paper)(({ theme }) => ({
  marginTop: theme.spacing(2),
  padding: theme.spacing(3),
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[2],
}));

const SectionPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(3),
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[1],
}));

// Tab Panel Component for Accessibility
const TabPanel = (props) => {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`create-drafts-tabpanel-${index}`}
      aria-labelledby={`create-drafts-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
};

// Helper function for accessibility props
const a11yProps = (index) => {
  return {
    id: `create-drafts-tab-${index}`,
    'aria-controls': `create-drafts-tabpanel-${index}`,
  };
};

const CreateDrafts = () => {
  // Access user email from Redux store
  const { email } = useSelector((state) => state.user);

  // State Variables
  const [draftTypes, setDraftTypes] = useState([]);
  const [draftItems, setDraftItems] = useState([]);
  const [selectedDraftType, setSelectedDraftType] = useState('');
  const [selectedDraftItem, setSelectedDraftItem] = useState('');
  const [formFields, setFormFields] = useState({});
  const [formData, setFormData] = useState({});
  const [formErrors, setFormErrors] = useState({}); // State to track validation errors
  const [pdfUrl, setPdfUrl] = useState(null); // URL of the PDF to display
  const [pdfBlob, setPdfBlob] = useState(null); // Blob of the submitted PDF
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchResults, setShowSearchResults] = useState(false); // Defined showSearchResults state
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success', // 'error', 'warning', 'info'
  });
  const [currentTab, setCurrentTab] = useState(0); // State to track current tab
  const formContainerRef = useRef(null); // Ref for form container
  const [confirmClear, setConfirmClear] = useState(false);

  // States for Preview and Suggestion
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewOrigin, setPreviewOrigin] = useState(null); // 'getDrafts' or 'searchDrafts'
  const [currentPreviewDraft, setCurrentPreviewDraft] = useState(null); // { type, filename }
  const [isSuggestingChanges, setIsSuggestingChanges] = useState(false);
  const [suggestionText, setSuggestionText] = useState('');
  const [isMaxSuggestionsReached, setIsMaxSuggestionsReached] = useState(false);
  const [isCreatingNewDraft, setIsCreatingNewDraft] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1.0); // Initial zoom level

  // Saved Drafts State
  const [savedDrafts, setSavedDrafts] = useState([]);
  const [selectedSavedDraft, setSelectedSavedDraft] = useState(null);

  // Handle Tab Change
  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  // Handle Clear Confirmation
  const handleClear = () => {
    setConfirmClear(true);
  };

  const confirmClearForm = () => {
    setConfirmClear(false);
    // Clear form state
    setSelectedDraftType('');
    setSelectedDraftItem('');
    setFormFields({});
    setFormData({});
    setFormErrors({});
    setDraftItems([]);
    setPdfUrl(null); // Clear previous PDF URL
    setPdfBlob(null);
    setSearchResults([]);
    setSearchQuery('');
    setShowSearchResults(false); // Reset showSearchResults
    setIsMaxSuggestionsReached(false);
    setZoomLevel(1.0);
  };

  const cancelClearForm = () => {
    setConfirmClear(false);
  };

  // Debounced validation function
  const debouncedValidate = useCallback(
    debounce((updatedFormData) => {
      validateForm(updatedFormData);
    }, 300), // 300ms debounce
    []
  );

  // Auto-save function with useCallback to ensure latest state is accessed
  const autoSaveForm = useCallback(async () => {
    console.log('Auto-save triggered');
    console.log('Draft Type:', selectedDraftType);
    console.log('Draft Item:', selectedDraftItem);
    console.log('Form Data:', formData);
    console.log('Required Fields:', formFields);

    // Ensure that both draft type and filename are selected
    if (!selectedDraftType || !selectedDraftItem) {
      console.warn('Draft type or filename is not selected. Auto-save skipped.');
      return;
    }

    // Prepare the payload as per backend requirements
    const payload = {
      type: selectedDraftType,
      filename: selectedDraftItem,
      form_data: formData,
      req_fields: formFields,
    };

    try {
      await AxiosInstance.post(`drafts/auto-save/`, payload);
      console.log('Auto-saved successfully.');
      handleSnackbarOpen('Auto-saved your progress.', 'info');
    } catch (error) {
      console.error('Error auto-saving form:', error);
      handleSnackbarOpen('Failed to auto-save. Please check your connection.', 'error');
    }
  }, [selectedDraftType, selectedDraftItem, formData, formFields]);

  // Debounced Auto-Save Function
  const debouncedAutoSave = useRef(
    debounce(() => {
      autoSaveForm();
    }, 1000)
  ).current; // 1000ms debounce

  // Time-Based Auto-Save (Every 5 minutes)
  useEffect(() => {
    const interval = setInterval(() => {
      autoSaveForm();
    }, 300000); // 300,000ms = 5 minutes

    return () => clearInterval(interval); // Cleanup on unmount
  }, [autoSaveForm]);

  // Debounced Fetch Draft Items
  const debouncedFetchDraftItems = useRef(
    debounce((draftType) => {
      fetchDraftItems(draftType);
    }, 300) // 300ms debounce
  ).current;

  // Cleanup debounced functions on unmount
  useEffect(() => {
    return () => {
      debouncedAutoSave.cancel();
      debouncedFetchDraftItems.cancel();
      debouncedValidate.cancel();
    };
  }, [debouncedAutoSave, debouncedFetchDraftItems, debouncedValidate]);

  // Fetch draft types on component mount
  useEffect(() => {
    const fetchDraftTypes = async () => {
      setLoading(true);
      try {
        const response = await AxiosInstance.get(`drafts/get-all-drafts/`);
        setDraftTypes(response.data.dir_list);
      } catch (error) {
        console.error('Error fetching draft types:', error);
        handleSnackbarOpen('Failed to fetch draft types. Please try again later.', 'error');
      } finally {
        setLoading(false);
      }
    };

    fetchDraftTypes();
  }, []);

  // Fetch saved drafts on component mount
  useEffect(() => {
    const fetchSavedDrafts = async () => {
      setLoading(true);
      try {
        const response = await AxiosInstance.get(`drafts/get-saved-drafts/`);
        // Assuming the API returns an array of drafts with 'type' and 'filename'
        setSavedDrafts(response.data.saved_drafts || []);
      } catch (error) {
        console.error('Error fetching saved drafts:', error);
        handleSnackbarOpen('Failed to fetch saved drafts. Please try again later.', 'error');
      } finally {
        setLoading(false);
      }
    };

    fetchSavedDrafts();
  }, []);

  const fetchDraftItems = async (draftType) => {
    if (!draftType) return;
    setLoading(true);
    try {
      const response = await AxiosInstance.get(
        `drafts/draft-items?type=${encodeURIComponent(draftType)}`
      );
      setDraftItems(response.data.all_drafts_list);
    } catch (error) {
      console.error('Error fetching draft items:', error);
      handleSnackbarOpen('Failed to fetch draft items. Please try again later.', 'error');
    } finally {
      setLoading(false);
    }
  };

  /**
   * handleDraftTypeChange
   * Handles the selection of a draft type and fetches corresponding draft items.
   */
  const handleDraftTypeChange = (e) => {
    const draftType = e.target.value;
    setSelectedDraftType(draftType);
    setSelectedDraftItem('');
    setFormFields({});
    setFormData({});
    setFormErrors({});
    setDraftItems([]);
    setPdfUrl(null); // Clear previous PDF URL
    setPdfBlob(null);
    setIsMaxSuggestionsReached(false);
    setZoomLevel(1.0); // Reset zoom level
    debouncedFetchDraftItems(draftType); // Trigger debounced fetch
  };

  /**
   * handleDraftItemSelection
   * Fetches the required fields for the selected draft and initializes the form.
   */
  const handleDraftItemSelection = async () => {
    if (!selectedDraftType || !selectedDraftItem) {
      handleSnackbarOpen('Please select both Draft Type and Draft Item.', 'warning');
      return;
    }

    setLoading(true);
    try {
      // Convert current pdfUrl to base64
      const pdfBytes = await fetchPdfBytes(pdfUrl); // ArrayBuffer
      const base64Pdf = arrayBufferToBase64(pdfBytes);

      const payload = {
        type: selectedDraftType,
        filename: selectedDraftItem,
        pdf_bytes: base64Pdf,
      };

      const response = await AxiosInstance.post(
        `drafts/draft-fields/`,
        payload,
        { responseType: 'json' }
      );

      console.log('API Response:', response);

      let fields = response.data.req_fields;
      console.log('Fields Before Parsing:', fields);

      if (typeof fields === 'string') {
        if (fields.trim().startsWith('{') || fields.trim().startsWith('[')) {
          try {
            fields = JSON.parse(fields);
          } catch (error) {
            console.error('Error parsing req_fields JSON:', error);
            handleSnackbarOpen('Error parsing required fields. Please contact support.', 'error');
            return;
          }
        } else {
          // Handle the case where fields is a message or plain text
          console.warn('No required fields:', fields);
          handleSnackbarOpen(`Message from server: ${fields}`, 'info');
          fields = {};
        }
      }

      if (Object.keys(fields).length === 0) {
        handleSnackbarOpen('There are no required fields for this draft.', 'info');
        setFormFields({});
        setFormData({});
        setFormErrors({});
        return;
      }

      setFormFields(fields);
      setFormData(initializeFormData(fields));
      setFormErrors({}); // Reset errors
      handleSnackbarOpen('Form loaded successfully.', 'success');

      // Scroll to the form container
      if (formContainerRef.current) {
        formContainerRef.current.scrollIntoView({ behavior: 'smooth' });
      }

      // Switch to the Get Drafts tab to view the form
      setCurrentTab(0);

    } catch (error) {
      console.error('Error fetching draft fields:', error);
      handleSnackbarOpen('An error occurred while fetching the draft fields. Please try again later.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const initializeFormData = (fields) => {
    const data = {};
    const setInitialValues = (obj, prefix = '') => {
      Object.entries(obj).forEach(([key, value]) => {
        if (typeof value === 'object' && !Array.isArray(value)) {
          setInitialValues(value, `${prefix}${key}.`);
        } else {
          data[`${prefix}${key}`] = value;
        }
      });
    };
    setInitialValues(fields);
    return data;
  };

  const handleInputChange = (e, key) => {
    const sanitizedValue = DOMPurify.sanitize(e.target.value); // Sanitize input
    const updatedFormData = { ...formData, [key]: sanitizedValue };
    setFormData(updatedFormData);
    debouncedValidate(updatedFormData); // Trigger debounced validation
    debouncedAutoSave(); // Trigger debounced auto-save without passing data
  };

  // Form Validation Function
  const validateForm = (data) => {
    const errors = {};

    Object.entries(formFields).forEach(([key, value]) => {
      const fieldKey = key;
      const fieldValue = data[fieldKey];
      const isRequired = value.required === 'True';
      const dataType = value.datatype;

      if (isRequired) {
        if (!fieldValue || fieldValue === '') {
          errors[fieldKey] = 'This field is required.';
          return;
        }
      }

      if (dataType === 'str') {
        if (fieldValue.length > 500) {
          errors[fieldKey] = 'Maximum 500 characters allowed.';
        }
        // Add more string validations if needed
      } else if (dataType === 'int') {
        if (fieldValue !== '' && isNaN(fieldValue)) {
          errors[fieldKey] = 'Must be a valid number.';
        }
        // Add range validations if needed
      } else if (dataType === 'datetime') {
        if (fieldValue && isNaN(new Date(fieldValue).getTime())) {
          errors[fieldKey] = 'Must be a valid date.';
        }
      }
      // Add more data type validations if needed
    });

    setFormErrors(errors);
  };

  const handleSubmit = async () => {
    // Check if there are validation errors
    if (Object.keys(formErrors).length > 0) {
      handleSnackbarOpen('Please fix validation errors before submitting.', 'warning');
      return;
    }

    // Check if required fields are filled
    for (const [key, value] of Object.entries(formFields)) {
      if (
        value.required === 'True' &&
        (!formData[key] || formData[key] === '')
      ) {
        handleSnackbarOpen(`Please fill in the required field: ${key.replace(/_/g, ' ')}`, 'warning');
        return;
      }
    }

    const payload = {
      type: selectedDraftType,
      filename: selectedDraftItem,
      email_id: email,
      fields: formData,
    };

    setLoading(true);
    try {
      const response = await AxiosInstance.post(
        `drafts/submit-draft/`,
        payload,
        { responseType: 'blob' }
      );
      const blob = new Blob([response.data], { type: 'application/pdf' });
      setPdfBlob(blob);
      console.log('Draft submitted successfully:', response);
      handleSnackbarOpen('Draft submitted successfully! You can now download the PDF.', 'success');

      // Scroll to the download button
      if (formContainerRef.current) {
        formContainerRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    } catch (error) {
      console.error('Error submitting draft:', error);
      handleSnackbarOpen('Failed to submit draft. Please try again later.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const downloadPdf = () => {
    if (!pdfBlob) return;

    const url = window.URL.createObjectURL(pdfBlob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute(
      'download',
      selectedDraftItem.split('.')[0] + '.pdf'
    );
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const renderFormFields = (fields, prefix = '') => {
    return Object.entries(fields).map(([key, value]) => {
      const isRequired = value.required === 'True';
      const dataType = value.datatype;
      const description = value.desc;

      let fieldComponent;

      if (dataType === 'datetime') {
        fieldComponent = (
          <DatePicker
            key={prefix + key}
            selected={formData[`${prefix}${key}`] ? new Date(formData[`${prefix}${key}`]) : null}
            onChange={(date) => {
              handleInputChange(
                { target: { value: date.toISOString() } },
                `${prefix}${key}`
              );
            }}
            customInput={
              <TextField
                label={`${key.replace(/_/g, ' ')} (${description})`}
                fullWidth
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <CalendarTodayIcon />
                    </InputAdornment>
                  ),
                }}
                required={isRequired}
                sx={{ minWidth: 600 }}
                error={Boolean(formErrors[`${prefix}${key}`])}
                helperText={formErrors[`${prefix}${key}`] || ''}
              />
            }
            dateFormat="yyyy-MM-dd"
          />
        );
      } else if (dataType === 'str') {
        fieldComponent = (
          <TextField
            key={prefix + key}
            label={`${key.replace(/_/g, ' ')} (${description})`}
            variant="outlined"
            fullWidth
            value={formData[`${prefix}${key}`] || ''}
            onChange={(e) => handleInputChange(e, `${prefix}${key}`)}
            required={isRequired}
            disabled={loading}
            inputProps={{
              maxLength: 500, // Limit input length
            }}
            error={Boolean(formErrors[`${prefix}${key}`])}
            helperText={formErrors[`${prefix}${key}`] || ''}
          />
        );
      } else if (dataType === 'int') {
        fieldComponent = (
          <TextField
            key={prefix + key}
            label={`${key.replace(/_/g, ' ')} (${description})`}
            variant="outlined"
            fullWidth
            type="number"
            value={formData[`${prefix}${key}`] || ''}
            onChange={(e) => handleInputChange(e, `${prefix}${key}`)}
            required={isRequired}
            disabled={loading}
            inputProps={{
              min: 0, // Example: setting a minimum value
              max: 1000000, // Example: setting a maximum value
            }}
            error={Boolean(formErrors[`${prefix}${key}`])}
            helperText={formErrors[`${prefix}${key}`] || ''}
          />
        );
      } else {
        return null;
      }

      return (
        <Box key={prefix + key} sx={{ marginBottom: 2 }}>
          {fieldComponent}
        </Box>
      );
    });
  };

  const handleSearch = async () => {
    // Clear previous selections and form fields immediately
    setSelectedDraftType('');
    setSelectedDraftItem('');
    setFormFields({});
    setFormData({});
    setFormErrors({});
    setDraftItems([]);
    setPdfUrl(null);
    setPdfBlob(null);
    setSearchResults([]);
    setShowSearchResults(false); // Reset showSearchResults
    setIsMaxSuggestionsReached(false);
    setZoomLevel(1.0); // Reset zoom level

    if (!searchQuery) {
      handleSnackbarOpen('Please enter a keyword to search.', 'warning');
      return;
    }

    setLoading(true);
    try {
      const response = await AxiosInstance.get(
        `search/search-by-index?q=${encodeURIComponent(searchQuery)}`
      );
      if (response.data.results && response.data.results.length > 0) {
        setSearchResults(response.data.results);
        setShowSearchResults(true);
      } else {
        setSearchResults([]); // Explicitly set to empty array
        handleSnackbarOpen('No drafts found for the given keyword.', 'info');
      }
    } catch (error) {
      console.error('Error searching drafts:', error);
      handleSnackbarOpen('Failed to search drafts. Please try again later.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSearch = () => {
    setSearchResults([]);
    setSearchQuery('');
    setSelectedDraftType('');
    setSelectedDraftItem('');
    setFormFields({});
    setFormData({});
    setFormErrors({});
    setDraftItems([]);
    setPdfUrl(null);
    setPdfBlob(null);
    setShowSearchResults(false);
    setIsMaxSuggestionsReached(false);
    setZoomLevel(1.0); // Reset zoom level
  };

  const handleSnackbarOpen = (message, severity) => {
    setSnackbar({
      open: true,
      message,
      severity,
    });
  };

  const handleSnackbarClose = () => {
    setSnackbar({
      ...snackbar,
      open: false,
    });
  };

  const isFormLoaded = Object.keys(formFields).length > 0;

  // Additional handler for Search Input with Debounce
  const handleSearchInputChange = (e) => {
    const sanitizedValue = DOMPurify.sanitize(e.target.value);
    setSearchQuery(sanitizedValue);
    // Do not trigger search on input change
    // debouncedHandleSearch();
  };

  /**
   * handlePreview
   * Opens the preview dialog and fetches the PDF either from the server or uses the provided blob.
   * @param {string} type - Draft type
   * @param {string} filename - Draft filename
   * @param {Blob|null} pdfBlobParam - Optional PDF blob
   * @param {string} origin - Origin of the preview ('getDrafts' or 'searchDrafts')
   */
  const handlePreview = async (type, filename, pdfBlobParam = null, origin = 'getDrafts') => {
    setLoading(true);
    try {
      let fetchedPdfUrl;
      if (pdfBlobParam) {
        fetchedPdfUrl = URL.createObjectURL(pdfBlobParam);
      } else {
        const response = await AxiosInstance.get(
          `drafts/get-template/`,
          {
            params: { type, filename },
            responseType: 'blob', // Expect binary data
          }
        );
        fetchedPdfUrl = URL.createObjectURL(response.data);
      }
      setPdfUrl(fetchedPdfUrl);
      setPreviewOrigin(origin);
      setCurrentPreviewDraft({ type, filename });
      setIsPreviewOpen(true);
    } catch (error) {
      console.error('Error fetching template PDF:', error);
      handleSnackbarOpen('Failed to fetch the template preview. Please try again later.', 'error');
    } finally {
      setLoading(false);
    }
  };

  /**
   * handleOkInPreview
   * This function is called when the user clicks "Ok" in the preview dialog.
   * Depending on the origin of the preview, it either calls handleDraftItemSelection
   * (for "Get Drafts" origin) or simply closes the preview (for "Search Drafts" origin).
   */
  const handleOkInPreview = async () => {
    setIsPreviewOpen(false);
    if (previewOrigin === 'getDrafts' && currentPreviewDraft) {
      // Call handleDraftItemSelection to fetch fields and initialize the form
      await handleDraftItemSelection();
    }
    // If origin is 'searchDrafts', simply close the preview
  };

  // Utility function to fetch binary data from Blob URL
  const fetchPdfBytes = async (blobUrl) => {
    const response = await fetch(blobUrl);
    const arrayBuffer = await response.arrayBuffer();
    return arrayBuffer;
  };

  // Utility function to convert ArrayBuffer to Base64
  const arrayBufferToBase64 = (buffer) => {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
  };

  /**
   * handleLoadSavedDraft
   * This function handles loading a saved draft when selected from the "Saved Drafts" tab.
   * It sets the selected draft type and item, and triggers the preview.
   */
  const handleLoadSavedDraft = async (selected) => {
    if (!selected) return;
    setSelectedDraftType(selected.type);
    setSelectedDraftItem(selected.filename);
    // Trigger Preview
    await handlePreview(selected.type, selected.filename, null, 'getDrafts');
    // Switch to Get Drafts tab to view the form
    setCurrentTab(0);
  };

  // Handle Suggest Changes
  const handleSuggestChanges = () => {
    setIsSuggestingChanges(true);
  };

  // Submit Suggestion
  const submitSuggestion = async () => {
    if (!suggestionText.trim()) {
      handleSnackbarOpen('Please provide a suggestion or confirm the template.', 'warning');
      return;
    }

    // Enforce character limit
    if (suggestionText.length > 500) {
      handleSnackbarOpen('Suggestion exceeds the 500 character limit.', 'warning');
      return;
    }

    // Sanitize suggestion
    const sanitizedSuggestion = DOMPurify.sanitize(suggestionText, { ALLOWED_TAGS: [], ALLOWED_ATTR: {} });

    setIsCreatingNewDraft(true);
    setLoading(true);

    try {
      // Fetch the current PDF bytes as ArrayBuffer
      const pdfBytes = await fetchPdfBytes(pdfUrl); // ArrayBuffer
      const base64Pdf = arrayBufferToBase64(pdfBytes); // Base64 String

      // Prepare payload
      const payload = {
        type: selectedDraftType,
        filename: selectedDraftItem,
        suggestion: sanitizedSuggestion,
        pdf_bytes: base64Pdf, // Pass the PDF as a base64 string
      };

      // Make API call expecting binary data
      const response = await AxiosInstance.post(
        `drafts/get-updated-template/`,
        payload,
        { responseType: 'blob' } // Expect binary data
      );

      console.log('Response from get-updated-template:', response);

      // Create a Blob URL from the response
      const updatedPdfBlob = new Blob([response.data], { type: 'application/pdf' });
      const updatedPdfUrl = URL.createObjectURL(updatedPdfBlob);
      setPdfUrl(updatedPdfUrl);

      // Optionally, revoke the previous Blob URL
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }

      setSuggestionText('');
      handleSnackbarOpen('Draft updated based on your suggestion.', 'success');
    } catch (error) {
      console.error('Error updating template:', error);
      if (error.response && error.response.status === 400 && error.response.data.message === 'Max suggestions reached') {
        setIsMaxSuggestionsReached(true);
        handleSnackbarOpen('Maximum number of suggestions reached. Try our draft bot for building your own template.', 'info');
      } else {
        handleSnackbarOpen('Failed to update the draft. Please try again later.', 'error');
      }
    } finally {
      setIsCreatingNewDraft(false);
      setLoading(false);
      setIsSuggestingChanges(false);
    }
  };

  // Handle Show Preview from Search Results
  const handleShowPreviewFromSearch = async (result) => {
    const { draft_type, filename, pdf_bytes } = result;
    if (pdf_bytes) {
      // Assuming pdf_bytes is a URL to the PDF
      try {
        const response = await AxiosInstance.get(pdf_bytes, { responseType: 'blob' });
        const pdfBlobParam = new Blob([response.data], { type: 'application/pdf' });
        await handlePreview(draft_type, filename, pdfBlobParam, 'searchDrafts');
      } catch (error) {
        console.error('Error fetching PDF from search result:', error);
        handleSnackbarOpen('Failed to fetch the PDF preview. Please try again later.', 'error');
      }
    } else {
      try {
        await handlePreview(draft_type, filename, null, 'searchDrafts');
      } catch (error) {
        console.error('Error fetching template PDF:', error);
        handleSnackbarOpen('Failed to fetch the template preview. Please try again later.', 'error');
      }
    }
  };

  /**
   * handleSelectFromSearch
   * When a user selects a draft from search results, this function sets the selected draft type and item,
   * triggers the preview, and switches to the "Get Drafts" tab.
   */
  const handleSelectFromSearch = async (result) => {
    const { draft_type, filename } = result;
    setSelectedDraftType(draft_type || '');
    setSelectedDraftItem(filename || '');
    setFormFields({});
    setFormData({});
    setFormErrors({});
    setPdfUrl(null);
    setPdfBlob(null);
    setIsMaxSuggestionsReached(false);
    setZoomLevel(1.0); // Reset zoom level
    // Trigger Preview
    await handlePreview(draft_type, filename, null, 'getDrafts');
    // Switch to Get Drafts tab to view the form
    setCurrentTab(0);
  };

  // Render Preview Dialog
  const renderPreviewDialog = () => (
    <Dialog
      open={isPreviewOpen}
      onClose={() => setIsPreviewOpen(false)}
      fullWidth
      maxWidth="lg"
      aria-labelledby="preview-dialog-title"
    >
      <DialogTitle id="preview-dialog-title">Draft Preview</DialogTitle>
      <DialogContent dividers>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Zoom Controls */}
          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <IconButton
              onClick={() => setZoomLevel((prev) => Math.min(prev + 0.2, 3))}
              aria-label="Zoom In"
            >
              <ZoomInIcon />
            </IconButton>
            <IconButton
              onClick={() => setZoomLevel((prev) => Math.max(prev - 0.2, 0.5))}
              aria-label="Zoom Out"
            >
              <ZoomOutIcon />
            </IconButton>
          </Box>
          {/* PDF Viewer */}
          {pdfUrl ? (
            <Box
              sx={{
                width: '100%',
                height: '600px',
                overflow: 'auto',
                border: '1px solid #ccc',
                borderRadius: 1,
                transform: `scale(${zoomLevel})`,
                transformOrigin: 'top left',
              }}
            >
              <iframe
                src={pdfUrl}
                title="Draft Preview"
                width="100%"
                height="100%"
                style={{ border: 'none' }}
              ></iframe>
            </Box>
          ) : (
            <Typography variant="body1">Loading preview...</Typography>
          )}
          {/* Suggestion Box - Only for Get Drafts Origin */}
          {previewOrigin === 'getDrafts' && isSuggestingChanges ? (
            <TextField
              label="Your Suggestions"
              multiline
              rows={4}
              variant="outlined"
              fullWidth
              value={suggestionText}
              onChange={(e) => setSuggestionText(e.target.value)}
              placeholder="Provide your suggestions here (max 500 characters)."
              inputProps={{
                maxLength: 500,
              }}
              disabled={isCreatingNewDraft}
            />
          ) : previewOrigin === 'getDrafts' && !isSuggestingChanges ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
              <Typography variant="body1">
                Please confirm if the draft template is correct.
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                If not, you can suggest changes to modify the template.
              </Typography>
            </Box>
          ) : null}
        </Box>
      </DialogContent>
      <DialogActions>
        {!isMaxSuggestionsReached && previewOrigin === 'getDrafts' && (
          <>
            {isSuggestingChanges ? (
              <>
                <Button onClick={() => setIsSuggestingChanges(false)} disabled={isCreatingNewDraft}>
                  Cancel
                </Button>
                <Button onClick={submitSuggestion} color="secondary" disabled={isCreatingNewDraft}>
                  {isCreatingNewDraft ? <CircularProgress size={24} /> : 'Submit Suggestion'}
                </Button>
              </>
            ) : (
              <>
                <Button onClick={handleOkInPreview} disabled={isCreatingNewDraft}>
                  Ok
                </Button>
                <Button onClick={handleSuggestChanges} color="secondary" disabled={isCreatingNewDraft}>
                  Suggest Changes
                </Button>
              </>
            )}
          </>
        )}
        {previewOrigin === 'searchDrafts' && (
          <>
            <Button onClick={handleOkInPreview} color="primary">
              Ok
            </Button>
          </>
        )}
        {/* Close Button - Always Available */}
        <Button onClick={() => setIsPreviewOpen(false)} color="inherit">
          Close
        </Button>
        {/* Max Suggestions Reached - Show Draft Bot Option */}
        {isMaxSuggestionsReached && (
          <Box sx={{ padding: 2, textAlign: 'center' }}>
            <Typography variant="body1">
              You have reached the maximum number of suggestions. Please try our draft bot for building your own template.
            </Typography>
            <Button
              href="/draft-bot" // Placeholder URL; update as needed
              variant="contained"
              color="primary"
              sx={{ mt: 2 }}
            >
              Try Draft Bot
            </Button>
          </Box>
        )}
      </DialogActions>
    </Dialog>
  );

  return (
    <BackgroundBox>
      <Typography variant="h4" gutterBottom>
        Create Drafts
      </Typography>

      {/* Loading backdrop */}
      <Backdrop
        sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }}
        open={loading || isCreatingNewDraft}
      >
        <CircularProgress color="inherit" />
      </Backdrop>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>

      {/* Preview Dialog */}
      {renderPreviewDialog()}

      {/* Clear Confirmation Dialog */}
      <Dialog
        open={confirmClear}
        onClose={cancelClearForm}
        aria-labelledby="confirm-clear-dialog"
      >
        <DialogTitle id="confirm-clear-dialog">Clear Form</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to clear the form? All unsaved changes will be lost.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelClearForm}>Cancel</Button>
          <Button onClick={confirmClearForm} color="secondary">
            Clear
          </Button>
        </DialogActions>
      </Dialog>

      {/* Tabs for Navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={currentTab} onChange={handleTabChange} aria-label="Create Drafts Tabs" centered>
          <Tab label="Get Drafts" {...a11yProps(0)} />
          <Tab label="Search Drafts" {...a11yProps(1)} />
          <Tab label="Saved Drafts" {...a11yProps(2)} />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      <TabPanel value={currentTab} index={0}>
        {/* Get Drafts Tab Content */}
        <FormContainer elevation={3}>
          <Typography variant="h6" gutterBottom>
            Get Drafts
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth disabled={loading}>
                <InputLabel id="select-draft-type-label">
                  Select Draft Type
                </InputLabel>
                <Select
                  labelId="select-draft-type-label"
                  value={selectedDraftType}
                  onChange={handleDraftTypeChange}
                  label="Select Draft Type"
                >
                  <MenuItem value="" disabled>
                    <em>Select Draft Type</em>
                  </MenuItem>
                  {draftTypes.map((type, index) => (
                    <MenuItem key={index} value={type}>
                      {type}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {selectedDraftType && (
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth disabled={loading}>
                  <InputLabel id="select-draft-item-label">
                    Select Draft Item
                  </InputLabel>
                  <Select
                    labelId="select-draft-item-label"
                    value={selectedDraftItem}
                    onChange={(e) => {
                      setSelectedDraftItem(e.target.value);
                      setFormFields({});
                      setFormData({});
                      setFormErrors({});
                      setPdfUrl(null); // Clear previous PDF URL
                      setPdfBlob(null);
                      setIsMaxSuggestionsReached(false);
                      setZoomLevel(1.0); // Reset zoom level
                    }}
                    label="Select Draft Item"
                  >
                    <MenuItem value="" disabled>
                      <em>Select Draft Item</em>
                    </MenuItem>
                    {draftItems.map((item, index) => (
                      <MenuItem key={index} value={item}>
                        {item}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            )}
          </Grid>

          {/* Action Buttons */}
          <Box sx={{ marginTop: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
            <StyledButton
              variant="contained"
              onClick={() => handlePreview(selectedDraftType, selectedDraftItem)}
              disabled={!selectedDraftType || !selectedDraftItem || loading}
            >
              Preview
            </StyledButton>
            {(pdfUrl || pdfBlob) && (
              <StyledButton
                variant="contained"
                color="secondary"
                onClick={downloadPdf}
              >
                Download PDF
              </StyledButton>
            )}
          </Box>
        </FormContainer>

        {/* Form Fields */}
        {isFormLoaded && (
          <FormContainer elevation={3} ref={formContainerRef}>
            <Typography variant="h6" gutterBottom>
              Fill in the Details
            </Typography>
            <Grid container spacing={2}>
              {renderFormFields(formFields).map((field, index) => (
                <Grid item xs={12} key={index}>
                  {field}
                </Grid>
              ))}
            </Grid>
            <Box sx={{ marginTop: 2, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
              <StyledButton
                variant="contained"
                onClick={handleSubmit}
                disabled={loading}
              >
                Submit
              </StyledButton>
              <SaveButton
                variant="contained"
                onClick={autoSaveForm} // Save Button
                disabled={loading}
              >
                Save
              </SaveButton>
              <Button
                variant="outlined"
                color="secondary"
                onClick={handleClear}
              >
                Clear
              </Button>
              {(pdfUrl || pdfBlob) && (
                <StyledButton
                  variant="contained"
                  color="secondary"
                  onClick={downloadPdf}
                >
                  Download PDF
                </StyledButton>
              )}
            </Box>
          </FormContainer>
        )}
      </TabPanel>

      <TabPanel value={currentTab} index={1}>
        {/* Search Drafts Tab Content */}
        <SectionPaper elevation={3}>
          <Typography variant="h6" gutterBottom>
            Search Drafts
          </Typography>
          <SearchBox>
            <TextField
              fullWidth
              placeholder="Type keyword to search draft"
              variant="outlined"
              value={searchQuery}
              onChange={handleSearchInputChange}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={handleSearch}
                      disabled={!searchQuery || loading}
                      color="primary"
                      aria-label="search"
                    >
                      <SearchIcon />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              disabled={loading}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleSearch();
                }
              }}
            />
          </SearchBox>
          {loading && searchQuery && (
            <Box sx={{ display: 'flex', justifyContent: 'center', marginTop: 2 }}>
              <CircularProgress />
            </Box>
          )}
          {!loading && showSearchResults && (
            <>
              {searchResults.length > 0 ? (
                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Search Results
                  </Typography>
                  <List>
                    {searchResults.map((result, index) => (
                      <ListItem
                        key={index}
                        disablePadding
                        sx={{
                          flexDirection: 'column',
                          alignItems: 'stretch',
                          mb: 1,
                          border: '1px solid #e0e0e0',
                          borderRadius: 1,
                          padding: 1,
                        }}
                      >
                        <ListItemText
                          primary={
                            <Typography variant="subtitle1" fontWeight="bold">
                              {result.filename}
                            </Typography>
                          }
                          secondary={
                            typeof result.content_snippet === 'string' ? (
                              result.content_snippet
                            ) : (
                              <Box sx={{ display: 'flex', alignItems: 'center', color: 'text.secondary' }}>
                                <SentimentDissatisfiedIcon fontSize="small" sx={{ marginRight: 0.5 }} />
                                <Typography variant="body2">No content snippet available.</Typography>
                              </Box>
                            )
                          }
                        />
                        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 1 }}>
                          <Button
                            variant="outlined"
                            size="small"
                            onClick={() => handleShowPreviewFromSearch(result)}
                            disabled={loading}
                            sx={{ textTransform: 'none' }}
                          >
                            Show Preview
                          </Button>
                          <Button
                            variant="contained"
                            size="small"
                            onClick={() => handleSelectFromSearch(result)}
                            disabled={loading}
                            sx={{ textTransform: 'none' }}
                          >
                            Select
                          </Button>
                        </Box>
                      </ListItem>
                    ))}
                  </List>
                  <Box sx={{ marginTop: 2 }}>
                    <StyledButton
                      variant="outlined"
                      onClick={handleCancelSearch}
                      sx={{ textTransform: 'none' }}
                    >
                      Cancel
                    </StyledButton>
                  </Box>
                </Box>
              ) : (
                <Box sx={{ padding: 2, textAlign: 'center', color: 'text.secondary' }}>
                  <SentimentDissatisfiedIcon fontSize="large" />
                  <Typography variant="body1" color="textSecondary" sx={{ marginTop: 1 }}>
                    No search results found for "{searchQuery}".
                  </Typography>
                </Box>
              )}
            </>
          )}
        </SectionPaper>
      </TabPanel>

      <TabPanel value={currentTab} index={2}>
        {/* Saved Drafts Tab Content */}
        <SectionPaper elevation={3}>
          <Typography variant="h6" gutterBottom>
            Saved Drafts
          </Typography>
          <FormControl fullWidth disabled={loading || savedDrafts.length === 0}>
            <InputLabel id="select-saved-draft-label">Select Saved Draft</InputLabel>
            <Select
              labelId="select-saved-draft-label"
              value={selectedSavedDraft ? `${selectedSavedDraft.type} - ${selectedSavedDraft.filename}` : ''}
              onChange={(e) => {
                const selected = savedDrafts.find(
                  (draft) => `${draft.type} - ${draft.filename}` === e.target.value
                );
                setSelectedSavedDraft(selected);
                handleLoadSavedDraft(selected);
              }}
              label="Select Saved Draft"
            >
              {savedDrafts.length > 0 ? (
                savedDrafts.map((draft, index) => (
                  <MenuItem key={index} value={`${draft.type} - ${draft.filename}`}>
                    {`${draft.type} - ${draft.filename}`}
                  </MenuItem>
                ))
              ) : (
                <MenuItem value="" disabled>
                  <em>No Saved Drafts Available</em>
                </MenuItem>
              )}
            </Select>
          </FormControl>
        </SectionPaper>
      </TabPanel>

      {/* Additional Floating Buttons or Components can be added here if needed */}
    </BackgroundBox>
  );

  // Utility function to convert ArrayBuffer to Base64
  // function arrayBufferToBase64(buffer) {
  //   let binary = '';
  //   const bytes = new Uint8Array(buffer);
  //   const len = bytes.byteLength;
  //   for (let i = 0; i < len; i++) {
  //     binary += String.fromCharCode(bytes[i]);
  //   }
  //   return window.btoa(binary);
  // }
};

export default CreateDrafts;
