import React, { useEffect, useState } from 'react';
import { Box, List, ListItemButton, ListItemText, IconButton, Typography, TextField, InputAdornment, Tooltip, Divider } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import { useDispatch, useSelector } from 'react-redux';
import { listSessions, deleteSession, renameSession } from './talktodocApi';
import { setSessions, setCurrentSession } from '../../features/chatDocsSlice';

export default function ChatHistoryPanel({ onOpen, onCloseMobile }) {
  const dispatch = useDispatch();
  const { sessions = [], currentSessionId } = useSelector(s => s.chatdocs);
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [q, setQ] = useState('');

  const load = async () => {
    const res = await listSessions({ page: 1, page_size: 100, q });
    dispatch(setSessions(res.data.items || []));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q]);

  const del = async (id) => { await deleteSession(id); await load(); };

  const handleEdit = (id, currentTitle) => {
    setEditingId(id);
    setEditValue(currentTitle || '');
  };
  const handleEditSave = async (id) => {
    await renameSession(id, editValue);
    setEditingId(null);
    setEditValue('');
    await load();
  };
  const handleEditCancel = () => {
    setEditingId(null);
    setEditValue('');
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ p: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, flex: 1 }}>Chats</Typography>
        {onCloseMobile && (
          <Tooltip title="Close">
            <IconButton size="small" onClick={onCloseMobile}><CloseIcon fontSize="inherit" /></IconButton>
          </Tooltip>
        )}
      </Box>
      <Box sx={{ px: 1.5, pb: 1 }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Search chats"
          value={q}
          onChange={e => setQ(e.target.value)}
          InputProps={{ endAdornment: <InputAdornment position="end"><SearchIcon fontSize="small" /></InputAdornment> }}
        />
      </Box>
      <Divider />
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <List dense disablePadding>
          {sessions.map(s => (
            <ListItemButton
              key={s.id}
              selected={s.id === currentSessionId}
              onClick={() => { dispatch(setCurrentSession(s.id)); onOpen && onOpen(); }}
              sx={{ alignItems: 'flex-start', py: 1 }}
            >
              <ListItemText
                primary={editingId === s.id ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TextField
                      size="small"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      onBlur={() => handleEditSave(s.id)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') handleEditSave(s.id);
                        if (e.key === 'Escape') handleEditCancel();
                      }}
                      autoFocus
                      sx={{ minWidth: 120 }}
                    />
                    <IconButton size="small" onClick={handleEditCancel}><CloseIcon fontSize="small" /></IconButton>
                  </Box>
                ) : (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography noWrap fontWeight={600}>{s.title || `Chat ${String(s.id).slice(-6)}`}</Typography>
                    <IconButton size="small" onClick={e => { e.stopPropagation(); handleEdit(s.id, s.title); }}>
                      <SearchIcon fontSize="small" />
                    </IconButton>
                  </Box>
                )}
                secondary={<Typography variant="caption" color="text.secondary">{new Date(s.last_message_at).toLocaleString()}</Typography>}
              />
              <Tooltip title="Delete chat">
                <IconButton size="small" onClick={(e) => { e.stopPropagation(); del(s.id); }}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </ListItemButton>
          ))}
          {!sessions.length && (
            <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
              No chats yet. Select documents below and start one.
            </Typography>
          )}
        </List>
      </Box>
    </Box>
  );
}
