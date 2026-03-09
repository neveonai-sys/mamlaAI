import React from 'react';
import { Box, Typography, Grid, Card, CardContent, Button, Container } from '@mui/material';
import GavelIcon from '@mui/icons-material/Gavel';
import UpdateIcon from '@mui/icons-material/Update';
import DescriptionIcon from '@mui/icons-material/Description';
import PeopleIcon from '@mui/icons-material/People';
import ChatIcon from '@mui/icons-material/Chat';
import EventIcon from '@mui/icons-material/Event';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { useNavigate } from 'react-router-dom';

const WelcomePage = () => {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/login');
  };

  const handleGetSignup = () => {
    navigate('/signup');
  };

  const handleTestAIDrafting = () => {
    navigate('/test-ai-drafting');
  };

  return (
    <Box>
      {/* Hero Section */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #0D47A1, #1565C0)',
          padding: { xs: '60px 20px', md: '100px 20px' },
          textAlign: 'center',
          color: 'white'
        }}
      >
        <Typography variant="h2" component="h1" sx={{ fontWeight: 'bold', fontSize: { xs: '2.5rem', sm: '3rem' } }}>
          Mamla.Ai
        </Typography>
        <Typography variant="h5" sx={{ mt: 2, mb: 3, fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
          Complete legal management solution for modern law firms
        </Typography>
        
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mb: 3, flexWrap: 'wrap', px: { xs: 2, sm: 0 } }}>
          <Button
            variant="contained"
            color="secondary"
            size="large"
            onClick={handleGetStarted}
            sx={{ minWidth: { xs: 140, sm: 180 }, fontSize: { xs: '0.875rem', sm: '1rem' } }}
          >
            Login
          </Button>
          
          <Button
            variant="contained"
            color="secondary"
            size="large"
            onClick={handleGetSignup}
            sx={{ minWidth: { xs: 140, sm: 180 }, fontSize: { xs: '0.875rem', sm: '1rem' } }}
          >
            Sign Up
          </Button>
        </Box>

        <Typography variant="body2" sx={{ mb: 3, opacity: 0.9, px: { xs: 2, sm: 0 } }}>
          Try our AI Drafting feature for free. No signup required!
        </Typography>
        
        <Button
          variant="contained"
          color="warning"
          size="large"
          startIcon={<AutoAwesomeIcon />}
          onClick={handleTestAIDrafting}
          sx={{ 
            minWidth: { xs: 200, sm: 220 }, 
            fontSize: { xs: '0.875rem', sm: '1rem' },
            backgroundColor: '#ff9800', 
            '&:hover': { 
              backgroundColor: '#f57c00',
              boxShadow: '0 4px 8px rgba(0,0,0,0.2)'
            } 
          }}
        >
          Test AI Drafting
        </Button>
      </Box>

      {/* Features Section */}
      <Box sx={{ padding: '60px 20px' }}>
        <Typography variant="h4" textAlign="center" gutterBottom>
          Our Features
        </Typography>
        <Grid container spacing={4} justifyContent="center">
          {/* Case Updates */}
          <Grid item xs={12} sm={6} md={4}>
            <Card sx={{ textAlign: 'center', padding: '20px' }}>
              <CardContent>
                <UpdateIcon sx={{ fontSize: 50, color: '#0D47A1' }} />
                <Typography variant="h6" sx={{ mt: 2 }}>
                  Case Updates
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Stay informed with real time updates on your cases and court proceedings.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          {/* AI Based Drafting */}
          <Grid item xs={12} sm={6} md={4}>
            <Card sx={{ textAlign: 'center', padding: '20px' }}>
              <CardContent>
                <DescriptionIcon sx={{ fontSize: 50, color: '#0D47A1' }} />
                <Typography variant="h6" sx={{ mt: 2 }}>
                  AI Based Drafting
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Generate legal documents seamlessly using artificial intelligence.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          {/* Client Management */}
          <Grid item xs={12} sm={6} md={4}>
            <Card sx={{ textAlign: 'center', padding: '20px' }}>
              <CardContent>
                <PeopleIcon sx={{ fontSize: 50, color: '#0D47A1' }} />
                <Typography variant="h6" sx={{ mt: 2 }}>
                  Client Management
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Manage client data, appointments, and communications in one place.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          {/* Real Time Court Updates by Paralegals */}
          <Grid item xs={12} sm={6} md={4}>
            <Card sx={{ textAlign: 'center', padding: '20px' }}>
              <CardContent>
                <GavelIcon sx={{ fontSize: 50, color: '#0D47A1' }} />
                <Typography variant="h6" sx={{ mt: 2 }}>
                  Real Time Court Updates
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Receive instant court updates with the help of professional paralegals.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          {/* WhatsApp Integrated */}
          <Grid item xs={12} sm={6} md={4}>
            <Card sx={{ textAlign: 'center', padding: '20px' }}>
              <CardContent>
                <ChatIcon sx={{ fontSize: 50, color: '#0D47A1' }} />
                <Typography variant="h6" sx={{ mt: 2 }}>
                  WhatsApp Integrated
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Stay connected on-the-go with seamless WhatsApp integration.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          {/* Event & Calendar Management */}
          <Grid item xs={12} sm={6} md={4}>
            <Card sx={{ textAlign: 'center', padding: '20px' }}>
              <CardContent>
                <EventIcon sx={{ fontSize: 50, color: '#0D47A1' }} />
                <Typography variant="h6" sx={{ mt: 2 }}>
                  Event & Calendar Management
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Organize your schedule with timely reminders and a powerful calendar.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Footer Section */}
      <Box sx={{ backgroundColor: '#f5f5f5', padding: '20px', textAlign: 'center' }}>
        <Typography variant="body2">
          {new Date().getFullYear()} Mamla.Ai. All rights reserved.
        </Typography>
      </Box>
    </Box>
  );
};

export default WelcomePage;