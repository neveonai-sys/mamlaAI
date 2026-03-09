import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { Box, Button, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';

const ROOT = styled(Box)(({ theme }) => ({
  minHeight: '100vh',
  position: 'relative',
  backgroundColor: theme.palette.background.default,
}));

const FloatingButtonContainer = styled(Box)(({ theme }) => ({
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: theme.spacing(4),
  zIndex: 1,
  // Mobile responsive
  [theme.breakpoints.down('sm')]: {
    flexDirection: 'column',
    gap: theme.spacing(2),
    width: '90%',
  },
}));

const StyledButton = styled(Button)(({ theme }) => ({
  width: 100,
  height: 100,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[3],
  fontSize: 16,
  fontWeight: 'bold',
  textTransform: 'none',
  transition: 'transform 0.3s ease',
  '&:hover': {
    transform: 'scale(1.05)',
  },
  // Mobile responsive
  [theme.breakpoints.down('sm')]: {
    width: '100%',
    height: 80,
    fontSize: 14,
  },
}));

const Home = () => {
  const { firstname, lastname, user_type } = useSelector((state) => state.user);
  const navigate = useNavigate();

  useEffect(() => {
    console.log('Home component - firstname:', firstname, 'lastname:', lastname);
    if (!firstname || !lastname) {
      navigate('/login');
    }
  }, [firstname, lastname, navigate]);

  const handleNavigate = (path) => {
    navigate(path);
  };

  return (
    <ROOT>
      <Box sx={{ padding: { xs: 2, md: 3 } }}>
        <Typography variant="h4" align="center" sx={{ fontSize: { xs: '1.5rem', sm: '2rem', md: '2.125rem' } }}>
          Welcome, {firstname} {lastname}!
        </Typography>
      </Box>
      <FloatingButtonContainer>
        <StyledButton variant="contained" color="primary" onClick={() => handleNavigate('/calendar')}>
          Calendar
        </StyledButton>
        {user_type === 'Lawyer' && (
          <>
            <StyledButton
              variant="contained"
              sx={{ backgroundColor: '#2E7D32', '&:hover': { backgroundColor: '#1B5E20' } }}
              onClick={() => handleNavigate('/draft-with-ai')}
            >
              AI Draft
            </StyledButton>
            <StyledButton variant="contained" color="secondary" onClick={() => handleNavigate('/onboard-client')}>
              Onboard
            </StyledButton>
          </>
        )}
      </FloatingButtonContainer>
    </ROOT>
  );
};

export default Home;
