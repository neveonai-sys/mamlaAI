import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  Alert, 
  Divider,
  IconButton,
  Tooltip,
  TextField,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Checkbox,
  Tabs,
  Tab
} from '@mui/material';
import { styled } from '@mui/material/styles';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DownloadIcon from '@mui/icons-material/Download';
import ShareIcon from '@mui/icons-material/Share';
import LockIcon from '@mui/icons-material/Lock';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import AxiosInstance from '../common/AxiosInstance';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[2],
}));

const StyledTableRow = styled(TableRow)(({ theme }) => ({
  '&:nth-of-type(odd)': {
    backgroundColor: theme.palette.action.hover,
  },
  '&:last-child td, &:last-child th': {
    border: 0,
  },
}));

const DraftPreview = () => {
  const { draftId } = useParams();
  const navigate = useNavigate();
  const [draftSections, setDraftSections] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [editingSection, setEditingSection] = useState(null);
  const [sectionContent, setSectionContent] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  useEffect(() => {
    const fetchDraftContent = async () => {
      try {
        const response = await AxiosInstance.get(`/aidrafts/test/sections/${draftId}/`);
        if (response.data && response.data.sections) {
          // Transform the sections to match the expected format
          const formattedSections = response.data.sections.map((section, index) => ({
            id: section.section_id || `section-${index}`,
            section_id: section.section_id || `section-${index}`,
            section_name: section.section_name || `Section ${index + 1}`,
            content: section.content || '',
            original_content: section.original_content || section.content || '',
            is_modified: section.is_modified || false,
            order: section.order || index
          }));
          setDraftSections(formattedSections);
        } else {
          setError('No draft sections found');
        }
      } catch (err) {
        console.error('Error fetching draft:', err);
        setError('Failed to load draft. The session may have expired or the draft is no longer available.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDraftContent();
  }, [draftId]);

  const handleEditSection = (section) => {
    setEditingSection(section);
    setSectionContent(section.content);
  };

  const handleSaveSection = () => {
    if (!editingSection) return;
    
    const updatedSections = draftSections.map(section => 
      section.id === editingSection.id 
        ? { ...section, content: sectionContent }
        : section
    );
    
    setDraftSections(updatedSections);
    setEditingSection(null);
    setSuccessMessage('Section updated successfully');
    setSnackbarOpen(true);
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;
    
    const items = Array.from(draftSections);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);
    
    setDraftSections(items);
    setSuccessMessage('Sections reordered successfully');
    setSnackbarOpen(true);
  };

  const handleDownload = () => {
    const fullContent = draftSections
      .map(section => `${section.section_name}\n${'='.repeat(section.section_name.length)}\n\n${section.content}`)
      .join('\n\n');
    
    const element = document.createElement('a');
    const file = new Blob([fullContent], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `draft-${draftId}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleCopyToClipboard = () => {
    const fullContent = draftSections
      .map(section => `${section.section_name}\n${'='.repeat(section.section_name.length)}\n\n${section.content}`)
      .join('\n\n');
    
    navigator.clipboard.writeText(fullContent)
      .then(() => {
        setSuccessMessage('Draft copied to clipboard');
        setSnackbarOpen(true);
      })
      .catch(err => {
        console.error('Failed to copy:', err);
        setError('Failed to copy to clipboard');
      });
  };

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Typography>Loading your draft...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
        <Button 
          variant="contained" 
          onClick={() => window.location.reload()}
          sx={{ mt: 2 }}
        >
          Retry
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, margin: '0 auto', p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Button 
          startIcon={<ArrowBackIcon />} 
          onClick={() => navigate(-1)}
          sx={{ textTransform: 'none' }}
        >
          Back to Drafting
        </Button>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Copy to clipboard">
            <IconButton onClick={handleCopyToClipboard} color="primary">
              <ContentCopyIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Download draft">
            <IconButton onClick={handleDownload} color="primary">
              <DownloadIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Sign up to enable AI suggestions">
            <span>
              <IconButton disabled>
                <LockIcon />
              </IconButton>
            </span>
          </Tooltip>
          
          <Tooltip title="Sign up to save this draft">
            <span>
              <IconButton disabled>
                <SaveIcon />
              </IconButton>
            </span>
          </Tooltip>
        </Box>
      </Box>

      <Alert 
        severity="warning" 
        icon={<LockIcon />}
        sx={{ 
          mb: 3, 
          '& .MuiAlert-message': { width: '100%' },
          '& .MuiAlert-action': { alignItems: 'center' }
        }}
        action={
          <Button 
            color="warning" 
            variant="contained" 
            size="small"
            onClick={() => navigate('/signup')}
          >
            Sign Up for Full Access
          </Button>
        }
      >
        <Box>
          <Typography variant="subtitle1" fontWeight="bold">Preview Mode</Typography>
          <Typography variant="body2">
            You're viewing a preview of your generated draft. Sign up to unlock all features including 
            AI suggestions, saving drafts, and collaboration tools.
          </Typography>
        </Box>
      </Alert>

      <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 3 }}>
        <Tab label="Draft Editor" {...a11yProps(0)} />
        <Tab label="Preview" {...a11yProps(1)} />
      </Tabs>

      <TabPanel value={activeTab} index={0}>
        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId="draft-sections">
            {(provided) => (
              <Box {...provided.droppableProps} ref={provided.innerRef}>
                {draftSections.map((section, index) => (
                  <Draggable key={section.id} draggableId={section.id} index={index}>
                    {(provided) => (
                      <StyledPaper
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        sx={{ mb: 2, p: 2, position: 'relative' }}
                      >
                        <Box 
                          {...provided.dragHandleProps}
                          sx={{ 
                            display: 'flex', 
                            justifyContent: 'space-between', 
                            alignItems: 'center',
                            mb: 2,
                            p: 1,
                            backgroundColor: 'action.hover',
                            borderRadius: 1,
                            cursor: 'grab',
                            '&:active': { cursor: 'grabbing' }
                          }}
                        >
                          <Typography variant="h6">{section.section_name}</Typography>
                          <Box>
                            <Tooltip title="Edit section">
                              <IconButton 
                                onClick={() => handleEditSection(section)}
                                size="small"
                                sx={{ mr: 1 }}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </Box>

                        {editingSection?.id === section.id ? (
                          <Box>
                            <TextField
                              fullWidth
                              multiline
                              rows={8}
                              variant="outlined"
                              value={sectionContent}
                              onChange={(e) => setSectionContent(e.target.value)}
                              sx={{ mb: 2 }}
                            />
                            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                              <Button 
                                variant="outlined" 
                                onClick={() => setEditingSection(null)}
                              >
                                Cancel
                              </Button>
                              <Button 
                                variant="contained" 
                                onClick={handleSaveSection}
                                color="primary"
                              >
                                Save Changes
                              </Button>
                            </Box>
                          </Box>
                        ) : (
                          <Box sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', lineHeight: 1.6 }}>
                            {section.content}
                          </Box>
                        )}
                      </StyledPaper>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </Box>
            )}
          </Droppable>
        </DragDropContext>
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <StyledPaper>
          {draftSections.map((section, index) => (
            <Box key={section.id} sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom>
                {section.section_name}
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
                {section.content}
              </Box>
            </Box>
          ))}
        </StyledPaper>
      </TabPanel>

      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 4, flexWrap: 'wrap' }}>
        <Button 
          variant="outlined" 
          onClick={() => navigate('/test-ai-drafting')}
          sx={{ minWidth: 180 }}
        >
          Create Another Draft
        </Button>
        
        <Button 
          variant="contained" 
          color="primary"
          onClick={() => navigate('/signup')}
          sx={{ minWidth: 220 }}
          startIcon={<LockIcon />}
        >
          Sign Up to Save & Enable AI Features
        </Button>
      </Box>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSnackbarOpen(false)} severity="success" sx={{ width: '100%' }}>
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

// Helper components for tabs
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`draft-preview-tabpanel-${index}`}
      aria-labelledby={`draft-preview-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 1 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index) {
  return {
    id: `draft-preview-tab-${index}`,
    'aria-controls': `draft-preview-tabpanel-${index}`,
  };
}

export default DraftPreview;
