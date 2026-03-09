import React, { useEffect, useRef, useState } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Chip, 
  TextField, 
  Button, 
  Stack, 
  Alert, 
  CircularProgress, 
  IconButton, 
  Tooltip, 
  Fade,
  Card,
  CardContent,
  CardActionArea,
  Grid,
  Container
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import SearchIcon from '@mui/icons-material/Search';
import SummarizeIcon from '@mui/icons-material/Summarize';
import FindInPageIcon from '@mui/icons-material/FindInPage';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import { useDispatch, useSelector } from 'react-redux';
import { getMessages, sendMessage } from './talktodocApi';
import { appendMessage, setMessages } from '../../features/chatDocsSlice';

const suggestedPrompts = [
  {
    title: 'Summarize Legal Documents',
    description: 'Get a clear, professional summary of your legal documents with key points highlighted.',
    icon: <SummarizeIcon />,
    prompt: 'Please provide a comprehensive legal summary of the uploaded documents, highlighting the parties involved, key clauses, obligations, and important dates. Present the information in a clear, professional manner suitable for both lawyers and clients.'
  },
  {
    title: 'Identify Key Legal Points',
    description: 'Extract critical clauses, deadlines, obligations, and rights from your documents.',
    icon: <FindInPageIcon />,
    prompt: 'Please identify and explain all key legal points in these documents, including: (1) Parties and their roles, (2) Important clauses and conditions, (3) Critical dates and deadlines, (4) Rights and obligations of each party, (5) Payment terms or financial obligations. Explain each point in simple, professional language.'
  },
  {
    title: 'Assess Legal Risks',
    description: 'Analyze potential legal risks, concerns, and areas requiring attention in your documents.',
    icon: <SearchIcon />,
    prompt: 'Please analyze these documents for potential legal risks, concerns, or issues that require attention. Highlight any ambiguous clauses, unfavorable terms, missing information, or areas that may need legal review. Explain each concern in clear language that both lawyers and clients can understand.'
  },
  {
    title: 'Ask Legal Question',
    description: 'Ask specific legal questions about your documents or general legal procedures.',
    icon: <LightbulbIcon />,
    prompt: ''
  },
];

export default function ChatPane() {
  const dispatch = useDispatch();
  const { currentSessionId, messages = [], selectedDocs = [] } = useSelector(s => s.chatdocs);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showPrompts, setShowPrompts] = useState(true);
  const scrollerRef = useRef(null);

  const canSend = Boolean(currentSessionId);

  const load = async () => {
    if (!currentSessionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getMessages(currentSessionId);
      dispatch(setMessages(res.data.messages || []));
      setShowPrompts(res.data.messages?.length === 0);
    } catch (err) {
      setError('Failed to load messages');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [currentSessionId]);
  useEffect(() => { 
    if (scrollerRef.current) scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight; 
    setShowPrompts(messages.length === 0 && currentSessionId);
  }, [messages, sending, currentSessionId]);

  const handlePromptClick = (prompt) => {
    if (prompt) {
      setText(prompt);
      setShowPrompts(false);
    }
  };

  const onSend = async () => {
    const content = text.trim();
    if (!content || !canSend) return;
    setShowPrompts(false);
    dispatch(appendMessage({ role: 'user', content, created_at: new Date().toISOString() }));
    setText(''); setSending(true); setError(null);
    try {
      const res = await sendMessage(currentSessionId, content);
      dispatch(appendMessage({
        role: 'assistant', content: res.data.message, citations: res.data.citations, created_at: new Date().toISOString()
      }));
    } catch (err) {
      setError('Failed to send message. Please try again.');
    } finally { setSending(false); }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#FAFAFA' }}>
      {/* Professional Header */}
      <Box sx={{ 
        py: 3, 
        px: 4, 
        borderBottom: '1px solid #E5E7EB', 
        bgcolor: 'white',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        <Stack direction="row" alignItems="center" spacing={2}>
          <Box sx={{
            width: 48,
            height: 48,
            borderRadius: '12px',
            bgcolor: 'primary.main',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <SmartToyIcon sx={{ color: 'white', fontSize: 28 }} />
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#111827', mb: 0.5 }}>
              {showPrompts && !messages.length ? 'Ask A Question' : 'Chat with Documents'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {selectedDocs.length > 0 
                ? `Chatting with ${selectedDocs.length} document${selectedDocs.length > 1 ? 's' : ''}`
                : 'Start by uploading documents or ask general questions'}
            </Typography>
          </Box>
          {currentSessionId && (
            <Tooltip title="Restart conversation">
              <IconButton 
                size="small" 
                onClick={load}
                sx={{ 
                  bgcolor: '#F3F4F6',
                  '&:hover': { bgcolor: '#E5E7EB' }
                }}
              >
                <RestartAltIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ m: 2, borderRadius: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* No Session Warning */}
      {!currentSessionId && (
        <Alert severity="info" sx={{ m: 2, borderRadius: 2 }}>
          👉 Upload documents and start a new chat session to begin.
        </Alert>
      )}

      {/* Main Content Area */}
      <Box ref={scrollerRef} sx={{ flex: 1, overflow: 'auto', px: 2, py: 3 }}>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        )}
        
        {/* Suggested Prompts - Card Based Design */}
        {!loading && showPrompts && currentSessionId && (
          <Container maxWidth="lg">
            <Fade in>
              <Box>
                <Box sx={{ textAlign: 'center', mb: 4, mt: 2 }}>
                  <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 700, mx: 'auto' }}>
                    Use Legal Chat to quickly explore legal strategies, uncover defenses, plan next steps, and more. 
                    Each prompt is designed to give practical, thoughtful guidance based on real legal needs.
                  </Typography>
                </Box>
                
                <Grid container spacing={2}>
                  {suggestedPrompts.map((item, idx) => (
                    <Grid item xs={12} key={idx}>
                      <Card 
                        elevation={0}
                        sx={{ 
                          border: '1px solid #E5E7EB',
                          borderRadius: 2,
                          transition: 'all 0.2s',
                          '&:hover': {
                            borderColor: 'primary.main',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                            transform: 'translateY(-2px)'
                          }
                        }}
                      >
                        <CardActionArea 
                          onClick={() => handlePromptClick(item.prompt)}
                          sx={{ p: 2.5 }}
                        >
                          <Stack direction="row" spacing={2} alignItems="center">
                            <Box sx={{ color: '#6B7280', display: 'flex' }}>
                              {item.icon}
                            </Box>
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#111827', mb: 0.5 }}>
                                {item.title}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {item.description}
                              </Typography>
                            </Box>
                            <ArrowForwardIcon sx={{ color: '#9CA3AF' }} />
                          </Stack>
                        </CardActionArea>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </Box>
            </Fade>
          </Container>
        )}

        {/* Chat Messages */}
        {!loading && !showPrompts && (
          <Container maxWidth="lg">
            {messages.map((m, i) => <Message key={i} role={m.role} content={m.content} citations={m.citations} />)}
            {sending && (
              <BotBubble>
                <Stack direction="row" spacing={1} alignItems="center">
                  <CircularProgress size={16} />
                  <em>Analyzing your documents...</em>
                </Stack>
              </BotBubble>
            )}
          </Container>
        )}
      </Box>

      {/* Enhanced Composer */}
      <Box sx={{ 
        p: 3, 
        borderTop: '1px solid #E5E7EB', 
        bgcolor: 'white',
        boxShadow: '0 -2px 8px rgba(0,0,0,0.05)'
      }}>
        <Container maxWidth="lg">
          <Stack spacing={1.5}>
            <Stack direction="row" spacing={2}>
              <TextField
                fullWidth 
                size="medium"
                placeholder={canSend ? "Ask me anything about your documents..." : "Start a chat session first"}
                value={text} 
                onChange={e => setText(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); } }}
                disabled={!canSend || sending} 
                multiline 
                minRows={1} 
                maxRows={4}
                sx={{ 
                  '& .MuiOutlinedInput-root': { 
                    borderRadius: 3,
                    bgcolor: '#F9FAFB',
                    fontSize: '0.95rem',
                    '& fieldset': {
                      borderColor: '#E5E7EB',
                    },
                    '&:hover fieldset': {
                      borderColor: '#D1D5DB',
                    },
                    '&.Mui-focused fieldset': {
                      borderWidth: 2,
                    }
                  } 
                }}
              />
              <Button 
                variant="contained" 
                onClick={onSend} 
                disabled={!canSend || !text.trim() || sending}
                sx={{ 
                  minWidth: 120, 
                  height: 56,
                  borderRadius: 3,
                  px: 4,
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  textTransform: 'none',
                  boxShadow: 'none',
                  '&:hover': {
                    boxShadow: '0 4px 12px rgba(25, 118, 210, 0.3)'
                  }
                }}
                endIcon={sending ? <CircularProgress size={18} color="inherit" /> : <SendIcon />}
              >
                {sending ? 'Sending' : 'Send'}
              </Button>
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', fontSize: '0.75rem' }}>
              Press Enter to send • Shift+Enter for new line
            </Typography>
          </Stack>
        </Container>
      </Box>
    </Box>
  );
}

function Message({ role, content, citations = [] }) {
  const isAssistant = role === 'assistant';
  return isAssistant ? <BotBubble citations={citations}>{content}</BotBubble> : <UserBubble>{content}</UserBubble>;
}
function BotBubble({ children, citations = [] }) {
  return (
    <Fade in>
      <Box sx={{ display: 'flex', justifyContent: 'flex-start', my: 1.5, gap: 1 }}>
        <Box sx={{ 
          width: 32, 
          height: 32, 
          borderRadius: '50%', 
          bgcolor: 'primary.main', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          flexShrink: 0,
          mt: 0.5
        }}>
          <SmartToyIcon sx={{ fontSize: 18, color: 'white' }} />
        </Box>
        <Paper elevation={0} sx={{ p: 2, maxWidth: { xs: '85%', md: '75%' }, bgcolor: 'white', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{children}</Typography>
          {!!citations.length && (
            <Box sx={{ mt: 1.5, pt: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>📚 Sources:</Typography>
              <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
                {citations.map((c, i) => (
                  <Chip 
                    key={i} 
                    size="small" 
                    label={`${c.doc_name} • p.${c.page || '?'}`} 
                    variant="outlined"
                    sx={{ fontSize: '0.7rem' }}
                  />
                ))}
              </Stack>
            </Box>
          )}
        </Paper>
      </Box>
    </Fade>
  );
}
function UserBubble({ children }) {
  return (
    <Fade in>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', my: 1.5 }}>
        <Paper elevation={0} sx={{ p: 2, maxWidth: { xs: '85%', md: '75%' }, bgcolor: 'primary.main', color: 'white', borderRadius: 2 }}>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{children}</Typography>
        </Paper>
      </Box>
    </Fade>
  );
}
