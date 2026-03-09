import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  CircularProgress,
  useTheme,
} from '@mui/material';
import {
  Close as CloseIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  Rotate90DegreesCw as RotateIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

const DocumentPreview = ({ file, open, onClose, highlight }) => {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [highlightedText, setHighlightedText] = useState(highlight || '');
  const theme = useTheme();

  // Update highlighted text when highlight prop changes
  useEffect(() => {
    setHighlightedText(highlight || '');
  }, [highlight]);

  // Update container width on resize
  useEffect(() => {
    if (!containerRef.current) return;
    
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth - 40);
      }
    };

    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, [open]);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    setIsLoading(false);
  };

  const onDocumentLoadError = (error) => {
    console.error('Error loading document:', error);
    setError('Failed to load document. Please try again.');
    setIsLoading(false);
  };

  const zoomIn = () => setScale(prev => Math.min(prev + 0.25, 3));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5));
  const rotate = () => setRotation(prev => (prev + 90) % 360);

  const downloadFile = () => {
    const link = document.createElement('a');
    link.href = file instanceof File ? URL.createObjectURL(file) : file.url || file.uri;
    link.download = file.name || 'document';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const goToPrevPage = () => setPageNumber(prev => Math.max(prev - 1, 1));
  const goToNextPage = () => setPageNumber(prev => Math.min(prev + 1, numPages));

  // Custom text renderer for highlighting search terms
  const textRenderer = useCallback((textItem) => {
    if (!highlightedText) return textItem.str;
    
    try {
      const regex = new RegExp(`(${highlightedText})`, 'gi');
      const parts = textItem.str.split(regex);
      
      return parts.map((part, i) => 
        regex.test(part) ? (
          <mark 
            key={i} 
            style={{ 
              backgroundColor: theme.palette.warning.light,
              color: theme.palette.getContrastText(theme.palette.warning.light),
              padding: '0 2px',
              borderRadius: '2px'
            }}
          >
            {part}
          </mark>
        ) : part
      );
    } catch (e) {
      console.error('Error creating regex:', e);
      return textItem.str;
    }
  }, [highlightedText, theme]);

  if (!file) return null;

  const isPdf = file.type === 'application/pdf' || file.name?.endsWith('.pdf');
  const isImage = file.type?.startsWith('image/') || 
                 ['.jpg', '.jpeg', '.png', '.gif'].some(ext => file.name?.toLowerCase().endsWith(ext));

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      aria-labelledby="document-preview-title"
      PaperProps={{
        sx: {
          height: '90vh',
          maxHeight: '800px',
        },
      }}
    >
      <DialogTitle 
        id="document-preview-title" 
        sx={{ 
          display: 'flex', 
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid',
          borderColor: 'divider',
          padding: '8px 24px',
        }}
      >
        <Typography variant="h6" noWrap sx={{ maxWidth: '80%' }}>
          {file.name}
        </Typography>
        <IconButton 
          edge="end" 
          color="inherit" 
          onClick={onClose} 
          aria-label="close"
          size="large"
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      
      <DialogContent 
        ref={containerRef}
        sx={{ 
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 2,
          backgroundColor: theme.palette.grey[100],
          overflow: 'auto',
          position: 'relative',
        }}
      >
        {isLoading && (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <CircularProgress />
            <Typography variant="body1" sx={{ mt: 2 }}>Loading document...</Typography>
          </Box>
        )}

        {error && (
          <Typography color="error">{error}</Typography>
        )}

        {isPdf && !error && (
          <Box sx={{ textAlign: 'center' }}>
            <Document
              file={file}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <CircularProgress />
                  <Typography variant="body1" sx={{ mt: 2 }}>Loading PDF...</Typography>
                </Box>
              }
            >
              <Page 
                pageNumber={pageNumber} 
                width={Math.min(containerWidth, 1000) * scale}
                rotate={rotation}
                renderTextLayer={true}
                renderAnnotationLayer={true}
                customTextRenderer={highlightedText ? textRenderer : undefined}
              />
            </Document>
            
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 2 }}>
              <Button 
                onClick={goToPrevPage} 
                disabled={pageNumber <= 1}
                variant="outlined"
                size="small"
              >
                Previous
              </Button>
              <Typography variant="body2">
                Page {pageNumber} of {numPages || '--'}
              </Typography>
              <Button 
                onClick={goToNextPage} 
                disabled={pageNumber >= (numPages || 1)}
                variant="outlined"
                size="small"
              >
                Next
              </Button>
            </Box>
          </Box>
        )}

        {isImage && !isPdf && !error && (
          <Box
            component="img"
            src={file instanceof File ? URL.createObjectURL(file) : file.url || file.uri}
            alt={file.name}
            sx={{
              maxWidth: '100%',
              maxHeight: '70vh',
              objectFit: 'contain',
              transform: `rotate(${rotation}deg)`,
              transition: 'transform 0.3s ease-in-out',
              transformOrigin: 'center',
            }}
            onLoad={() => setIsLoading(false)}
            onError={() => {
              setError('Failed to load image.');
              setIsLoading(false);
            }}
          />
        )}

        {!isPdf && !isImage && !error && !isLoading && (
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body1" color="textSecondary" sx={{ mb: 2 }}>
              Preview not available for this file type.
            </Typography>
            <Button 
              variant="contained" 
              color="primary" 
              onClick={downloadFile}
              startIcon={<DownloadIcon />}
            >
              Download File
            </Button>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ 
        borderTop: '1px solid',
        borderColor: 'divider',
        padding: '8px 16px',
        justifyContent: 'space-between',
      }}>
        <Box>
          <IconButton 
            onClick={zoomIn} 
            disabled={!isPdf && !isImage}
            title="Zoom In"
            size="large"
          >
            <ZoomInIcon />
          </IconButton>
          <IconButton 
            onClick={zoomOut} 
            disabled={!isPdf && !isImage}
            title="Zoom Out"
            size="large"
          >
            <ZoomOutIcon />
          </IconButton>
          <IconButton 
            onClick={rotate} 
            disabled={!isPdf && !isImage}
            title="Rotate"
            size="large"
          >
            <RotateIcon />
          </IconButton>
        </Box>
        
        <Box>
          <Button 
            onClick={downloadFile}
            startIcon={<DownloadIcon />}
            color="primary"
            variant="outlined"
            size="large"
          >
            Download
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  );
};

export default DocumentPreview;
