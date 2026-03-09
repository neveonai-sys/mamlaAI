// src/components/InitialQueryComponent.js
import React, { useState, useEffect, Suspense } from 'react';
import AxiosInstance from '../common/AxiosInstance';
import {
  Box,
  Typography,
  Snackbar,
  Alert,
  Tabs,
  Tab,
  Fade,
  CircularProgress,
} from '@mui/material';
import LoadingOverlay from '../common/LoadingOverlay';

// Lazy-loaded tab components
const CreateNewDraftTab = React.lazy(() => import('../tabs/CreateNewDraftTab'));
const LoadDraftTab = React.lazy(() => import('../tabs/LoadDraftTab'));
const LoadTemplateTab = React.lazy(() => import('../tabs/LoadTemplateTab'));

// A small helper for tab panels
function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`initial-query-tabpanel-${index}`}
      aria-labelledby={`initial-query-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

/**
 * Main initial entry point where user:
 * - Creates a new draft
 * - Loads an existing draft
 * - Loads or retrieves a template
 */
function InitialQueryComponent({ onSessionStarted, filterData, userType }) {
  // Add debug log
  useEffect(() => {
    console.log('InitialQueryComponent - userType:', userType);
    console.log('InitialQueryComponent - isClientUser:', userType === 'Client');
  }, [userType]);

  // Tab state
  const [tabIndex, setTabIndex] = useState(0);

  const [languagesList, setLanguagesList] = useState([]);
  const [selectedLanguage, setSelectedLanguage] = useState('English');

  // Common UI states
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Draft count limiting
  const [totalDrafts, setTotalDrafts] = useState(0);
  const MAX_DRAFTS = 20; // You can customize this

  // Check if the current user is a client
  const isClientUser = userType === 'Client';

  // -------------------------------------------------------
  // STATES FOR: "Create New Draft" TAB
  // -------------------------------------------------------
  const [userQuery, setUserQuery] = useState('');
  const [inputMethod, setInputMethod] = useState(null); // 'write' or 'upload'
  const [uploadFile, setUploadFile] = useState(null);
  const [selectedDraftFor, setSelectedDraftFor] = useState([]);
  const [selectedCaseIds, setSelectedCaseIds] = useState([]);
  const [selectedClientIds, setSelectedClientIds] = useState([]);
  const [selectedCaseClientIds, setSelectedCaseClientIds] = useState([]);

  // Optional location fields
  const [statesList, setStatesList] = useState([]);
  const [districtsList, setDistrictsList] = useState([]);
  const [courtsList, setCourtsList] = useState([]);
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedCourt, setSelectedCourt] = useState('');

  // -------------------------------------------------------
  // STATES FOR: "Load Draft" TAB
  // -------------------------------------------------------
  const [draftRows, setDraftRows] = useState([]);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [rowCount, setRowCount] = useState(0);
  const [searchField, setSearchField] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDraftId, setSelectedDraftId] = useState(null);
  const [selectedDraft, setSelectedDraft] = useState(null);

  // -------------------------------------------------------
  // STATES FOR: "Load Template" TAB
  // -------------------------------------------------------
  const [templateFile, setTemplateFile] = useState(null);
  const [draftType, setDraftType] = useState('');

  // PREVIEW STATES for the "Load Template" flow
  const [templateSessionId, setTemplateSessionId] = useState(null);
  const [templatePreviewSections, setTemplatePreviewSections] = useState(null);
  const [showTemplatePreview, setShowTemplatePreview] = useState(false);

  // Filter data
  const [filterDataState, setFilterDataState] = useState({
    caseIds_without_client: [],
    clientIds_without_case: [],
    case_client_map: {},
  });

  // -------------------------------------------------------
  // Fetch initial data on mount (filter data, total drafts, saved drafts)
  // -------------------------------------------------------
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // If filterData not passed from parent, fetch it
        if (!filterData) {
          const filterResponse = await AxiosInstance.get('users/filter_with_details/');
          setFilterDataState(filterResponse.data);
        } else {
          setFilterDataState(filterData);
        }

        // Fetch total draft count
        const totalResponse = await AxiosInstance.get('aidrafts/get-draft-count');
        setTotalDrafts(totalResponse.data.total_drafts);

       const langResp = await AxiosInstance.get('aidrafts/get_supported_languages');
        setLanguagesList(langResp.data.languages);
        setSelectedLanguage(
          langResp.data.languages.includes('English')
            ? 'English'
            : langResp.data.languages[0]
        );
          
      } catch (error) {
        console.error('Error fetching initial data:', error);
        setErrorMessage('Failed to fetch initial data.');
        setLoading(false);
        return;
      }

      // Fetch saved drafts for the "Load Draft" tab
      try {
        await fetchSavedDrafts();
      } catch (error) {
        console.error('Error fetching saved drafts:', error);
        setErrorMessage('Failed to fetch saved drafts.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // We include page, pageSize, searchField, searchQuery in the dependency array
    // because fetchSavedDrafts is dependent on them.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, searchField, searchQuery]);

  // Helper to fetch the user's saved drafts with pagination and searching
   const fetchSavedDrafts = async () => {
    try {
      const params = { page: page + 1, page_size: pageSize };
      if (searchField && searchQuery) {
        params.search_field = searchField;
        params.search_query = searchQuery;
      }

      const r = await AxiosInstance.get(
        'aidrafts/get_user_saved_drafts_v2',
        { params }
      );

      const rows = r.data.saved_drafts.map((d) => {
        /* draft_for can be {}, [], or list‑of‑dict – normalise to array */
        const dfArr = Array.isArray(d.draft_for)
          ? d.draft_for
          : (d.draft_for && Object.keys(d.draft_for).length ? [d.draft_for] : []);

        const get = (obj, ...k) =>
          k.reduce((acc, key) => acc || obj[key], '');

        const caseIds   = dfArr.map((x) => get(x, 'case_id', 'caseid')).filter(Boolean).join(', ');
        const clientIds = dfArr.map((x) => get(x, 'client_id', 'clientid')).filter(Boolean).join(', ');
        const names     = dfArr.map((x) => get(x, 'client_name', 'clientname')).filter(Boolean).join(', ');

        return {
          id              : d.draft_id,
          draft_name      : d.draft_name,
          session_id      : d.session_id,
          created_on      : d.created_on      ? new Date(d.created_on)      : null,
          last_updated_on : d.last_updated_on ? new Date(d.last_updated_on) : null,
          case_ids        : caseIds,
          client_ids      : clientIds,
          client_names    : names,
        };
      });

      setDraftRows(rows);
      setRowCount(r.data.pagination.total_count);
    } catch (e) {
      console.error(e);
      setErrorMessage('Failed to fetch saved drafts.');
    }
  };

  // When the user switches tabs
  const handleTabChange = (event, newValue) => {
    setTabIndex(newValue);
    setErrorMessage('');
    setSuccessMessage('');
    setSearchField('');
    setSearchQuery('');
    setSelectedDraftId(null);
    setSelectedDraft(null);
  };

  // -------------------------------------------------------
  // Populate list of states / districts / courts
  // -------------------------------------------------------
  useEffect(() => {
    const fetchStates = async () => {
      try {
        const resp = await AxiosInstance.get('users/get-states/');
        setStatesList(resp.data.states || []);
      } catch (err) {
        console.error('Error fetching states:', err);
      }
    };
    fetchStates();
  }, []);

  const handleSelectState = async (value) => {
    setSelectedState(value);
    setSelectedDistrict('');
    setSelectedCourt('');
    setDistrictsList([]);
    setCourtsList([]);

    if (!value) return;
    try {
      const resp = await AxiosInstance.get('users/get-districts/', {
        params: { state: value },
      });
      setDistrictsList(resp.data.districts || []);
    } catch (err) {
      console.error('Error fetching districts:', err);
    }
  };

  const handleSelectDistrict = async (value) => {
    setSelectedDistrict(value);
    setSelectedCourt('');
    setCourtsList([]);

    if (!value) return;
    try {
      const resp = await AxiosInstance.get('users/get-courts/', {
        params: { state: selectedState, district: value },
      });
      setCourtsList(resp.data.courts || []);
    } catch (err) {
      console.error('Error fetching courts:', err);
    }
  };

  const handleSelectCourt = (value) => {
    setSelectedCourt(value);
  };

  // -------------------------------------------------------
  // Data Grid columns for the "Load Draft" tab
  // -------------------------------------------------------
  const draftColumns = [
    { field:"draft_name", headerName:"Draft Name", flex:1, sortable:true },
    { field:"case_ids",     headerName:"Case ID(s)", flex:1, sortable:false },
    { field:"client_names", headerName:"Client Name(s)", flex:1.5, sortable:false },
    { field:"created_on", headerName:"Created On", type:"dateTime", flex:1, sortable:true },
    { field:"last_updated_on", headerName:"Last Updated On", type:"dateTime", flex:1, sortable:true },
  ];

  // -------------------------------------------------------
  // Download a blank sample template from the server
  // -------------------------------------------------------
  const downloadTemplate = async () => {
    setLoading(true);
    try {
      const response = await AxiosInstance.get('aidrafts/download_template', {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      let fileName = 'template.docx';
      const contentDisposition = response.headers['content-disposition'];
      if (contentDisposition) {
        const fileNameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (fileNameMatch && fileNameMatch[1]) {
          fileName = fileNameMatch[1];
        }
      }

      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);

      console.log('Template downloaded successfully.');
      setSuccessMessage('Template downloaded successfully.');
    } catch (error) {
      console.error('Error downloading template:', error);
      if (error.response) {
        setErrorMessage(error.response.data.error || 'Failed to download template.');
      } else if (error.request) {
        setErrorMessage('No response from server. Check your connection.');
      } else {
        setErrorMessage('An unexpected error occurred.');
      }
    } finally {
      setLoading(false);
    }
  };

  // -------------------------------------------------------
  // "Load Draft" tab: handle loading the user’s selected draft
  // -------------------------------------------------------
  const handleLoadSavedDraft = async () => {
    if (!selectedDraft) {
      setErrorMessage('Please select a draft.');
      return;
    }
      console.log("selectedDraft ===>>", selectedDraft)
    setLoading(true);
    try {
      const response = await AxiosInstance.get('aidrafts/load_saved_draft', {
        params: {
          session_id: selectedDraft.session_id,
          draft_id: selectedDraft.id,
        },
      });
      const draftSections = response.data.draft_sections;
      console.log('Draft sections loaded:', draftSections);

      if (!draftSections || draftSections.length === 0) {
        setErrorMessage('No draft sections found.');
        return;
      }
        const loadedDraftName = selectedDraft.draft_name || 'Untitled Draft';
        const loadedDraftId = selectedDraft.id;
      // Immediately pass them to the parent
      onSessionStarted(selectedDraft.session_id, draftSections, loadedDraftName, loadedDraftId);
      setSuccessMessage('Draft loaded successfully!');
    } catch (error) {
      console.error('Error loading saved draft:', error);
      if (error.response) {
        setErrorMessage(error.response.data.error || 'Failed to load saved draft.');
      } else if (error.request) {
        setErrorMessage('No response from server. Check your connection.');
      } else {
        setErrorMessage('An unexpected error occurred.');
      }
    } finally {
      setLoading(false);
    }
  };

  // -------------------------------------------------------
  // "Create New Draft" tab: handle the user’s request
  // -------------------------------------------------------
  const handleSubmitQuery = async (draftFor = []) => {
    if (loading) return;
    
    try {
      setLoading(true);
      setErrorMessage('');
      setSuccessMessage('');

      // For client users, ensure they can't specify draft_for
      const draft_for = isClientUser ? [] : draftFor;
      
      // Validate write vs. upload
      if (inputMethod === 'write' && userQuery.trim().length < 10) {
        setErrorMessage('Please enter at least 10 characters for a detailed description.');
        return;
      }
      if (inputMethod === 'upload' && !uploadFile) {
        setErrorMessage('Please upload a relevant document.');
        return;
      }
      if (!inputMethod) {
        setErrorMessage('Please select “Write” or “Upload” as your input method.');
        return;
      }

      // Build location
      const locationObj = {};
      if (selectedState)    locationObj.state    = selectedState;
      if (selectedDistrict) locationObj.district = selectedDistrict;
      if (selectedCourt)    locationObj.court    = selectedCourt;

      setLoading(true);
      try {
        let resp;                                        // <-- FIX: single scoped response
        if (inputMethod === 'upload') {
          const formData = new FormData();
          formData.append('file', uploadFile);
          formData.append('draft_for', JSON.stringify(draft_for));
          formData.append('location',  JSON.stringify(locationObj));
          formData.append('language',  selectedLanguage);

          resp = await AxiosInstance.post(
            'aidrafts/start_session_for_casedocument',
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
          );
        } else {
          resp = await AxiosInstance.post('aidrafts/start_session', {
            user_query: userQuery,
            draft_for : draft_for,
            location  : locationObj,
            language  : selectedLanguage,
          });
        }

        const { session_id, draft_name, draft_id, draft_for: responseDraftFor } = resp.data;
        onSessionStarted(session_id, null, draft_name, draft_id, responseDraftFor);
        setSuccessMessage('Session started successfully!');

        // reset only the things we need
        setInputMethod(null);
        setUserQuery('');
        setUploadFile(null);
        setSelectedState('');
        setSelectedDistrict('');
        setSelectedCourt('');
        setDistrictsList([]);
        setCourtsList([]);
        setTotalDrafts(c => c + 1);
      } catch (err) {
        console.error(err);
        setErrorMessage(err.response?.data?.error || 'Failed to start session.');
      } finally {
        setLoading(false);
      }
    } catch (error) {
      console.error('Error submitting query:', error);
      setErrorMessage('Failed to submit query.');
    }
  };

  // -------------------------------------------------------
  // "Load Template" tab: handle uploading a template
  // -------------------------------------------------------
  // Inside InitialQueryComponent (parent)
const handleUploadTemplate = async (data) => {
  try {
    setLoading(true);

    if (data.existingTemplate) {
      // Skip the local file checks
      if (!data.chosenDraftType) {
        setErrorMessage('Please select Draft Type from the dropdown.');
        return;
      }
      if (!data.chosenDraftName) {
        setErrorMessage('Please select Draft Name.');
        return;
      }

      // Build FormData or do anything your server needs
      const formData = new FormData();
      formData.append('draft_type', data.chosenDraftType);
      formData.append('existing_template_name', data.chosenDraftName);
        // console.log("handleUploadTemplate ===== data", data)
      // If data.draft_for is provided, pass it along so the backend can store it
      if (data.draft_for) {
        formData.append('draft_for', JSON.stringify(data.draft_for));
      }

      // Actually call your backend
      const response = await AxiosInstance.post('aidrafts/upload_template', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const sessionId = response.data.session_id;
      onSessionStarted(sessionId);
      setSuccessMessage('Existing template processed successfully!');

    } else {
      // User is uploading a local file
      // Use your existing checks
      if (!data.chosenDraftType.trim()) {
        setErrorMessage('Please enter the type of draft.');
        return;
      }
      if (!data.file) {
        setErrorMessage('Please upload a template file.');
        return;
      }

      const formData = new FormData();
      formData.append('draft_type', data.chosenDraftType);
      formData.append('file', data.file);

      // If data.draft_for is provided, pass it along so the backend can store it
      if (data.draft_for) {
        formData.append('draft_for', JSON.stringify(data.draft_for));
      }

      const response = await AxiosInstance.post('aidrafts/upload_template', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const sessionId = response.data.session_id;
      onSessionStarted(sessionId);
      setSuccessMessage('Template uploaded and processed successfully!');
    }
  } catch (error) {
    console.error('Error uploading template:', error);
    setErrorMessage('Failed to process template. Please try again.');
  } finally {
    setLoading(false);
  }
};


  // -------------------------------------------------------
  // Confirm or cancel the template preview
  // -------------------------------------------------------
  const handleConfirmTemplatePreview = () => {
    if (!templateSessionId || !templatePreviewSections) {
      setErrorMessage('No template session or sections to confirm.');
      return;
    }
    // Pass them along to the parent’s drafting flow
    onSessionStarted(templateSessionId, templatePreviewSections);
    // Reset
    setTemplateSessionId(null);
    setTemplatePreviewSections(null);
    setShowTemplatePreview(false);
    setDraftType('');
    setTemplateFile(null);
    // Optionally increment totalDrafts
    setTotalDrafts((prevCount) => prevCount + 1);
  };

  const handleCancelTemplatePreview = () => {
    // Discard the preview and session references
    setTemplateSessionId(null);
    setTemplatePreviewSections(null);
    setShowTemplatePreview(false);
    // Don’t necessarily remove it from DB, but you could call an endpoint to cancel
  };

  // -------------------------------------------------------
  // Render
  // -------------------------------------------------------
  const renderTabContent = () => {
    if (loading) {
      return (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <CircularProgress />
        </Box>
      );
    }

    return (
      <Suspense fallback={
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <CircularProgress />
        </Box>
      }>
        {tabIndex === 0 && (
          <CreateNewDraftTab
            userQuery={userQuery}
            setUserQuery={setUserQuery}
            inputMethod={inputMethod}
            setInputMethod={setInputMethod}
            uploadFile={uploadFile}
            setUploadFile={(f) => { setUploadFile(f); if (f) setErrorMessage(''); }}
            handleSubmitQuery={handleSubmitQuery}
            filterDataState={filterDataState}
            
            statesList={statesList}
            districtsList={districtsList}
            courtsList={courtsList}
            selectedState={selectedState}
            handleSelectState={handleSelectState}
            selectedDistrict={selectedDistrict}
            handleSelectDistrict={handleSelectDistrict}
            selectedCourt={selectedCourt}
            handleSelectCourt={handleSelectCourt}
            
            downloadTemplate={downloadTemplate}
            loading={loading}
            setErrorMessage={setErrorMessage}
            
            languagesList={languagesList}
            selectedLanguage={selectedLanguage}
            setSelectedLanguage={setSelectedLanguage}
            isClientUser={isClientUser}
          />
        )}
        {tabIndex === 1 && (
          <LoadDraftTab
            // Props for "LoadDraftTab"
            draftRows={draftRows}
            page={page}
            setPage={setPage}
            pageSize={pageSize}
            setPageSize={setPageSize}
            rowCount={rowCount}
            searchField={searchField}
            setSearchField={setSearchField}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            handleLoadSavedDraft={handleLoadSavedDraft}
            selectedDraftId={selectedDraftId}
            setSelectedDraftId={setSelectedDraftId}
            selectedDraft={selectedDraft}
            setSelectedDraft={setSelectedDraft}
            draftColumns={draftColumns}
            loading={loading}
          />
        )}
        {tabIndex === 2 && (
          <LoadTemplateTab
            // Add debug log for props
            onMount={() => {
              console.log('LoadTemplateTab mounted with isClientUser:', userType === 'Client');
            }}
            // Props for "LoadTemplateTab"
            draftType={draftType}
            setDraftType={setDraftType}
            templateFile={templateFile}
            setTemplateFile={(f) => {
              setTemplateFile(f);
              if (f) setErrorMessage('');
            }}
            handleUploadTemplate={handleUploadTemplate}
            onConfirmTemplatePreview={handleConfirmTemplatePreview}
            onCancelTemplatePreview={handleCancelTemplatePreview}
            previewSections={templatePreviewSections}
            showPreview={showTemplatePreview}
            loading={loading}
            filterDataState={filterDataState}
            setErrorMessage={setErrorMessage}
            isClientUser={userType === 'Client'}
          />
        )}
      </Suspense>
    );
  };

  return (
    <Box
      sx={{
        maxWidth: 1200,
        margin: '0 auto',
        padding: 4,
        boxShadow: 3,
        borderRadius: 2,
        backgroundColor: '#fff',
      }}
    >
      <LoadingOverlay open={loading} message="Processing..." />

      {/* Error Snackbar */}
      <Snackbar
        open={Boolean(errorMessage)}
        autoHideDuration={6000}
        onClose={() => setErrorMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        TransitionComponent={Fade}
      >
        <Alert
          onClose={() => setErrorMessage('')}
          severity="error"
          sx={{ width: '100%' }}
        >
          {errorMessage}
        </Alert>
      </Snackbar>

      {/* Success Snackbar */}
      <Snackbar
        open={Boolean(successMessage)}
        autoHideDuration={6000}
        onClose={() => setSuccessMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        TransitionComponent={Fade}
      >
        <Alert
          onClose={() => setSuccessMessage('')}
          severity="success"
          sx={{ width: '100%' }}
        >
          {successMessage}
        </Alert>
      </Snackbar>

      {/* Tabs header */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={tabIndex}
          onChange={handleTabChange}
          aria-label="Initial Query Tabs"
          variant="fullWidth"
          sx={{
            '& .MuiTabs-indicator': { backgroundColor: '#1976d2' },
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 500,
            },
          }}
        >
          {/* Create New Draft */}
          <Tab
            label={
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography variant="subtitle2">Create New Draft</Typography>
                {totalDrafts < MAX_DRAFTS ? (
                  <Typography variant="caption" sx={{ marginLeft: '8px', color: 'gray' }}>
                    ({totalDrafts}/{MAX_DRAFTS})
                  </Typography>
                ) : (
                  <Typography variant="caption" sx={{ marginLeft: '8px', color: 'red' }}>
                    - Please Go Premium
                  </Typography>
                )}
              </Box>
            }
            id="initial-query-tab-0"
            disabled={totalDrafts >= MAX_DRAFTS}
          />
          {/* Load Draft */}
          <Tab label="Load Draft" id="initial-query-tab-1" />
          {/* Load Template */}
          <Tab label="Load Template" id="initial-query-tab-2" />
        </Tabs>
      </Box>

      {/* TAB PANELS */}
      <Box mt={2}>
        {renderTabContent()}
      </Box>
    </Box>
  );
}

export default InitialQueryComponent;
