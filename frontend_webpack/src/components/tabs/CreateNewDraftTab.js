// src/components/tabs/CreateNewDraftTab.js

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Tooltip,
  Link,
  Card,
  CardActionArea,
  CardContent,
  Checkbox,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { useDropzone } from 'react-dropzone';
import AxiosInstance from '../common/AxiosInstance';

function CreateNewDraftTab(props) {
  const {
    userQuery, setUserQuery,
    inputMethod, setInputMethod,
    uploadFile, setUploadFile,
    handleSubmitQuery,
    filterDataState,
    statesList, districtsList, courtsList,
    selectedState, handleSelectState,
    selectedDistrict, handleSelectDistrict,
    selectedCourt, handleSelectCourt,
    downloadTemplate,
    loading,
    setErrorMessage,
    languagesList,
    selectedLanguage,
    setSelectedLanguage,
    isClientUser = false, // Add isClientUser prop with default false for backward compatibility
  } = props;

  // --- Draft-For grid state ---
  const [draftForRows, setDraftForRows] = useState([]);
  const [selectedRows, setSelectedRows] = useState([]);

  // --- "Add New" dialog state ---
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [newCaseId, setNewCaseId] = useState('');
  const [addOpen, setAddOpen]            = useState(false);
  // const [newClientId, setNewClientId]    = useState("");
  const [newClientName, setNewClientName]= useState("");

  // Populate grid rows from backend map
  useEffect(() => {
    const rows = [];
    const map  = filterDataState.case_client_map || {};
    Object.entries(map).forEach(([caseId, cli]) =>
      rows.push({
        id         : caseId,          // unique for DataGrid
        case_id    : caseId,
        client_name: `${cli.Fname || ''} ${cli.Lname || ''}`.trim() || 'Unnamed',
      })
    );

    /* any orphan clients w/out case id */
    (filterDataState.clientIds_without_case || []).forEach((cli) =>
      rows.push({
        id         : cli.user_id,
        case_id    : '',              // blank case
        client_name: `${cli.Fname || ''} ${cli.Lname || ''}`.trim() || 'Unnamed',
      })
    );

    setDraftForRows(rows);
    setSelectedRows([]);
  }, [filterDataState]);


  // --- Dropzone setup ---
  const handleFileValidation = (file) => {
    const allowed = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ];
    const maxSize = 5 * 1024 * 1024;
    if (!allowed.includes(file.type)) {
      setErrorMessage('Unsupported format. Use PDF, DOC, DOCX, or TXT.');
      return false;
    }
    if (file.size > maxSize) {
      setErrorMessage('File exceeds 5MB. Please choose a smaller file.');
      return false;
    }
    return true;
  };
  const onDrop = (accepted, rejected) => {
    if (rejected.length > 0) {
      const errCodes = rejected[0].errors.map(e => e.code);
      if (errCodes.includes('file-invalid-type'))
        setErrorMessage('Unsupported format. Use PDF, DOC, DOCX, or TXT.');
      else if (errCodes.includes('file-too-large'))
        setErrorMessage('File exceeds 5MB. Please choose a smaller file.');
      return;
    }
    const file = accepted[0];
    if (handleFileValidation(file)) {
      setUploadFile(file);
      setErrorMessage('');
    }
  };
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
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

  const handleAddRow = () => {
    if (!newCaseId && !newClientName) {
      setErrorMessage('Please fill at least one field.');
      return;
    }
    setDraftForRows((r) => [
      ...r,
      { id: Date.now(), case_id: newCaseId, client_name: newClientName || 'Unnamed' },
    ]);
    setAddOpen(false);
  };

  // --- Add-New handlers ---
  const handleOpenAddNew  = () => { setNewCaseId(''); setNewClientName(''); setAddDialogOpen(true); };
  const handleCloseAddNew = () => setAddDialogOpen(false);
  const handleConfirmAddNew = () => {
    if (!newCaseId && !newClientName) {
      setErrorMessage('Please fill at least one field.');
      return;
    }
    const newRow = { id: newCaseId || Date.now(), caseId: newCaseId, clientName: newClientName };
    setDraftForRows(rows => [...rows, newRow]);
    setAddDialogOpen(false);
  };

  // --- Generate click ---
   const onGenerate = () => {
    // For client users, skip the draft_for validation and pass empty array
    if (isClientUser) {
      handleSubmitQuery([]);
      return;
    }

    // For non-client users (Lawyer, Paralegal), require at least one selection
    if (!selectedRows.length) {
      setErrorMessage('Choose at least one entry.');
      return;
    }
    const draft_for = selectedRows.map((rid) => {
      const r = draftForRows.find((x) => x.id === rid);
      return { case_id: r.case_id, client_name: r.client_name };
    });
    handleSubmitQuery(draft_for);
  };

  return (
    <Box>
      <Typography variant="h6">1. Create New Draft</Typography>

      {/* Language Dropdown */}
      <Box sx={{ mt: 2 }}>
        <FormControl fullWidth>
          <InputLabel id="lang-label">Language</InputLabel>
          <Select
            labelId="lang-label"
            value={selectedLanguage}
            label="Language"
            onChange={(e) => setSelectedLanguage(e.target.value)}
          >
            {languagesList.map((lang) => (
              <MenuItem key={lang} value={lang}>{lang}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Input Method Cards */}
      <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
        <Card
          sx={{
            flex: 1,
            border: inputMethod === 'write' ? '2px solid #1976d2' : '1px solid #ccc',
            backgroundColor: inputMethod === 'write' ? '#e3f2fd' : '#fafafa',
          }}
        >
          <CardActionArea onClick={() => { setInputMethod('write'); setUploadFile(null); }}>
            <CardContent>
              <Typography variant="h6" align="center">Write Description</Typography>
              <Typography variant="body2" align="center">
                Provide a detailed description of the draft you need.
              </Typography>
            </CardContent>
          </CardActionArea>
        </Card>
        <Card
          sx={{
            flex: 1,
            border: inputMethod === 'upload' ? '2px solid #1976d2' : '1px solid #ccc',
            backgroundColor: inputMethod === 'upload' ? '#e3f2fd' : '#fafafa',
          }}
        >
          <CardActionArea onClick={() => { setInputMethod('upload'); setUserQuery(''); }}>
            <CardContent>
              <Typography variant="h6" align="center">Upload Document</Typography>
              <Typography variant="body2" align="center">
                Upload a relevant document (PDF, DOC, DOCX, or TXT).
              </Typography>
            </CardContent>
          </CardActionArea>
        </Card>
      </Box>

      {/* Draft-For Grid - Only show for non-client users */}
      {!isClientUser && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Draft For
          </Typography>
          <Button 
            variant="outlined" 
            sx={{ mb: 1 }} 
            onClick={() => { 
              setAddOpen(true); 
              setNewCaseId(''); 
              setNewClientName(''); 
            }}
          >
            Add New
          </Button>

          <TableContainer component={Paper} sx={{ maxHeight: 300 }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      indeterminate={
                        selectedRows.length > 0 && selectedRows.length < draftForRows.length
                      }
                      checked={
                        draftForRows.length > 0 && selectedRows.length === draftForRows.length
                      }
                      onChange={(e) =>
                        setSelectedRows(e.target.checked ? draftForRows.map((r) => r.id) : [])
                      }
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
                        onChange={(e) =>
                          setSelectedRows((s) =>
                            e.target.checked ? [...s, r.id] : s.filter((x) => x !== r.id)
                          )
                        }
                      />
                    </TableCell>
                    <TableCell>{r.case_id}</TableCell>
                    <TableCell>{r.client_name}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Location Selection */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="subtitle1" gutterBottom>(Optional) Location</Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel id="state-select-label">State</InputLabel>
            <Select
              labelId="state-select-label"
              value={selectedState}
              label="State"
              onChange={(e) => handleSelectState(e.target.value)}
            >
              <MenuItem value="">None</MenuItem>
              {statesList.map(st => <MenuItem key={st} value={st}>{st}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl sx={{ minWidth: 200 }} disabled={!selectedState}>
            <InputLabel id="district-select-label">District</InputLabel>
            <Select
              labelId="district-select-label"
              value={selectedDistrict}
              label="District"
              onChange={(e) => handleSelectDistrict(e.target.value)}
            >
              <MenuItem value="">None</MenuItem>
              {districtsList.map(d => <MenuItem key={d} value={d}>{d}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl sx={{ minWidth: 200 }} disabled={!selectedDistrict}>
            <InputLabel id="court-select-label">Court</InputLabel>
            <Select
              labelId="court-select-label"
              value={selectedCourt}
              label="Court"
              onChange={(e) => handleSelectCourt(e.target.value)}
            >
              <MenuItem value="">None</MenuItem>
              {courtsList.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </Select>
          </FormControl>
        </Box>
      </Box>

      {/* Write / Upload UI */}
      {inputMethod === 'write' && (
        <Box sx={{ mt: 3 }}>
          <Tooltip title="Provide at least 10 characters" arrow>
            <TextField
              label="Describe the draft"
              multiline
              rows={6}
              fullWidth
              value={userQuery}
              onChange={e => setUserQuery(e.target.value)}
              helperText="Minimum 10 characters."
              error={userQuery.trim().length > 0 && userQuery.trim().length < 10}
            />
          </Tooltip>
        </Box>
      )}
      {inputMethod === 'upload' && (
        <Box sx={{ mt: 3 }}>
          <Tooltip title="Max 5MB: PDF, DOC, DOCX, TXT" arrow>
            <Box
              {...getRootProps()}
              sx={{
                border: '2px dashed #1976d2',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
                backgroundColor: isDragActive ? '#e3f2fd' : '#fafafa',
              }}
            >
              <input {...getInputProps()} />
              <Typography>
                {isDragActive
                  ? 'Drop files here…'
                  : "Drag & drop a file, or click to select"}
              </Typography>
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                Supported: PDF, DOC, DOCX, TXT.
              </Typography>
            </Box>
          </Tooltip>
          {uploadFile && (
            <Typography sx={{ mt: 2 }}>
              <strong>Selected:</strong> {uploadFile.name} (
              {(uploadFile.size / 1024 / 1024).toFixed(2)} MB)
            </Typography>
          )}
          <Typography variant="body2" sx={{ mt: 1 }}>
            Need a sample?{' '}
            <Link href="#" onClick={downloadTemplate}>
              Download template
            </Link>
          </Typography>
        </Box>
      )}

      {/* Generate Button */}
      <Box sx={{ mt:3 }}>
        <Button fullWidth variant="contained" color="primary"
          disabled={loading || (inputMethod==="upload"&&!uploadFile) ||
                    (inputMethod==="write" && userQuery.trim().length<10)}
          onClick={onGenerate}>
          {inputMethod==="upload"?"Upload & Generate Draft":"Generate Draft"}
        </Button>
      </Box>

      {/* Add-New Dialog */}
      <Dialog open={addOpen} onClose={() => setAddOpen(false)}>
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
          <Button onClick={() => setAddOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddRow}>
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default CreateNewDraftTab;
