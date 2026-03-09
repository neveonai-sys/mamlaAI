// src/components/ForgetPassword.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  InputAdornment,
  IconButton
} from '@mui/material';
import { styled } from '@mui/material/styles';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import AxiosInstance from '../common/AxiosInstance';

// ~~~~~~ THEME / STYLED COMPONENTS ~~~~~~

// Match your existing Signup / Login theme (blue gradient)
const BackgroundBox = styled(Box)(({ theme }) => ({
  width: '100vw',
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'linear-gradient(135deg, #0D47A1, #1565C0)', // same as your Signup
  padding: theme.spacing(2),
}));

const WhiteBox = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  minWidth: 320,
  width: '100%',
  maxWidth: 600,
  borderRadius: theme.shape.borderRadius,
  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
  backgroundColor: theme.palette.background.paper,
  [theme.breakpoints.down('sm')]: {
    width: '90%',
    padding: theme.spacing(3),
  },
}));

const ItemBox = styled(Box)(({ theme }) => ({
  marginBottom: theme.spacing(2),
}));

const StyledButton = styled(Button)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  color: '#fff',
  borderRadius: 5,
  padding: theme.spacing(1.5),
  fontSize: 16,
  width: '100%',
  '&:hover': {
    backgroundColor: theme.palette.primary.dark,
  },
  '&:focus': {
    outline: '2px solid #fff',
    outlineOffset: '2px',
  },
  transition: 'background-color 0.3s ease, outline 0.3s ease',
}));

// We keep the same name as in your snippet
const ResetPassword = () => {
  const navigate = useNavigate();

  // STEP 1 state (Send reset link)
  const [email_id, setEmail] = useState('');
  const [linkSent, setLinkSent] = useState(false);

  // STEP 2 state (Reset with token)
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // General feedback
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // On mount, parse the token from ?token= or ?supabase_token=, etc.
  useEffect(() => {
    const hash = window.location.hash; 
      // remove the "#" at the start
      const params = new URLSearchParams(hash.substring(1));
    const tokenFromUrl = params.get('access_token');
    // or if supabase appends it as 'supabase_token', do:
    // const tokenFromUrl = params.get('supabase_token');
      // console.log("========== params ==========", params)
      // console.log("========== tokenFromUrl ==========", tokenFromUrl)

    if (tokenFromUrl) {
      setResetToken(tokenFromUrl);
    }
  }, []);

  // ============= STEP 1: Send Reset Link =============
  const handleSendResetLink = async (e) => {
    e.preventDefault(); // let Enter key submit
    setErrorMessage('');
    setSuccessMessage('');
    setLinkSent(false);

    if (!email_id) {
      setErrorMessage('Please enter your email.');
      return;
    }

    try {
      // Django endpoint: send_reset_password_link
      const response = await AxiosInstance.post('users/send-reset-password-link/', {
        email_id,
      });

      if (response.data.success === true) {
        setLinkSent(true);
        setSuccessMessage('Reset link sent to your email address.');
      } else {
        setErrorMessage('Something went wrong. Please try again.');
      }
    } catch (error) {
      console.error('Error sending reset link:', error);
      let msg = 'Error sending reset link. Please try again.';
      if (error.response && error.response.data && error.response.data.message) {
        msg = error.response.data.message;
      }
      setErrorMessage(msg);
    }
  };

  // ============= STEP 2: Reset w/ Token =============
  const handleResetPassword = async (e) => {
    e.preventDefault(); // let Enter key submit
    setPasswordError('');
    setErrorMessage('');
    setSuccessMessage('');

    // 1) Check match
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match.');
      return;
    }

    // 2) Check complexity
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?#&]).{6,}$/;
    if (!passwordRegex.test(newPassword)) {
      setPasswordError(
        'Password must be at least 6 characters and include uppercase, lowercase, digit, and a special character.'
      );
      return;
    }

    try {
      // Django endpoint: reset_password
      // Expects { new_password, recovery_access_token }
      const response = await AxiosInstance.post('users/reset-user-password/', {
        new_password: newPassword,
        recovery_access_token: resetToken,
      });

      if (response.data.success === true) {
        setSuccessMessage('Password reset successful! Redirecting to login...');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else {
        setErrorMessage(
          response.data.message || 'Something went wrong. Please try again.'
        );
      }
    } catch (error) {
      console.error('Error resetting password:', error);
      let msg = 'Error resetting password. Please try again.';
      if (error.response && error.response.data && error.response.data.message) {
        msg = error.response.data.message;
      }
      setErrorMessage(msg);
    }
  };

  // ==================== RENDERING ====================
  // If we found a token => Step 2: "Reset Your Password"
  if (resetToken) {
    return (
      <BackgroundBox>
        <WhiteBox elevation={3}>
          <Typography variant="h5" align="center" gutterBottom>
            Reset Your Password
          </Typography>

          <Box component="form" onSubmit={handleResetPassword}>
            <ItemBox>
              <TextField
                label="New Password"
                type={showNewPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                fullWidth
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowNewPassword((prev) => !prev)}
                        edge="end"
                      >
                        {showNewPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </ItemBox>

            <ItemBox>
              <TextField
                label="Confirm Password"
                type={showConfirmPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                fullWidth
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowConfirmPassword((prev) => !prev)}
                        edge="end"
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </ItemBox>

            {passwordError && (
              <Typography color="error" align="center" sx={{ mb: 2 }}>
                {passwordError}
              </Typography>
            )}
            {errorMessage && (
              <Typography color="error" align="center" sx={{ mb: 2 }}>
                {errorMessage}
              </Typography>
            )}
            {successMessage && (
              <Typography color="primary" align="center" sx={{ mb: 2 }}>
                {successMessage}
              </Typography>
            )}

            <StyledButton type="submit" variant="contained">
              Reset Password
            </StyledButton>
          </Box>

          <Box mt={2} textAlign="center">
            <Button onClick={() => navigate('/login')}>
              Back to Login
            </Button>
          </Box>
        </WhiteBox>
      </BackgroundBox>
    );
  }

  // If no token => Step 1: "Send Reset Link"
  return (
    <BackgroundBox>
      <WhiteBox elevation={3}>
        <Typography variant="h5" align="center" gutterBottom>
          Forgot Your Password?
        </Typography>

        <Box component="form" onSubmit={handleSendResetLink}>
          <ItemBox>
            <TextField
              label="Email"
              type="email"
              value={email_id}
              onChange={(e) => setEmail(e.target.value)}
              required
              fullWidth
            />
          </ItemBox>

          {errorMessage && (
            <Typography color="error" align="center" sx={{ mb: 2 }}>
              {errorMessage}
            </Typography>
          )}
          {successMessage && (
            <Typography color="primary" align="center" sx={{ mb: 2 }}>
              {successMessage}
            </Typography>
          )}
{/*{linkSent && (
            <Typography color="primary" align="center" sx={{ mb: 2 }}>
              A reset link has been sent to your email.
            </Typography>
          )}*/}

          <StyledButton type="submit" variant="contained">
            Send Reset Link
          </StyledButton>
        </Box>

        <Box mt={2} textAlign="center">
          <Button
            onClick={() => navigate('/login')}
            style={{ textDecoration: 'underline' }}
          >
            Back to Login
          </Button>
        </Box>
      </WhiteBox>
    </BackgroundBox>
  );
};

export default ResetPassword;
