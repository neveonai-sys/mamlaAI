import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  CircularProgress,
  Radio,
  RadioGroup,
  FormControlLabel,
  Checkbox,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Paper,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import { useDropzone } from 'react-dropzone';
import AxiosInstance from '../common/AxiosInstance';

// ---------------------------------------------------------------------------
// Styled components
// ---------------------------------------------------------------------------
const UploadBox = styled(Box)(({ theme }) => ({
  border: '2px dashed #1976d2',
  borderRadius: 8,
  padding: theme.spacing(3),
  textAlign: 'center',
  cursor: 'pointer',
  backgroundColor: '#fafafa',
  marginTop: theme.spacing(2),
}));

function LoadTemplateTab(props) {
  // Add debug log for props
  useEffect(() => {
    console.log('LoadTemplateTab - props:', {
      isClientUser: props.isClientUser,
      filterDataState: props.filterDataState
    });
  }, [props.isClientUser, props.filterDataState]);

  const {
    draftType,
    setDraftType,
    templateFile,
    setTemplateFile,

    handleUploadTemplate, // parent cb
    loading,
    setErrorMessage,

    // — Preview-related props left unchanged
    onConfirmTemplatePreview,
    onCancelTemplatePreview,
    previewSections,
    showPreview,

    // filter data from parent, default empty structure
    filterDataState = {
      caseIds_without_client: [],
      clientIds_without_case: [],
      case_client_map: {},
    },
    isClientUser = false, // Add isClientUser prop with default false for backward compatibility
  } = props;

  // Log when isClientUser changes
  useEffect(() => {
    console.log('isClientUser changed:', isClientUser);
  }, [isClientUser]);

  // -----------------------------------------------------------------------
  // 1) Draft-for Grid State (mirrors CreateNewDraftTab)
  // -----------------------------------------------------------------------
  const [draftForRows, setDraftForRows] = useState([]); // [{id,case_id,client_name,isCustom?}]
  const [selectedRows, setSelectedRows] = useState([]); // array of row.id

  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [newCaseId, setNewCaseId] = useState('');
  const [newClientName, setNewClientName] = useState('');

  // Build / refresh rows when filterDataState changes. Only update the state
  // if the computed rows differ to avoid an infinite re\-render loop.
  useEffect(() => {
    // Build rows from filterDataState
    const rows = [];
    const map = filterDataState.case_client_map || {};
    Object.entries(map).forEach(([caseId, cli]) => {
      rows.push({
        id: caseId,
        case_id: caseId,
        client_name: `${cli.Fname || ''} ${cli.Lname || ''}`.trim() || 'Unnamed',
      });
    });
    (filterDataState.clientIds_without_case || []).forEach((cli) => {
      rows.push({
        id: cli.user_id,
        case_id: '',
        client_name: `${cli.Fname || ''} ${cli.Lname || ''}`.trim() || 'Unnamed',
      });
    });
    setDraftForRows(rows);
    setSelectedRows([]);
  }, [filterDataState]);

  const handleAddCustomRow = () => {
    if (!newCaseId && !newClientName) {
      setErrorMessage('Please fill at least one field.');
      return;
    }
    const row = {
      id: Date.now(),
      case_id: newCaseId,
      client_name: newClientName || 'Unnamed',
    };
    setDraftForRows((prev) => [...prev, row]);
    setAddDialogOpen(false);
  };

  // -----------------------------------------------------------------------
  // 2) Template source choice (existing vs upload) — keeps original logic
  // -----------------------------------------------------------------------
  const [templateChoice, setTemplateChoice] = useState('');

  const [draftTypes, setDraftTypes] = useState([]);
  const [draftNames, setDraftNames] = useState([]);
  const [selectedDraftType, setSelectedDraftType] = useState('');
  const [selectedDraftName, setSelectedDraftName] = useState('');

  // PDF preview state (unchanged)
  const [pdfUrl, setPdfUrl] = useState(null);
  const [showPdfDialog, setShowPdfDialog] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [fetchingPdf, setFetchingPdf] = useState(false);

  // -----------------------------------------------------------------------
  // 3) INITIAL FETCH: all draft types
  // -----------------------------------------------------------------------
  useEffect(() => {
    async function fetchDraftTypes() {
      try {
        const resp = await AxiosInstance.get('drafts/get-all-drafts/');
        if (resp.data?.dir_list) setDraftTypes(resp.data.dir_list);
      } catch (err) {
        console.error(err);
        setErrorMessage('Error fetching draft types. Please try again.');
      }
    }
    fetchDraftTypes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // -----------------------------------------------------------------------
  // 4) FETCH draft names when a type is chosen
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (!selectedDraftType) {
      setDraftNames([]);
      return;
    }
    async function fetchDraftNames() {
      try {
        const resp = await AxiosInstance.get(
          `drafts/draft-items?type=${encodeURIComponent(selectedDraftType)}`
        );
        if (resp.data?.all_drafts_list) setDraftNames(resp.data.all_drafts_list);
      } catch (err) {
        console.error(err);
        setErrorMessage('Error fetching draft names. Please try again.');
      }
    }
    fetchDraftNames();
  }, [selectedDraftType, setErrorMessage]);

  // -----------------------------------------------------------------------
  // 5) Preview existing template (unchanged)
  // -----------------------------------------------------------------------
  const handlePreviewExistingTemplate = async () => {
    if (!selectedDraftType || !selectedDraftName) {
      setErrorMessage('Select both Draft Type and Draft Name.');
      return;
    }
    setFetchingPdf(true);
    try {
      const resp = await AxiosInstance.get('drafts/get-template/', {
        params: {
          type: selectedDraftType,
          filename: selectedDraftName,
        },
        responseType: 'blob',
      });
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      const blobUrl = URL.createObjectURL(resp.data);
      setPdfUrl(blobUrl);
      setShowPdfDialog(true);
    } catch (err) {
      console.error(err);
      setErrorMessage('Failed to preview template.');
    } finally {
      setFetchingPdf(false);
    }
  };

  const resetTemplateChoice = () => {
    setTemplateChoice('');
    setSelectedDraftType('');
    setSelectedDraftName('');
    setDraftNames([]);
    setDraftType('');
    setTemplateFile(null);
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
    setShowPdfDialog(false);
    setZoomLevel(1);
  };

  // -----------------------------------------------------------------------
  // 6) File validation & dropzone for new uploads (unchanged)
  // -----------------------------------------------------------------------
  const handleFileValidation = (file) => {
    const allowed = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ];
    const maxSize = 5 * 1024 * 1024;
    return allowed.includes(file.type) && file.size <= maxSize;
  };

  const onDrop = (accepted, rejected) => {
    if (rejected.length) return; // message omitted for brevity
    const file = accepted[0];
    if (handleFileValidation(file)) setTemplateFile(file);
  };

  const {
    getRootProps: getTemplateRootProps,
    getInputProps: getTemplateInputProps,
    isDragActive: isTemplateDragActive,
  } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxSize: 5 * 1024 * 1024,
    multiple: false,
  });

  // -----------------------------------------------------------------------
  // 3) Submit builds draft_for and calls parent
  // -----------------------------------------------------------------------
  const handleSubmit = () => {
    // For client users, skip the draft_for validation and pass empty array
    if (isClientUser) {
      if (templateChoice === 'existing') {
        if (!selectedDraftType || !selectedDraftName) {
          setErrorMessage('Select Draft Type & Draft Name.');
          return;
        }
        handleUploadTemplate({ 
          existingTemplate: true, 
          chosenDraftType: selectedDraftType, 
          chosenDraftName: selectedDraftName, 
          draft_for: [] // Empty array for client users
        });
        return;
      }
      if (templateChoice === 'upload') {
        if (!draftType.trim() || !templateFile) {
          setErrorMessage('Enter Draft Type and choose a file.');
          return;
        }
        handleUploadTemplate({ 
          existingTemplate: false, 
          chosenDraftType: draftType, 
          file: templateFile, 
          draft_for: [] // Empty array for client users
        });
        return;
      }
      setErrorMessage('Please choose existing or upload path.');
      return;
    }

    // For non-client users (Lawyer, Paralegal), require at least one selection
    if (!selectedRows.length) {
      setErrorMessage('Choose at least one Draft For entry.');
      return;
    }
    const draft_for = selectedRows.map((id) => {
      const r = draftForRows.find((x) => x.id === id);
      return { case_id: r.case_id, client_name: r.client_name };
    });

    if (templateChoice === 'existing') {
      if (!selectedDraftType || !selectedDraftName) {
        setErrorMessage('Select Draft Type & Draft Name.');
        return;
      }
      handleUploadTemplate({ existingTemplate: true, chosenDraftType: selectedDraftType, chosenDraftName: selectedDraftName, draft_for });
      return;
    }
    if (templateChoice === 'upload') {
      if (!draftType.trim() || !templateFile) {
        setErrorMessage('Enter Draft Type and choose a file.');
        return;
      }
      handleUploadTemplate({ existingTemplate: false, chosenDraftType: draftType, file: templateFile, draft_for });
      return;
    }
    setErrorMessage('Please choose existing or upload path.');
  };

  // -----------------------------------------------------------------------
  // 8) Render
  // -----------------------------------------------------------------------
  return (
    <Box>
      <Typography variant="h6">3. Load or Upload Your Template</Typography>

      {/* Debug info - remove in production */}
      <Box sx={{ display: 'none' }} data-testid="debug-info">
        <div>isClientUser: {String(isClientUser)}</div>
        <div>User Type: {isClientUser ? 'Client' : 'Lawyer/Paralegal'}</div>
      </Box>

      {/* Draft For Grid - Only show for non-client users */}
      {!isClientUser ? (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle1" gutterBottom>Draft For</Typography>
          <Button 
            variant="outlined" 
            sx={{ mb: 1 }} 
            onClick={() => { setNewCaseId(''); setNewClientName(''); setAddDialogOpen(true); }}
          >
            Add New
          </Button>
          
          <TableContainer component={Paper} sx={{ maxHeight: 200, overflow: 'auto' }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      indeterminate={selectedRows.length > 0 && selectedRows.length < draftForRows.length}
                      checked={draftForRows.length > 0 && selectedRows.length === draftForRows.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedRows(draftForRows.map((r) => r.id));
                        } else {
                          setSelectedRows([]);
                        }
                      }}
                    />
                  </TableCell>
                  <TableCell>Case ID</TableCell>
                  <TableCell>Client Name</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {draftForRows.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={selectedRows.includes(r.id)}
                        onChange={(e) => setSelectedRows((s) => e.target.checked ? [...s, r.id] : s.filter((x) => x !== r.id))}
                      />
                    </TableCell>
                    <TableCell>{r.case_id || '—'}</TableCell>
                    <TableCell>{r.client_name}</TableCell>
                  </TableRow>
                ))}
                {draftForRows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} align="center">
                      No entries yet. Click "Add New" to add one.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      ) : null}

      {/* Add New Dialog */}
      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)}>
        <DialogTitle>Add New Entry</DialogTitle>
        <DialogContent>
          <TextField
            label="Case ID"
            fullWidth
            margin="dense"
            value={newCaseId}
            onChange={(e) => setNewCaseId(e.target.value)}
          />
          <TextField
            label="Client Name"
            fullWidth
            margin="dense"
            value={newClientName}
            onChange={(e) => setNewClientName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddCustomRow}>
            Add
          </Button>
        </DialogActions>
      </Dialog>

      {/* Radio choice: existing vs upload */}
      <RadioGroup
        row
        value={templateChoice}
        onChange={(e) => {
          resetTemplateChoice();
          setTemplateChoice(e.target.value);
        }}
        sx={{ mt: 3 }}
      >
        <FormControlLabel value="existing" control={<Radio />} label="Select Existing Template" />
        <FormControlLabel value="upload" control={<Radio />} label="Upload New Template" />
      </RadioGroup>

      {/* EXISTING FLOW */}
      {templateChoice === 'existing' && (
        <Box sx={{ mt: 2 }}>
          <FormControl fullWidth size="small" sx={{ mb: 2 }}>
            <InputLabel id="draft-type-label">Draft Type</InputLabel>
            <Select
              labelId="draft-type-label"
              value={selectedDraftType}
              label="Draft Type"
              onChange={(e) => {
                setSelectedDraftType(e.target.value);
                setSelectedDraftName('');
              }}
            >
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {draftTypes.map((t) => (
                <MenuItem key={t} value={t}>{t}</MenuItem>
              ))}
            </Select>
          </FormControl>

          {selectedDraftType && (
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel id="draft-name-label">Draft Name</InputLabel>
              <Select
                labelId="draft-name-label"
                value={selectedDraftName}
                label="Draft Name"
                onChange={(e) => setSelectedDraftName(e.target.value)}
              >
                <MenuItem value="">
                  <em>None</em>
                </MenuItem>
                {draftNames.map((n) => (
                  <MenuItem key={n} value={n}>{n}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <Button
              variant="contained"
              onClick={handlePreviewExistingTemplate}
              disabled={!selectedDraftName || loading || fetchingPdf}
            >
              {fetchingPdf ? <CircularProgress size={20} /> : 'Preview'}
            </Button>
            <Button variant="outlined" color="secondary" onClick={resetTemplateChoice}>
              Cancel
            </Button>
          </Box>
        </Box>
      )}

      {/* UPLOAD FLOW */}
      {templateChoice === 'upload' && (
        <Box sx={{ mt: 2 }}>
          <TextField
            label="Draft Type"
            value={draftType}
            onChange={(e) => setDraftType(e.target.value)}
            fullWidth
            size="small"
            sx={{ mb: 2 }}
          />

          <UploadBox {...getTemplateRootProps()}>
            <input {...getTemplateInputProps()} />
            <Typography>
              {isTemplateDragActive ? 'Drop the file here…' : 'Drag & drop or click to select a file'}
            </Typography>
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              Supported: PDF, DOC, DOCX, TXT (max 5MB)
            </Typography>
          </UploadBox>

          {templateFile && (
            <Typography sx={{ mt: 1 }}>Selected File: {templateFile.name}</Typography>
          )}

          <Box sx={{ mt: 2 }}>
            <Button variant="outlined" color="secondary" onClick={resetTemplateChoice}>
              Cancel
            </Button>
          </Box>
        </Box>
      )}

      {(templateChoice === 'existing' || templateChoice === 'upload') && (
        <Box sx={{ mt: 3 }}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            disabled={loading}
            onClick={handleSubmit}
          >
            Submit
          </Button>
        </Box>
      )}

      {/* PDF Preview dialog */}
      <Dialog open={showPdfDialog} onClose={() => setShowPdfDialog(false)} fullWidth maxWidth="lg">
        <DialogTitle>Preview Template</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 1 }}>
            <IconButton onClick={() => setZoomLevel((z) => Math.min(z + 0.2, 3))} size="small">
              <ZoomInIcon />
            </IconButton>
            <IconButton onClick={() => setZoomLevel((z) => Math.max(z - 0.2, 0.5))} size="small">
              <ZoomOutIcon />
            </IconButton>
          </Box>
          {pdfUrl ? (
            <Box
              sx={{ width: '100%', height: '70vh', overflow: 'auto', border: '1px solid #ccc', borderRadius: 1, transform: `scale(${zoomLevel})`, transformOrigin: 'top left' }}
            >
              <iframe title="Template PDF" src={pdfUrl} width="100%" height="100%" style={{ border: 'none' }} />
            </Box>
          ) : (
            <Typography>Loading PDF…</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowPdfDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Add New Dialog */}
      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)}>
        <DialogTitle>Add New Entry</DialogTitle>
        <DialogContent>
          <TextField
            label="Case ID"
            fullWidth
            margin="dense"
            value={newCaseId}
            onChange={(e) => setNewCaseId(e.target.value)}
          />
          <TextField
            label="Client Name"
            fullWidth
            margin="dense"
            value={newClientName}
            onChange={(e) => setNewClientName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddCustomRow}>
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default LoadTemplateTab;
