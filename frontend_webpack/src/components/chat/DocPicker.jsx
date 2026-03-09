import React, { useEffect, useMemo, useState } from 'react';
import { Box, Paper, Typography, Button, TextField, List, ListItem, ListItemText, Checkbox, Divider, Stack, InputAdornment, IconButton, CircularProgress, Alert, Chip, Tooltip } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CloseIcon from '@mui/icons-material/Close';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DescriptionIcon from '@mui/icons-material/Description';
import { useDropzone } from 'react-dropzone';
import { listDocs, uploadDoc, createSession } from './talktodocApi';
import { useDispatch, useSelector } from 'react-redux';
import { addSelectedDoc, removeSelectedDoc, setMatter, setCurrentSession } from '../../features/chatDocsSlice';

const sidebarBorder = '#E5E7EB';

export default function DocPicker({ mobile = false, inlineClose }) {
  const dispatch = useDispatch();
  const { selectedDocs, matter } = useSelector(s => s.chatdocs);
  const [docs, setDocs] = useState([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const refresh = async () => {
    setLoading(true);
    const res = await listDocs({ q, page: 1, page_size: 200 });
    setDocs(res?.data?.items || []);
    setLoading(false);
  };
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, []);

  const onDrop = async (accepted, rejected) => {
    if (rejected.length > 0) {
      setUploadError('Invalid file type or size. Please use PDF, DOCX, or TXT files under 25MB.');
      return;
    }
    if (!accepted.length) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(false);
    try {
      const fd = new FormData();
      fd.append('file', accepted[0]);
      fd.append('matter', JSON.stringify(matter));
      await uploadDoc(fd);
      setUploadSuccess(true);
      setTimeout(() => setUploadSuccess(false), 3000);
      await refresh();
    } catch (err) {
      setUploadError('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, multiple: false, maxSize: 25 * 1024 * 1024,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
  });

  const toggle = (d) => {
    if (selectedDocs.find(x => x.id === d.id)) dispatch(removeSelectedDoc(d.id));
    else dispatch(addSelectedDoc({ id: d.id, name: d.name }));
  };
  const selectedSet = useMemo(() => new Set(selectedDocs.map(d => d.id)), [selectedDocs]);

  const getFileIcon = (name) => {
    if (name.endsWith('.pdf')) return <PictureAsPdfIcon color="error" fontSize="small" />;
    if (name.endsWith('.docx') || name.endsWith('.doc')) return <DescriptionIcon color="primary" fontSize="small" />;
    return <InsertDriveFileIcon color="action" fontSize="small" />;
  };

  const startChat = async () => {
    // Allow starting chat with or without docs
    const body = { doc_ids: selectedDocs.map(d => d.id), matter };
    const res = await createSession(body);
    dispatch(setCurrentSession(res.data.session_id));
    if (inlineClose) inlineClose();
  };

  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1.5, height: '100%' }}>
      {/* header row */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, flex: 1 }}>
          📚 Documents {docs.length > 0 && `(${docs.length})`}
        </Typography>
        {mobile && (
          <IconButton size="small" onClick={inlineClose}><CloseIcon fontSize="inherit" /></IconButton>
        )}
      </Box>

      {/* Upload feedback */}
      {uploadError && (
        <Alert severity="error" onClose={() => setUploadError(null)} sx={{ py: 0.5 }}>
          {uploadError}
        </Alert>
      )}
      {uploadSuccess && (
        <Alert severity="success" sx={{ py: 0.5 }}>
          ✅ Document uploaded successfully!
        </Alert>
      )}

      {/* upload */}
      <Paper
        variant="outlined"
        {...getRootProps()}
        sx={{ 
          p: 2, 
          borderStyle: 'dashed', 
          borderWidth: 2,
          textAlign: 'center', 
          cursor: uploading ? 'not-allowed' : 'pointer', 
          bgcolor: isDragActive ? 'action.hover' : uploading ? 'action.disabledBackground' : 'background.default',
          transition: 'all 0.2s',
          '&:hover': {
            borderColor: 'primary.main',
            bgcolor: 'action.hover'
          }
        }}
      >
        <input {...getInputProps()} disabled={uploading} />
        {uploading ? (
          <Stack alignItems="center" spacing={1}>
            <CircularProgress size={24} />
            <Typography variant="caption">Uploading...</Typography>
          </Stack>
        ) : (
          <>
            <CloudUploadIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
            <Typography variant="body2" fontWeight={600} gutterBottom>
              {isDragActive ? 'Drop file here' : 'Upload Document'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              PDF, DOCX, TXT • Max 25MB
            </Typography>
          </>
        )}
      </Paper>

      {/* START CHAT BUTTON - Prominent position at top */}
      <Button 
        variant="contained" 
        fullWidth
        size="large"
        onClick={startChat}
        sx={{
          py: 1.5,
          fontWeight: 600,
          fontSize: '0.95rem',
          textTransform: 'none',
          borderRadius: 2,
          boxShadow: '0 4px 12px rgba(25, 118, 210, 0.3)',
          '&:hover': {
            boxShadow: '0 6px 16px rgba(25, 118, 210, 0.4)',
          }
        }}
      >
        {selectedDocs.length 
          ? `🚀 Start Chat (${selectedDocs.length} doc${selectedDocs.length > 1 ? 's' : ''})` 
          : '💬 Start Chat Session'}
      </Button>

      <Divider sx={{ my: 1 }} />

      {/* selected */}
      <Box>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
          Selected Documents ({selectedDocs.length})
        </Typography>
        <List dense disablePadding sx={{ maxHeight: 120, overflow: 'auto' }}>
          {selectedDocs.map(d => (
            <ListItem key={d.id} secondaryAction={<Checkbox checked onChange={() => toggle(d)} />}>
              <ListItemText primary={<Typography noWrap>{d.name}</Typography>} />
            </ListItem>
          ))}
          {!selectedDocs.length && (
            <Typography variant="body2" color="text.secondary" sx={{ py: 1, px: 1 }}>No documents selected</Typography>
          )}
        </List>
      </Box>

      <Divider />

      {/* available */}
      <Box>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>Available Documents</Typography>
        <TextField
          size="small"
          fullWidth
          placeholder="Search…"
          value={q}
          onChange={e => setQ(e.target.value)}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton size="small" onClick={refresh}><SearchIcon fontSize="small" /></IconButton>
              </InputAdornment>
            ),
          }}
        />
        <Paper variant="outlined" sx={{ mt: 1, maxHeight: 240, overflow: 'auto' }}>
          <List dense>
            {docs.map(d => (
              <ListItem key={d.id} secondaryAction={<Checkbox checked={selectedSet.has(d.id)} onChange={() => toggle(d)} />}>
                <ListItemText
                  primary={<Typography noWrap>{d.name}</Typography>}
                  secondary={`${(d.size / 1024 / 1024).toFixed(2)} MB · ${new Date(d.created_at).toLocaleString()}`}
                />
              </ListItem>
            ))}
            {!docs.length && (
              <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                {loading ? 'Loading…' : 'No documents found'}
              </Typography>
            )}
          </List>
        </Paper>
      </Box>
    </Box>
  );
}
