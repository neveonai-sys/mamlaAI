import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Box,
  Grid,
  Typography,
  Radio,
  RadioGroup,
  FormControl,
  FormControlLabel,
  FormLabel,
  TextField,
  Paper,
  InputAdornment,
  IconButton,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

import { styled } from '@mui/material/styles';
import { useDispatch } from 'react-redux';
import { setUser } from '../../features/userSlice';
import AxiosInstance from '../common/AxiosInstance';
import { getDeviceInfo } from '../../utils/getDeviceInfo';
import { 
  secureSessionStorage, 
  sanitizeInput, 
  isValidEmail, 
  isStrongPassword 
} from '../../utils/securityUtils';
import { Link as RouterLink } from 'react-router-dom';

/* ---------- styled shells ---------- */
const FullHeightBox = styled(Box)({
  minHeight: '100vh',
  width: '100%',
  display: 'flex'
});

const StyledLink = styled(Link)(({ theme }) => ({
  textDecoration: 'none',
  color: theme.palette.primary.main,
  '&:hover': {
    textDecoration: 'underline',
  },
}));

const Banner = styled(Box)(({ theme }) => ({
  backgroundColor: '#062448',                      // deep navy
  color: theme.palette.common.white,
  padding: theme.spacing(8),
  [theme.breakpoints.down('md')]: {
    display: 'none'
  },
  flex: 1
}));

const Highlight = styled('span')(({ theme }) => ({
  color: theme.palette.warning.main,
  fontWeight: 700
}));

const FormWrapper = styled(Paper)(({ theme }) => ({
  margin: 'auto',
  padding: theme.spacing(5),
  maxWidth: 480,
  width: '100%',
  borderRadius: 12,
  boxShadow: theme.shadows[4]
}));

const PrimaryButton = styled(Button)(({ theme }) => ({
  marginTop: theme.spacing(2),
  padding: theme.spacing(1.3),
  borderRadius: 6,
  backgroundColor: theme.palette.primary.main,
  color: '#fff',
  '&:hover': { backgroundColor: theme.palette.primary.dark }
}));

const FormContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  px: { xs: 2, md: 6 },
  py: { xs: 4, md: 0 }
}));

const FormPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(5),
  maxWidth: 480,
  width: '100%',
  borderRadius: 12,
  boxShadow: theme.shadows[4]
}));

const ErrorAlert = styled(Alert)(({ theme }) => ({
  marginBottom: theme.spacing(2)
}));

/* ----------------------------------- */

const Login = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const deviceType = getDeviceInfo();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleEmailChange = (e) => {
    const sanitized = sanitizeInput(e.target.value);
    setEmail(sanitized);
    
    if (sanitized && !isValidEmail(sanitized)) {
      setError('Please enter a valid email address');
    } else {
      setError('');
    }
  };

  const handleClickShowPassword = () => {
    setShowPassword(!showPassword);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!email || !password) {
      setError('Please fill in all required fields');
      return;
    }
    
    if (!isValidEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }
    
    setIsLoading(true);
    
    try {
      const deviceInfo = getDeviceInfo();
      
      const response = await AxiosInstance.post('/users/login-user/', {
        email: email.trim().toLowerCase(),
        password: password,
        device_info: deviceInfo
      });
      
      // Store basic user info for immediate UI feedback (optional)
      secureSessionStorage.setItem('userData', response.data);

      // Immediately verify auth using the new HttpOnly cookie
      try {
        const authResp = await AxiosInstance.get('/users/check-auth/');
        if (authResp.data?.isAuthenticated) {
          dispatch(setUser({
            firstname: authResp.data.firstname,
            lastname: authResp.data.lastname,
            email: authResp.data.email_id,
            user_type: authResp.data.user_type,
            sessions: authResp.data.sessions,
          }));
        }
      } catch (checkErr) {
        console.warn('Auth verify failed right after login', checkErr);
      }

      const redirectTo = location.state?.from?.pathname || '/home';
      navigate(redirectTo);
      
    } catch (err) {
      console.error('Login error:', err);
      
      const errorMessage = err.response?.data?.message || 'Login failed. Please check your credentials and try again.';
      setError(errorMessage);
      
      setPassword('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <FullHeightBox>
      {/* ---------- LEFT BANNER ---------- */}
      <Banner>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
          <Highlight>Intelligent</Highlight> Legal Management
        </Typography>
        <Typography variant="body1" sx={{ mb: 4, maxWidth: 360 }}>
          AI‑powered assistant for case tracking, drafting and client
          collaboration.
        </Typography>

        <List dense>
          {[
            'AI‑Assisted Drafting – Generate pleadings, petitions and contracts with jurisdiction‑specific precision',
            'Live Docket Monitoring – Automatic sync with e‑Courts for stage, order and causelist alerts',
            'Secure Client & Matter Hub – Centralise briefs, evidence and correspondence in an encrypted workspace',
            'On‑Demand Paralegal Dispatch – Geo‑matched professionals for filing, appearances and service of process',
            'Compliance & Limitation Calendar – Statutory deadlines and hearing dates, pushed to WhatsApp & email',
            'Conversational Interface – Query matters or create documents in plain English',
            'Multi‑Agent Collaboration – Human + AI agents orchestrating tasks across the firm'
            ].map(text => (
            <ListItem key={text} disableGutters sx={{ alignItems: 'flex-start' }}>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <CheckCircleIcon color="warning" fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary={<Typography variant="body2">{text}</Typography>}
              />
            </ListItem>
          ))}
        </List>
      </Banner>

      {/* ---------- RIGHT FORM PANEL ---------- */}
      <Grid
        item
        xs={12}
        md={7}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          px: { xs: 2, md: 6 },
          py: { xs: 4, md: 0 }
        }}
      >
        <FormContainer>
          <FormPaper elevation={3}>
            <Typography variant="h5" gutterBottom align="center">
            <StyledLink to="/">Mamla.Ai</StyledLink>
            </Typography>
            <Typography variant="h6" align="center" gutterBottom>
              Welcome
            </Typography>
            
            {error && (
              <ErrorAlert severity="error" onClose={() => setError('')}>
                {error}
              </ErrorAlert>
            )}
            
            <form onSubmit={handleSubmit}>
              <FormControl fullWidth margin="normal" required>
                <FormLabel>Email</FormLabel>
                <TextField
                  type="email"
                  value={email}
                  onChange={handleEmailChange}
                  placeholder="Enter your email"
                  variant="outlined"
                  fullWidth
                  margin="normal"
                  required
                  autoComplete="email"
                />
              </FormControl>
              
              <FormControl fullWidth margin="normal" required>
                <FormLabel>Password</FormLabel>
                <TextField
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(sanitizeInput(e.target.value))}
                  placeholder="Enter your password"
                  variant="outlined"
                  fullWidth
                  margin="normal"
                  required
                  autoComplete="current-password"
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          aria-label="toggle password visibility"
                          onClick={handleClickShowPassword}
                          edge="end"
                        >
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              </FormControl>
              
              <Box mt={3}>
                <Button
                  type="submit"
                  variant="contained"
                  color="primary"
                  fullWidth
                  size="large"
                  disabled={isLoading || !email || !password}
                >
                  {isLoading ? 'Signing in...' : 'Sign In'}
                </Button>
              </Box>
              
              <Box mt={2} textAlign="center">
                <Typography variant="body2" color="primary">
                  <StyledLink to="/reset-password">Forgot your password?</StyledLink>
                </Typography>
              </Box>
              
              <Box mt={1} textAlign="center">
                <Typography variant="body2" fontSize="0.9rem">
                  New user?{' '}
                  <StyledLink to="/signup">Please signup!</StyledLink>
                </Typography>
              </Box>
            </form>
          </FormPaper>
        </FormContainer>
      </Grid>
    </FullHeightBox>
  );
};

export default Login;
