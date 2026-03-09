// src/components/DraftViewerComponent.js

import React, { useState, useEffect } from 'react';
import DraftSectionEditor from './DraftSectionEditor';
import SectionHistory from './SectionHistory';
import SaveDraft from './SaveAIDraft'; // Import SaveDraft component
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import {
  Box,
  Typography,
  Button,
  Paper,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Fade,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Tooltip,
  TextField,
  IconButton,
  Popper,
} from '@mui/material';
import AxiosInstance from '../common/AxiosInstance';
import LoadingOverlay from '../common/LoadingOverlay';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`draft-viewer-tabpanel-${index}`}
      aria-labelledby={`draft-viewer-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index) {
  return {
    id: `draft-viewer-tab-${index}`,
    'aria-controls': `draft-viewer-tabpanel-${index}`,
  };
}

function DraftViewerComponent({ sessionId, draftSections: initialDraftSections, existingDraftName, existingSavedDraftId, draftFor }) {
  const [draftSections, setDraftSections] = useState(initialDraftSections || []);
  const [selectedSection, setSelectedSection] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [confirmRevert, setConfirmRevert] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  /* --- add a local state for name (rename stays via SaveDraft) --- */
  const [draftName, setDraftName] = useState(existingDraftName || '');
  
  // State for Tabs
  const [tabIndex, setTabIndex] = useState(0);

  // New State Variables for draft_for
  const [draftForData, setDraftForData] = useState({});
  const [buttonStates, setButtonStates] = useState({}); // To track button disabled states

  // New State Variables for AI Suggestions
  const [aiSuggestionCount, setAiSuggestionCount] = useState(0); // Number of AI suggestions used
  const MAX_AI_SUGGESTIONS = 7; // Maximum allowed AI suggestions

  /* if parent later supplies newer name via props we sync once */
  useEffect(() => { setDraftName(existingDraftName); }, [existingDraftName]);

   const [anchorEl, setAnchorEl] = useState(null);
   const handlePopoverOpen  = (e) => setAnchorEl(e.currentTarget);
   const handlePopoverClose = ()  => setAnchorEl(null);
   const popoverOpen        = Boolean(anchorEl);
  
   // normalise draft_for into a simple array‑of‑objects
   const [popAnchor, setPopAnchor] = useState(null);
   const openPop = Boolean(popAnchor);
   const handleOpenPop  = (e) => setPopAnchor(e.currentTarget);
   const handleClosePop = () => setPopAnchor(null);
   const draftForRows = React.useMemo(() => {
     if (!draftForData) return [];
     if (Array.isArray(draftForData)) return draftForData;
     return Object.values(draftForData);
   }, [draftForData]);

  /* ---------- fetch when prop not supplied ---------- */
  useEffect(() => {
    if (draftFor) return;               // already have it
    (async () => {
      try {
        const r = await AxiosInstance.get('aidrafts/get_draft_for', {
          params: { session_id: sessionId }
        });
        setDraftForData(r.data.draft_for || {});
        const initBtns = {};
        Object.keys(r.data.draft_for || {}).forEach(
          k => (initBtns[k] = { publish:false, mail:false })
        );
        setButtonStates(initBtns);
      } catch (err) {
        console.error('Error fetching draft_for data:', err);
        setErrorMessage('Failed to fetch draft details.');
      }
    })();
  }, [sessionId, draftFor]);

  // Fetch draft sections if not provided
  useEffect(() => {
    if (initialDraftSections && initialDraftSections.length > 0) {
      console.log('Initial draft sections provided:', initialDraftSections);
      setDraftSections(initialDraftSections);
      // Initialize AI suggestion count from initialDraftSections
      // Assuming each section has an 'ai_suggested_update_count'
      const totalAiSuggestions = initialDraftSections.reduce((acc, section) => {
        return acc + (section.ai_suggested_update_count || 0);
      }, 0);
      setAiSuggestionCount(totalAiSuggestions);
    } else if (sessionId) {
      const fetchDraftSections = async () => {
        setLoading(true);
        setLoadingMessage('Fetching your draft sections...');
        try {
          const response = await AxiosInstance.get(`aidrafts/get_draft_sections`, {
            params: { session_id: sessionId },
          });
          setDraftSections(response.data.draft_sections);
          console.log('Draft sections fetched from API:', response.data.draft_sections);
          
          // Initialize AI suggestion count from API response
          // Assuming the API returns 'ai_suggested_update_count' for the session
          setAiSuggestionCount(response.data.ai_suggested_update_count || 0);
        } catch (error) {
          console.error('Error fetching draft sections:', error);
          setErrorMessage('Failed to fetch draft sections. Please try again.');
        } finally {
          setLoading(false);
          setLoadingMessage('');
        }
      };

      fetchDraftSections();
    }
  }, [sessionId, initialDraftSections]);


   // ↓ local loading flag for the save‑rename action
    const [savingName, setSavingName] = useState(false);
    
    /* -- handler that re‑uses your existing save‑draft endpoint -- */
    const handleInlineSave = async () => {
      if (!draftName.trim()) return;
      try {
        setSavingName(true);
        await AxiosInstance.post('aidrafts/save_draft', {
          session_id     : sessionId,
          draft_name     : draftName.trim(),
          draft_sections : draftSections,
          draft_for      : draftForData,
          draft_id       : existingSavedDraftId,   // update if it exists
        });
        setSuccessMessage('Draft saved successfully.');
      } catch (err) {
        console.error(err);
        setErrorMessage(
          err.response?.data?.error || 'Failed to save draft name.'
        );
      } finally {
        setSavingName(false);
      }
    };

  // Handle Tab Change
  const handleTabChange = (event, newValue) => {
    setTabIndex(newValue);
    setErrorMessage(''); // Clear any existing error messages when switching tabs
    setSuccessMessage(''); // Clear any existing success messages when switching tabs
  };

  // Handle Section Update (from child component)
  const handleSectionUpdate = async (sectionId, updatedSection) => {
    console.log(`Updating section ${sectionId} with:`, updatedSection);
    const previousSections = [...draftSections];

    // Optimistically update the UI
    setDraftSections((prevSections) =>
      prevSections.map((s) =>
        s.section_id === sectionId ? { ...s, ...updatedSection } : s
      )
    );

    // Reset buttonStates to enable buttons again
    setButtonStates((prevStates) => {
      const resetStates = { ...prevStates };
      Object.keys(resetStates).forEach((key) => {
        resetStates[key] = { publish: false, mail: false };
      });
      return resetStates;
    });

    try {
      // Send update request to the backend
      await AxiosInstance.post(`aidrafts/update_section`, {
        session_id: sessionId,
        section_id: sectionId,
        section_name: updatedSection.section_name,
        content: updatedSection.content,
      });

      console.log('Section updated successfully.');
      setSuccessMessage('Section updated successfully.');
    } catch (error) {
      console.error('Error updating section:', error);
      setErrorMessage('Failed to update section. Please try again.');
      setDraftSections(previousSections); // Revert to previous state
    }
  };

  // Handle Section Deletion (from child component)
  const handleSectionDelete = async (sectionId) => {
    console.log(`Deleting section ${sectionId}`);
    // Optimistically remove the section from the UI
    const previousSections = [...draftSections];
    setDraftSections((prevSections) =>
      prevSections.filter((s) => s.section_id !== sectionId)
    );

    // Reset buttonStates to enable buttons again
    setButtonStates((prevStates) => {
      const resetStates = { ...prevStates };
      Object.keys(resetStates).forEach((key) => {
        resetStates[key] = { publish: false, mail: false };
      });
      return resetStates;
    });

    try {
      await AxiosInstance.post(`aidrafts/delete_section`, {
        session_id: sessionId,
        section_id: sectionId,
      });
      console.log('Section deleted successfully.');
      setSuccessMessage('Section deleted successfully.');
    } catch (error) {
      console.error('Error deleting section:', error);
      setErrorMessage('Failed to delete section. Please try again.');
      // Revert to previous state
      setDraftSections(previousSections);
    }
  };

  // Handle Drag End for Reordering Sections
  const handleDragEnd = async (result) => {
    if (!result.destination) return;

    const reorderedSections = Array.from(draftSections);
    const [movedSection] = reorderedSections.splice(result.source.index, 1);
    reorderedSections.splice(result.destination.index, 0, movedSection);

    // Optimistically update the UI
    setDraftSections(reorderedSections);

    // Reset buttonStates to enable buttons again
    setButtonStates((prevStates) => {
      const resetStates = { ...prevStates };
      Object.keys(resetStates).forEach((key) => {
        resetStates[key] = { publish: false, mail: false };
      });
      return resetStates;
    });

    // Show loading overlay
    setLoading(true);
    setLoadingMessage('Updating section order...');

    try {
      await AxiosInstance.post(`aidrafts/update_section_order`, {
        session_id: sessionId,
        draft_sections: reorderedSections,
      });
      console.log('Section order updated successfully.');
      setSuccessMessage('Section order updated successfully.');
    } catch (error) {
      console.error('Error updating section order:', error);
      setErrorMessage('Failed to update section order. Please try again.');
      // Revert to previous order
      setDraftSections(draftSections);
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  // Handle Adding a New Section
  const handleAddSection = async () => {
    const sectionName = prompt('Enter section name:');
    if (!sectionName) return;

    console.log(`Adding new section: ${sectionName}`);
    // Create a temporary section for optimistic UI
    const tempSection = {
      section_id: 'temp-' + Date.now(),
      section_name: sectionName,
      content: '',
    };

    // Optimistically add the section to the UI
    setDraftSections((prevSections) => [...prevSections, tempSection]);

    // Reset buttonStates to enable buttons again
    setButtonStates((prevStates) => {
      const resetStates = { ...prevStates };
      Object.keys(resetStates).forEach((key) => {
        resetStates[key] = { publish: false, mail: false };
      });
      return resetStates;
    });

    // Show loading overlay
    setLoading(true);
    setLoadingMessage('Adding a new section...');

    try {
      const response = await AxiosInstance.post(`aidrafts/add_section`, {
        session_id: sessionId,
        section_name: sectionName,
        content: '',
      });
      console.log('Section added successfully:', response.data.section);
      // Replace temporary section with the one from backend
      setDraftSections((prevSections) =>
        prevSections.map((s) =>
          s.section_id === tempSection.section_id ? response.data.section : s
        )
      );
      setSuccessMessage('Section added successfully.');
    } catch (error) {
      console.error('Error adding section:', error);
      setErrorMessage('Failed to add section. Please try again.');
      // Remove the temporary section
      setDraftSections((prevSections) =>
        prevSections.filter((s) => s.section_id !== tempSection.section_id)
      );
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  // Handle Downloading the Draft
  const handleDownload = async () => {
    setLoading(true);
    setLoadingMessage('Preparing your draft for download...');

    try {
      const response = await AxiosInstance.get(`aidrafts/download_draft`, {
        params: { session_id: sessionId },
        responseType: 'blob', // Important for handling binary data
      });

      // Create a URL for the blob
      const url = window.URL.createObjectURL(new Blob([response.data]));

      // Create a link and trigger the download
      const link = document.createElement('a');
      link.href = url;

      // Attempt to extract filename from headers
      const contentDisposition = response.headers['content-disposition'];
      let fileName = 'legal_draft.docx'; // Default filename

      if (contentDisposition) {
        const fileNameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (fileNameMatch && fileNameMatch[1]) {
          fileName = fileNameMatch[1];
        }
      }

      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();

      // Clean up and remove the link
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);

      console.log('Draft downloaded successfully.');
      setSuccessMessage('Draft downloaded successfully.');
    } catch (error) {
      console.error('Error downloading draft:', error);
      setErrorMessage('Failed to download draft. Please try again.');
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  // Handle Reverting to Original Draft
  const handleRevertToOriginal = async () => {
    // Show confirmation dialog
    setConfirmRevert(true);
  };

  const confirmRevertAction = async () => {
    setConfirmRevert(false);
    setLoading(true);
    setLoadingMessage('Reverting to original draft...');

    try {
      await AxiosInstance.post(`aidrafts/revert_to_original`, {
        session_id: sessionId,
      });
      const response = await AxiosInstance.get(`aidrafts/get_draft_sections`, {
        params: { session_id: sessionId },
      });
      setDraftSections(response.data.draft_sections);
      console.log('Reverted to original draft successfully.');
      setSuccessMessage('Reverted to original draft successfully.');
      
      // Reset buttonStates since we've reverted to the original
      setButtonStates((prevStates) => {
        const resetStates = { ...prevStates };
        Object.keys(resetStates).forEach((key) => {
          resetStates[key] = { publish: false, mail: false };
        });
        return resetStates;
      });

      // Reset AI suggestion count
      setAiSuggestionCount(response.data.ai_suggested_update_count || 0);
    } catch (error) {
      console.error('Error reverting to original:', error);
      setErrorMessage('Failed to revert to original draft. Please try again.');
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  const cancelRevertAction = () => {
    setConfirmRevert(false);
  };

  // Handle Showing Section History
  const handleShowHistory = (sectionId) => {
    const section = draftSections.find((s) => s.section_id === sectionId);
    setSelectedSection(section);
  };

  const handleCloseHistory = () => {
    setSelectedSection(null);
  };

  // New Handlers for Publish and Mail Buttons
  const handlePublishToUser = async (draftForType, data) => {
    // Placeholder: Currently disabled and does nothing
    // Future implementation can be added here
    console.log(`Publishing draft for ${draftForType}:`, data);
    setSuccessMessage(`Draft for ${draftForType} published successfully.`);
    // Disable only the publish button for this draftForType
    setButtonStates((prevStates) => ({
      ...prevStates,
      [draftForType]: { ...prevStates[draftForType], publish: true },
    }));
  };

  const handleSaveDraft = async () => {
    if (!draftName.trim()) { setErrorMessage('Draft name cannot be empty.'); return; }

    setLoading(true); setLoadingMessage('Saving draft…');
    try {
      const payload = {
        session_id     : sessionId,
        draft_name     : draftName.trim(),
        draft_sections : draftSections,
        draft_for      : draftForData,
      };
      if (existingSavedDraftId) payload.draft_id = existingSavedDraftId;

      await AxiosInstance.post('aidrafts/save_draft', payload);
      setSuccessMessage('Draft saved successfully.');
    } catch (e) {
      console.error(e);
      setErrorMessage(e.response?.data?.error || 'Failed to save draft.');
    } finally {
      setLoading(false); setLoadingMessage('');
    }
  };

  const handleMailToUser = async (draftForType, data) => {
    // Send API request to backend to mail the draft
    setLoading(true);
    setLoadingMessage(`Sending draft to user for ${draftForType}...`);
    try {
      await AxiosInstance.post(`aidrafts/mail_to_user`, {
        session_id: sessionId,
        draft_for_type: draftForType,
        data: data, // This could be user_id or case_id depending on draftForType
      });
      console.log(`Draft for ${draftForType} mailed successfully.`);
      setSuccessMessage(`Draft for ${draftForType} mailed successfully.`);
      // Disable only the mail button for this draftForType
      setButtonStates((prevStates) => ({
        ...prevStates,
        [draftForType]: { ...prevStates[draftForType], mail: true },
      }));
    } catch (error) {
      console.error(`Error mailing draft for ${draftForType}:`, error);
      setErrorMessage(`Failed to mail draft for ${draftForType}. Please try again.`);
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  // New Handler for AI Suggestion Count
  const handleAiSuggestionMade = () => {
    setAiSuggestionCount((prevCount) => prevCount + 1);
  };

  return (
    <Box sx={{ mt: 3, position: 'relative' }}>
      {/* Loading Overlay */}
      <LoadingOverlay open={loading} message={loadingMessage} />

      <Box
        sx={{
          mb: 2,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 2,
        }}
      >
        {/* file‑name as editable field */}
        <TextField
          variant="standard"
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') handleInlineSave();
          }}
          sx={{ minWidth: 220 }}
          InputProps={{ sx: { fontSize: 24, fontWeight: 500 } }}
        />
        <Button
          variant="contained"
          size="small"
          onClick={handleInlineSave}
          disabled={savingName}
        >
          {savingName ? 'Saving…' : 'Save'}
        </Button>
      
        {/* Draft‑For viewer (only if we have entries) */}
        {draftForRows.length > 0 && (
          <>
            <IconButton
              size="small"
              onMouseEnter={handleOpenPop}
              onMouseLeave={handleClosePop}
              onClick={openPop ? handleClosePop : handleOpenPop} // mobile
            >
              <InfoOutlinedIcon />
            </IconButton>
      
            <Popper
              open={openPop}
              anchorEl={popAnchor}
              onMouseEnter={handleOpenPop}
              onMouseLeave={handleClosePop}
              placement="bottom-end"
              sx={{ zIndex: 1300 }}
            >
              <Paper sx={{ p: 1, maxWidth: 300 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Case&nbsp;ID</strong></TableCell>
                      <TableCell><strong>Client&nbsp;Name</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {draftForRows.map((r, i) => (
                      <TableRow key={i}>
                        <TableCell>{r.case_id ?? r.caseid ?? '-'}</TableCell>
                        <TableCell>{r.client_name ?? r.clientname ?? '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Paper>
            </Popper>
          </>
        )}
      </Box>

      {/* Error Notification Snackbar */}
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

      {/* Success Notification Snackbar */}
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

      {/* Confirmation Dialog for Reverting Draft */}
      <Dialog
        open={confirmRevert}
        onClose={cancelRevertAction}
        aria-labelledby="revert-dialog-title"
        aria-describedby="revert-dialog-description"
      >
        <DialogTitle id="revert-dialog-title">Confirm Revert</DialogTitle>
        <DialogContent>
          <DialogContentText id="revert-dialog-description">
            Are you sure you want to revert to the original draft? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelRevertAction}>Cancel</Button>
          <Button onClick={confirmRevertAction} color="error" autoFocus>
            Revert
          </Button>
        </DialogActions>
      </Dialog>

      {/* AI Suggestions Count and Upgrade Message */}
      <Box sx={{ mb: 2 }}>
        {aiSuggestionCount < MAX_AI_SUGGESTIONS ? (
          <Typography variant="subtitle1">
            AI Suggestions Remaining: {MAX_AI_SUGGESTIONS - aiSuggestionCount}
          </Typography>
        ) : (
          <Typography variant="subtitle1" color="error">
            You have reached the maximum number of AI suggestions ({MAX_AI_SUGGESTIONS}).
            <Box component="span" sx={{ ml: 1 }}>
              Please go <strong>Premium</strong> for more AI suggestions with Mamla.AI Magic.
            </Box>
          </Typography>
        )}
      </Box>

      {/* Tabs for Navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={tabIndex}
          onChange={handleTabChange}
          aria-label="Draft Viewer Tabs"
          variant="fullWidth"
          sx={{
            '& .MuiTabs-indicator': {
              backgroundColor: '#1976d2', // Customize the indicator color
            },
            '& .MuiTab-root': {
              textTransform: 'none', // Prevent uppercase transformation
              fontWeight: 500,
            },
          }}
        >
          <Tab label="Draft Sections" {...a11yProps(0)} />
          <Tab disabled label="Publish or Mail (Upcoming feature)" {...a11yProps(1)} />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      <TabPanel value={tabIndex} index={0}>
        {/* Draft Sections Content */}
        <Box>
          <Typography variant="h5" gutterBottom>
            Your Draft
          </Typography>
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="sections">
              {(provided) => (
                <Box
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                >
                  {draftSections.map((section, index) => (
                    <Draggable
                      key={section.section_id} // Ensure unique key
                      draggableId={String(section.section_id)} // Must be a string
                      index={index}
                    >
                      {(provided) => (
                        <Fade in={true}>
                          <Paper
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            {...provided.dragHandleProps}
                            sx={{ padding: 2, mb: 2 }}
                            elevation={3}
                          >
                            <DraftSectionEditor
                              sessionId={sessionId}
                              section={section}
                              onUpdate={handleSectionUpdate} // Handles API call
                              onDelete={handleSectionDelete} // Handles deletion
                              onShowHistory={handleShowHistory} // Shows history
                              aiSuggestionCount={aiSuggestionCount}
                              MAX_AI_SUGGESTIONS={MAX_AI_SUGGESTIONS}
                              handleAiSuggestionMade={handleAiSuggestionMade}
                            />
                          </Paper>
                        </Fade>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </Box>
              )}
            </Droppable>
          </DragDropContext>
          <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleAddSection}
              disabled={loading}
            >
              Add Section
            </Button>
            <Button
              variant="contained"
              color="secondary"
              onClick={handleDownload}
              disabled={loading}
            >
              Download Draft
            </Button>
            <Button
              variant="outlined"
              color="error"
              onClick={handleRevertToOriginal}
              disabled={loading}
            >
              Revert to Original
            </Button>
    
          </Box>
        </Box>
      </TabPanel>

      <TabPanel value={tabIndex} index={1}>
        {/* Draft For Actions Content */}
        <Box>
          <Typography variant="h6" gutterBottom>
            Publish or Mail to related parties
          </Typography>
          <TableContainer component={Paper}>
            <Table aria-label="draft-for-actions table">
              <TableHead>
                <TableRow>
                  <TableCell>Draft For Type</TableCell>
                  <TableCell>Details</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(draftForData).map(([draftForType, details]) => (
                  <TableRow key={draftForType}>
                    <TableCell component="th" scope="row">
                      {draftForType.charAt(0).toUpperCase() + draftForType.slice(1)}
                    </TableCell>
                    <TableCell>
                      {Array.isArray(details)
                        ? details.map((item, idx) => {
                            if (typeof item === 'object') {
                              // For caseid_with_clientid
                              return (
                                <Box key={idx} sx={{ mb: 1 }}>
                                  <strong>Case ID:</strong> {Object.keys(item)[0]}<br />
                                  <strong>First Name:</strong> {item[Object.keys(item)[0]].Fname}<br />
                                  <strong>Phone:</strong> {item[Object.keys(item)[0]].phone_number}
                                </Box>
                              );
                            } else {
                              return <span key={idx}>{item}{idx < details.length -1 ? ', ' : ''}</span>;
                            }
                          })
                        : JSON.stringify(details)}
                    </TableCell>
                    <TableCell align="center">
                      <Tooltip title="Publish draft to user. (Currently Disabled)">
                        <span>
                          <Button
                            variant="contained"
                            color="primary"
                            sx={{ mr: 1 }}
                            onClick={() => handlePublishToUser(draftForType, details)}
                            disabled={buttonStates[draftForType]?.publish}
                          >
                            Publish to User
                          </Button>
                        </span>
                      </Tooltip>
                      <Tooltip title="Mail draft to user.">
                        <span>
                          <Button
                            variant="contained"
                            color="secondary"
                            onClick={() => handleMailToUser(draftForType, details)}
                            disabled={buttonStates[draftForType]?.mail}
                          >
                            Mail to User
                          </Button>
                        </span>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
                {draftForData && Object.keys(draftForData).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} align="center">
                      No Draft For Data Available
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      </TabPanel>

      {selectedSection && (
        <Box
          sx={{
            flex: 1,
            backgroundColor: '#f9f9f9',
            p: 2,
            borderLeft: '1px solid #ddd',
            overflowY: 'auto',
            transition: 'all 0.3s ease-in-out',
          }}
        >
          <Button variant="text" onClick={handleCloseHistory} sx={{ mb: 2 }}>
            Close History
          </Button>
          <SectionHistory
            sessionId={sessionId}
            sectionId={selectedSection.section_id}
          />
        </Box>
      )
      }
    </Box>
  );
}
export default DraftViewerComponent;
