import React, { useMemo, useState } from 'react';
import { Box, AppBar, Toolbar, IconButton, Tooltip, Typography, Divider, useMediaQuery, useTheme } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import ChatPane from './ChatPane';
import DocPicker from './DocPicker';
import ChatHistoryPanel from './ChatHistoryPanel';
import { useSelector } from 'react-redux';

export default function ChatWithDocs() {
  const theme = useTheme();
  const isSm = useMediaQuery(theme.breakpoints.down('md'));
  const { selectedDocs } = useSelector(s => s.chatdocs);

  const [showSidebars, setShowSidebars] = useState(!isSm);

  return (
    <Box sx={{ height: 'calc(100vh - 64px)', display: 'flex', bgcolor: '#FAFAFA' }}>
      {/* Desktop: 3-column layout */}
      {!isSm ? (
        <>
          {/* LEFT: Chat History */}
          <Box
            sx={{
              width: 280,
              borderRight: '1px solid #E5E7EB',
              height: '100%',
              bgcolor: 'white',
              overflow: 'auto'
            }}
          >
            <ChatHistoryPanel onOpen={() => { /* no-op */ }} />
          </Box>

          {/* CENTER: Chat Pane */}
          <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
            <ChatPane />
          </Box>

          {/* RIGHT: Document Picker */}
          <Box
            sx={{
              width: 320,
              borderLeft: '1px solid #E5E7EB',
              height: '100%',
              bgcolor: 'white',
              overflow: 'auto'
            }}
          >
            <DocPicker />
          </Box>
        </>
      ) : (
        /* Mobile: Original stacked layout */
        <>
          {showSidebars && (
            <Box
              sx={{
                width: '100%',
                borderRight: '1px solid',
                borderColor: 'divider',
                height: '100%',
                display: 'block'
              }}
            >
              <LeftColumn mobile onClose={() => setShowSidebars(false)} />
            </Box>
          )}

          {!showSidebars && (
            <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', width: '100%' }}>
              {/* Mobile top bar */}
              <AppBar position="static" elevation={0} color="transparent" sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
                <Toolbar sx={{ gap: 1 }}>
                  <Tooltip title="Show documents & chats">
                    <IconButton size="small" onClick={() => setShowSidebars(true)}>
                      <MenuIcon fontSize="inherit" />
                    </IconButton>
                  </Tooltip>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>
                    {selectedDocs.length ? `Docs selected: ${selectedDocs.length}` : 'Chat with Documents'}
                  </Typography>
                </Toolbar>
              </AppBar>

              <Box sx={{ flex: 1, minHeight: 0 }}>
                <ChatPane />
              </Box>
            </Box>
          )}
        </>
      )}
    </Box>
  );
}

// Keep mobile stacked layout
function LeftColumn({ mobile = false, onClose }) {
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'background.paper' }}>
      <Box sx={{ flex: 1, minHeight: 0, display: 'grid', gridTemplateRows: 'minmax(180px, 40%) 1fr' }}>
        <Box sx={{ overflow: 'auto' }}>
          <ChatHistoryPanel onOpen={() => { /* no-op */ }} onCloseMobile={mobile ? onClose : undefined} />
        </Box>
        <Divider />
        <Box sx={{ overflow: 'auto' }}>
          <DocPicker mobile={mobile} inlineClose={onClose} />
        </Box>
      </Box>
    </Box>
  );
}
