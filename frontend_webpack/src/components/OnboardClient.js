// src/components/OnboardClient.js

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  TextField,
  Button,
  Typography,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Tabs,
  Tab,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Fade,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { DataGrid } from '@mui/x-data-grid';
import AxiosInstance from './common/AxiosInstance';
import { useNavigate } from 'react-router-dom';

const WhiteBox = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  width: '100%',
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[5],
}));

const StyledButton = styled(Button)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.common.white,
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(1.5),
  fontSize: 16,
  fontFamily: theme.typography.fontFamily,
  cursor: 'pointer',
  width: '100%',
  '&:hover': { backgroundColor: theme.palette.primary.dark },
  '&:focus': {
    outline: `2px solid ${theme.palette.common.white}`,
    outlineOffset: '2px',
  },
  transition: 'background-color 0.3s ease, outline 0.3s ease',
}));

function TabPanel({ children, value, index }) {
  return (
    <Fade in={value === index} timeout={300} unmountOnExit>
      <div role="tabpanel" hidden={value !== index}>
        {value === index && <Box mt={2}>{children}</Box>}
      </div>
    </Fade>
  );
}

export default function OnboardClient() {
  const navigate = useNavigate();
  const [tabIndex, setTabIndex] = useState(0);

  // — Onboard New User —
  const [newClientData, setNewClientData] = useState({
    fname: '',
    lname: '',
    phonenumber: '',
    email: '',
    case_id: '',
  });
  const [newClientError, setNewClientError] = useState('');
  const [newClientSuccess, setNewClientSuccess] = useState(false);

  // — Onboard Existing User —
  const [existingUserData, setExistingUserData] = useState({
    phonenumber: '',
    email: '',
  });
  const [existingUserError, setExistingUserError] = useState('');
  const [existingUserExists, setExistingUserExists] = useState(false);
  const [existingUserCaseId, setExistingUserCaseId] = useState('');
  const [onboardExistingSuccess, setOnboardExistingSuccess] = useState(false);
  const [onboardExistingError, setOnboardExistingError] = useState('');

  // — Client List —
  const [loadingList, setLoadingList] = useState(false);
  const [clientsError, setClientsError] = useState('');
  const [casesWithoutClient, setCasesWithoutClient] = useState([]);
  const [clientsWithoutCase, setClientsWithoutCase] = useState([]);
  const [mappedRows, setMappedRows] = useState([]);

  // Handlers — New Client
  const handleNewClientChange = (e) =>
    setNewClientData({ ...newClientData, [e.target.name]: e.target.value });

  const handleOnboardNewClient = async () => {
    const { fname, phonenumber } = newClientData;
    if (!fname || !phonenumber) {
      setNewClientError('Please fill in all required fields.');
      return;
    }
    try {
      const res = await AxiosInstance.post('users/onboard-client/', newClientData);
      if (res.status === 201) {
        setNewClientSuccess(true);
        setNewClientData({ fname: '', lname: '', phonenumber: '', email: '', case_id: '' });
      } else {
        setNewClientError('Failed to onboard client.');
      }
    } catch (err) {
      setNewClientError(err.response?.data?.message || 'Error onboarding client.');
    }
  };

  // Handlers — Existing Client
  const handleExistingUserChange = (e) =>
    setExistingUserData({ ...existingUserData, [e.target.name]: e.target.value });

  const handleCheckExistingUser = async () => {
    const { phonenumber, email } = existingUserData;
    if (!(phonenumber || email)) {
      setExistingUserError('At least phone or email is required.');
      return;
    }
    try {
      const res = await AxiosInstance.post('users/check-existing-user/', existingUserData);
      if (res.status === 200 && res.data.exists) {
        setExistingUserExists(true);
        setExistingUserError('');
      } else {
        setExistingUserError('User does not exist.');
      }
    } catch (err) {
      setExistingUserError(err.response?.data?.message || 'Error checking user validity.');
    }
  };

  const handleOnboardExistingUser = async () => {
    try {
      const payload = {
        ...existingUserData,
        case_id: existingUserCaseId || null,
      };
      const res = await AxiosInstance.post('users/onboard-existing-client/', payload);
      if (res.status === 200) {
        setOnboardExistingSuccess(true);
        setExistingUserData({ phonenumber: '', email: '' });
        setExistingUserCaseId('');
        setExistingUserExists(false);
      } else {
        setOnboardExistingError('Failed to onboard existing user.');
      }
    } catch (err) {
      setOnboardExistingError(err.response?.data?.message || 'Error onboarding existing user.');
    }
  };

  // Dialog closes
  const closeNewSuccess = () => setNewClientSuccess(false);
  const closeExistingSuccess = () => setOnboardExistingSuccess(false);

  // Fetch Client List
  const fetchClientList = async () => {
    setLoadingList(true);
    try {
      const { data } = await AxiosInstance.get(
        'users/filter_with_details/'
      );
      setCasesWithoutClient(data.caseIds_without_client || []);
      setClientsWithoutCase(data.clientIds_without_case || []);
      const rows = Object.entries(data.case_client_map || {})
        .filter(([cid, c]) => cid && c && c.Fname)
        .map(([caseId, c], i) => ({
          id: i,
          caseId,
          clientName: `${c.Fname} ${c.Lname}`,
          email: c.email,
          phone: c.phone_number,
          status: c.status,
        }));
      setMappedRows(rows);
      setClientsError('');
    } catch (err) {
      setClientsError(err.response?.data?.message || 'Failed to load client list.');
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    if (tabIndex === 1) fetchClientList();
  }, [tabIndex]);

  const columns = [
    { field: 'clientName', headerName: 'Client Name', flex: 1 },
    { field: 'email', headerName: 'Email', flex: 1 },
    { field: 'phone', headerName: 'Phone', flex: 1 },
    { field: 'caseId', headerName: 'Case ID', flex: 1 },
    { field: 'status', headerName: 'Status', flex: 1 },
  ];

  const isEmpty =
    !loadingList &&
    !clientsError &&
    casesWithoutClient.length === 0 &&
    clientsWithoutCase.length === 0 &&
    mappedRows.length === 0;

  return (
    <Box mt={4}>
      <WhiteBox>
        <Box display="flex" justifyContent="center">
          <Tabs
            value={tabIndex}
            onChange={(_, v) => setTabIndex(v)}
            indicatorColor="primary"
            textColor="primary"
            centered
          >
            <Tab label="Onboard Client" />
            <Tab label="Client List" />
          </Tabs>
        </Box>

        {/* Tab 0: Onboard */}
        <TabPanel value={tabIndex} index={0}>
          <Grid container spacing={4}>
            {/* New User */}
            <Grid item xs={12} md={6}>
              <Typography variant="h5" align="center" gutterBottom>
                Onboard New User
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <TextField
                  label="First Name"
                  name="fname"
                  value={newClientData.fname}
                  onChange={handleNewClientChange}
                  required
                  fullWidth
                />
                <TextField
                  label="Last Name"
                  name="lname"
                  value={newClientData.lname}
                  onChange={handleNewClientChange}
                  fullWidth
                />
                <TextField
                  label="Phone Number"
                  name="phonenumber"
                  value={newClientData.phonenumber}
                  onChange={handleNewClientChange}
                  required
                  type="tel"
                  fullWidth
                  inputProps={{ maxLength: 10 }}
                />
                <TextField
                  label="Email ID"
                  name="email"
                  value={newClientData.email}
                  onChange={handleNewClientChange}
                  type="email"
                  fullWidth
                />
                <TextField
                  label="Case ID (Optional)"
                  name="case_id"
                  value={newClientData.case_id}
                  onChange={handleNewClientChange}
                  fullWidth
                />
                {newClientError && (
                  <Typography color="error" align="center">
                    {newClientError}
                  </Typography>
                )}
                <StyledButton onClick={handleOnboardNewClient}>
                  Onboard Client
                </StyledButton>
              </Box>
            </Grid>

            {/* Existing User */}
            <Grid item xs={12} md={6}>
              <Typography variant="h5" align="center" gutterBottom>
                Onboard Existing User
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <TextField
                  label="Phone Number"
                  name="phonenumber"
                  value={existingUserData.phonenumber}
                  onChange={handleExistingUserChange}
                  type="tel"
                  fullWidth
                  inputProps={{ maxLength: 10 }}
                />
                <TextField
                  label="Email ID"
                  name="email"
                  value={existingUserData.email}
                  onChange={handleExistingUserChange}
                  type="email"
                  fullWidth
                />
                {existingUserError && (
                  <Typography color="error" align="center">
                    {existingUserError}
                  </Typography>
                )}
                <StyledButton onClick={handleCheckExistingUser}>
                  Check Validity
                </StyledButton>
              </Box>
            </Grid>
          </Grid>

          {/* Success & case-id dialogs */}
          <Dialog open={newClientSuccess} onClose={closeNewSuccess}>
            <DialogTitle>Client Onboarded</DialogTitle>
            <DialogContent>
              <DialogContentText>
                The new client has been onboarded successfully.
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={closeNewSuccess}>Close</Button>
            </DialogActions>
          </Dialog>

          <Dialog
            open={existingUserExists}
            onClose={() => setExistingUserExists(false)}
          >
            <DialogTitle>Add Case ID (Optional)</DialogTitle>
            <DialogContent>
              <DialogContentText>
                The user exists. You can add an optional Case ID.
              </DialogContentText>
              <TextField
                autoFocus
                margin="dense"
                label="Case ID"
                fullWidth
                variant="standard"
                value={existingUserCaseId}
                onChange={(e) => setExistingUserCaseId(e.target.value)}
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setExistingUserExists(false)}>
                Cancel
              </Button>
              <Button onClick={handleOnboardExistingUser}>Onboard</Button>
            </DialogActions>
          </Dialog>

          <Dialog open={onboardExistingSuccess} onClose={closeExistingSuccess}>
            <DialogTitle>User Onboarded</DialogTitle>
            <DialogContent>
              <DialogContentText>
                The existing user has been successfully onboarded.
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={closeExistingSuccess}>Close</Button>
            </DialogActions>
          </Dialog>

          <Dialog
            open={Boolean(onboardExistingError)}
            onClose={() => setOnboardExistingError('')}
          >
            <DialogTitle>Error</DialogTitle>
            <DialogContent>
              <DialogContentText>
                {onboardExistingError}
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOnboardExistingError('')}>
                Close
              </Button>
            </DialogActions>
          </Dialog>
        </TabPanel>

        {/* Tab 1: Client List */}
        <TabPanel value={tabIndex} index={1}>
          {loadingList ? (
            <Box textAlign="center" mt={4}>
              <CircularProgress />
            </Box>
          ) : clientsError ? (
            <Typography color="error">{clientsError}</Typography>
          ) : isEmpty ? (
            <Typography>No clients or cases available.</Typography>
          ) : (
            <>
              {casesWithoutClient.length > 0 && (
                <Box mb={2}>
                  <Typography variant="subtitle1">
                    Cases without clients:
                  </Typography>
                  <List dense>
                    {casesWithoutClient.map((cid) => (
                      <ListItem key={cid}>
                        <ListItemText primary={cid} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {clientsWithoutCase.length > 0 && (
                <Box mb={2}>
                  <Typography variant="subtitle1">
                    Clients without cases:
                  </Typography>
                  <List dense>
                    {clientsWithoutCase.map((c, i) => (
                      <ListItem key={i}>
                        <ListItemText
                          primary={`${c.Fname} ${c.Lname}`}
                          secondary={c.phone_number}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {mappedRows.length > 0 && (
                <div style={{ height: 400, width: '100%' }}>
                  <DataGrid rows={mappedRows} columns={columns} pageSize={5} />
                </div>
              )}
            </>
          )}
        </TabPanel>
      </WhiteBox>
    </Box>
  );
}
