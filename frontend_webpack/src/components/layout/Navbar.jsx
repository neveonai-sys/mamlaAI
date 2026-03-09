// src/components/Navbar.js

import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Avatar,
  Badge,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Typography,
  useMediaQuery,
  Chip,
} from '@mui/material';
import { styled, useTheme } from '@mui/material/styles';
import {
  Home as HomeIcon,
  Event as EventIcon,
  Logout as LogoutIcon,
  Description as DescriptionIcon,
  PersonAdd as PersonAddIcon,
  Feedback as FeedbackIcon,
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  QuestionAnswer as QuestionAnswerIcon,
  Chat as ChatIcon,
  Gavel as GavelIcon,
} from '@mui/icons-material';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { clearUser } from '../../features/userSlice';
import AxiosInstance from '../common/AxiosInstance';

const drawerWidth = 240;
const miniDrawerWidth = 64;
const sidebarBg = '#FFFFFF';
const sidebarBorder = '#E5E7EB';

const AppBarStyled = styled(AppBar, {
  shouldForwardProp: (prop) => prop !== 'open',
})(({ theme, open }) => ({
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.common.white,
  transition: theme.transitions.create(['width', 'margin'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  marginLeft: open ? drawerWidth : miniDrawerWidth,
  width: `calc(100% - ${open ? drawerWidth : miniDrawerWidth}px)`,
  '& .MuiSvgIcon-root': {
    color: theme.palette.common.white,
  },
  [theme.breakpoints.down('sm')]: {
    width: '100%',
    marginLeft: 0,
  },
}));

const DrawerStyled = styled(Drawer, {
  shouldForwardProp: (prop) => prop !== 'open',
})(({ theme, open }) => ({
  width: open ? drawerWidth : miniDrawerWidth,
  flexShrink: 0,
  whiteSpace: 'nowrap',
  '& .MuiDrawer-paper': {
    width: open ? drawerWidth : miniDrawerWidth,
    overflowX: 'hidden',
    backgroundColor: sidebarBg,
    color: '#374151',
    boxSizing: 'border-box',
    borderRight: `1px solid ${sidebarBorder}`,
    transition: theme.transitions.create(['width', 'margin'], {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen,
    }),
    '& .MuiListItemIcon-root, & .MuiSvgIcon-root': {
      color: '#6B7280',
      minWidth: 0,
      mr: open ? 2 : 'auto',
      justifyContent: 'center',
    },
    '& .MuiListItemText-root': {
      opacity: open ? 1 : 0,
      transition: 'opacity 0.2s',
      '& .MuiTypography-root': {
        fontSize: '0.875rem',
        fontWeight: 500,
        color: '#374151',
      },
    },
  },
}));

const getMenuItems = (user_type) => {
  const menu = [
    { text: 'Home', icon: <HomeIcon />, path: '/home' },
    { text: 'eCourts', icon: <GavelIcon />, path: '/ecourts' },
    { text: 'Calendar', icon: <EventIcon />, path: '/calendar' },
    { text: 'Draft with AI', icon: <DescriptionIcon />, path: '/draft-with-ai' },
    { text: 'Chat with Docs', icon: <ChatIcon />, path: '/chat-with-docs' },
  ];
  // if (user_type === 'Lawyer' || user_type === 'Client') {
  //   menu.push({ text: 'Talk to Doc', icon: <QuestionAnswerIcon />, path: '/talkdoc' });
  // }
  if (user_type === 'Lawyer') {
    menu.push(
      { text: 'Onboard Client', icon: <PersonAddIcon />, path: '/onboard-client' },
      // { text: 'Talk to Doc', icon: <QuestionAnswerIcon />, path: '/talkdoc' }
    );
  } else if (user_type === 'Paralegal') {
    menu.push({ text: 'My Updates', icon: <EventIcon />, path: '/my-updates' });
  }
  menu.push({ text: 'Feedback', icon: <FeedbackIcon />, path: '/feedback' });
  return menu;
};

export default function Navbar() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const { firstname, lastname, email, user_type } = useSelector((s) => s.user);
  const menuItems = getMenuItems(user_type);

  const [logoutDialogOpen, setLogoutDialogOpen] = React.useState(false);

  const [open, setOpen] = useState(!isMobile);
  const handleDrawerToggle = () => setOpen((prev) => !prev);

  // Auto-expand on desktop
  useEffect(() => {
    if (!isMobile) setOpen(true);
  }, [isMobile]);

  const [menuAnchor, setMenuAnchor] = useState(null);
  const doLogout = async () => {
    try {
      await AxiosInstance.post('users/sign-out-user/', { scope: 'local' });
    } catch {}
    dispatch(clearUser());
    navigate('/login');
  };
  const handleLogoutClick = () => setLogoutDialogOpen(true);
  const handleLogoutConfirm = () => {
    setLogoutDialogOpen(false);
    doLogout();
  };
  const handleLogoutCancel = () => setLogoutDialogOpen(false);

  return (
    <>
      <CssBaseline />

      <AppBarStyled position="fixed" open={open}>
        <Toolbar>
          {/* Hamburger menu for mobile */}
          {isMobile && (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              onClick={handleDrawerToggle}
              edge="start"
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}
          
          <Box sx={{ flexGrow: 1 }} />

          <IconButton onClick={(e) => setMenuAnchor(e.currentTarget)}>
            <Avatar sx={{ bgcolor: theme.palette.secondary.main }}>
              {firstname?.[0] || 'U'}
            </Avatar>
          </IconButton>

          <Menu
            anchorEl={menuAnchor}
            open={Boolean(menuAnchor)}
            onClose={() => setMenuAnchor(null)}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
          >
            <Box sx={{ px: 2.5, pt: 2 }}>
              <Typography fontWeight={600}>{`${firstname} ${lastname}`}</Typography>
              <Typography variant="body2" color="text.secondary">
                {email}
              </Typography>
              <Chip size="small" label={user_type} sx={{ mt: 1 }} />
            </Box>
            <Divider />
            <MenuItem disabled>My Profile</MenuItem>
            <MenuItem disabled>Settings</MenuItem>
            <MenuItem disabled>Notifications</MenuItem>
            <MenuItem component={Link} to="/sessions" onClick={() => setMenuAnchor(null)}>
              <ListItemIcon>
                <Badge color="primary" variant="dot">
                  <NotificationsIcon />
                </Badge>
              </ListItemIcon>
              Sessions
            </MenuItem>
            <Divider />
            <MenuItem
                  onClick={() => {
                    setMenuAnchor(null);
                    doLogout();
                  }}
                >
              <ListItemIcon>
                <LogoutIcon />
              </ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBarStyled>

      <DrawerStyled
        variant={isMobile ? 'temporary' : 'permanent'}
        open={open}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
        sx={{
          display: { xs: 'block' },
          '& .MuiDrawer-paper': { 
            boxSizing: 'border-box',
            zIndex: (theme) => theme.zIndex.drawer,
          },
        }}
      >
        {/* Fixed Logo/Brand Header */}
        <Box sx={{ 
          p: 2.5, 
          borderBottom: `1px solid ${sidebarBorder}`,
          bgcolor: sidebarBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: open ? 'flex-start' : 'center',
          gap: 1.5,
          minHeight: '72px'
        }}>
          {!open && (
            <IconButton 
              onClick={handleDrawerToggle} 
              size="medium"
              sx={{ 
                color: 'primary.main',
                bgcolor: '#F3F4F6',
                '&:hover': {
                  bgcolor: '#E5E7EB'
                }
              }}
            >
              <MenuIcon />
            </IconButton>
          )}
          {open && (
            <>
              <Box sx={{
                width: 40,
                height: 40,
                borderRadius: '8px',
                bgcolor: 'primary.main',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                <GavelIcon sx={{ color: 'white', fontSize: 24 }} />
              </Box>
              <Typography variant="h6" sx={{ 
                fontWeight: 700, 
                color: '#111827',
                fontSize: '1.25rem',
                letterSpacing: '-0.01em',
                flex: 1
              }}>
                Mamla.AI
              </Typography>
              <IconButton 
                onClick={handleDrawerToggle} 
                size="small"
                sx={{ 
                  color: '#6B7280',
                  '&:hover': {
                    bgcolor: '#F3F4F6'
                  }
                }}
              >
                <MenuIcon fontSize="small" />
              </IconButton>
            </>
          )}
        </Box>
        <List>
          {menuItems.map(({ text, icon, path }) => (
            <ListItem key={text} disablePadding>
                <ListItemButton
                selected={pathname === path || (path !== '/home' && pathname.startsWith(path + '/'))}
                component={Link}
                to={path}
                onClick={isMobile ? handleDrawerToggle : undefined}
                sx={{
                  justifyContent: open ? 'initial' : 'center',
                  px: 2.5,
                  py: 1.25,
                  mx: 1,
                  my: 0.25,
                  borderRadius: '8px',
                  color: (pathname === path || (path !== '/home' && pathname.startsWith(path + '/'))) ? 'primary.main' : '#6B7280',
                  bgcolor: (pathname === path || (path !== '/home' && pathname.startsWith(path + '/'))) ? 'primary.lighter' : 'transparent',
                  '&:hover': {
                    bgcolor: (pathname === path || (path !== '/home' && pathname.startsWith(path + '/'))) ? 'primary.lighter' : '#F3F4F6',
                  },
                  '&.Mui-selected': {
                    bgcolor: 'rgba(25, 118, 210, 0.08)',
                    '&:hover': {
                      bgcolor: 'rgba(25, 118, 210, 0.12)',
                    },
                    '& .MuiListItemIcon-root': {
                      color: 'primary.main',
                    },
                    '& .MuiListItemText-root .MuiTypography-root': {
                      color: 'primary.main',
                      fontWeight: 600,
                    },
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open ? 3 : 'auto',
                    justifyContent: 'center',
                  }}
                >
                  {icon}
                </ListItemIcon>
                <ListItemText
                  primary={text}
                  sx={{
                    opacity: open ? 1 : 0,
                    transition: 'opacity 0.2s',
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </DrawerStyled>
    </>
  );
}
