import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#0D47A1', // Deep blue for professionalism
    },
    secondary: {
      main: '#FFC107', // Amber/gold accent
    },
    background: {
      default: '#F1F4F9',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#263238',
      secondary: '#546e7a',
    },
  },
  typography: {
    fontFamily: ['Roboto', 'sans-serif'].join(','),
    h4: {
      fontWeight: 600,
    },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#FFFFFF',
        },
      },
    },
  },
});

export default theme; 