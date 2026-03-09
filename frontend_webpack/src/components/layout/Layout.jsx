import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Box, CssBaseline, Toolbar } from '@mui/material';
import Navbar from './Navbar';   //  ⬅️  import the shared width

const Layout = () => {
  const [open, setOpen] = useState(true);

  const handleDrawerToggle = () => setOpen((prev) => !prev);

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />

      {/* Nav rail + top bar */}
      <Navbar open={open} handleDrawerToggle={handleDrawerToggle} />

      {/* Main workspace */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
        }}
      >
        <Toolbar />   {/* keeps content below the AppBar */}
        <Outlet />    {/* nested routes render here */}
      </Box>
    </Box>
  );
};

export default Layout;
