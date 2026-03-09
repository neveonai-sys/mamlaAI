import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Grid,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  TextField,
  Button,
  InputLabel,
  Select,
  MenuItem,
  FormLabel,
  FormControl,
  FormHelperText,
  Checkbox,
  IconButton,
  FormControlLabel,
  InputAdornment,
  Autocomplete,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import Cancel from '@mui/icons-material/Cancel';
import CancelIcon from '@mui/icons-material/Cancel';
import CheckCircle from '@mui/icons-material/CheckCircle';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import { styled } from '@mui/material/styles';
import AxiosInstance from '../common/AxiosInstance';
import LoadingOverlay from '../common/LoadingOverlay';

/* ---------- shared shells ---------- */
const FullHeightBox = styled(Box)({
  minHeight: '100vh',
  width: '100%',
  display: 'flex'
});

const Banner = styled(Box)(({ theme }) => ({
  backgroundColor: '#062448',
  color: theme.palette.common.white,
  padding: theme.spacing(8),
  [theme.breakpoints.down('md')]: {
    display: 'none'
  }
}));

const Highlight = styled('span')(({ theme }) => ({
  color: theme.palette.warning.main,
  fontWeight: 700
}));

const FormWrapper = styled(Paper)(({ theme }) => ({
  margin: 'auto',
  padding: theme.spacing(5),
  maxWidth: 620,
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

// Styled Components
const BackgroundBox = styled(Box)(({ theme }) => ({
  width: '100vw',
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'linear-gradient(135deg, #0D47A1, #1565C0)',
  padding: theme.spacing(2),
}));

const FormContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  width: '100%',
  maxWidth: 650,
  borderRadius: theme.shape.borderRadius,
  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
  backgroundColor: theme.palette.background.paper,
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(3),
    maxWidth: '90%',
  },
}));

const SmallTextField = styled(TextField)(() => ({
  '& .MuiInputBase-root': {
    fontSize: '0.875rem',
  },
  '& .MuiFormLabel-root': {
    fontSize: '0.875rem',
  },
}));

const GradientButton = styled(Button)(({ theme }) => ({
  background: 'linear-gradient(to right, #4e54c8, #8f94fb)',
  color: '#fff',
  padding: theme.spacing(1.2),
  width: '100%',
  borderRadius: theme.shape.borderRadius,
  textTransform: 'none',
  fontSize: '0.9rem',
  '&:hover': {
    background: 'linear-gradient(to right, #4e54c8, #8f94fb)',
    opacity: 0.9
  }
}));

const StyledLink = styled(Link)(({ theme }) => ({
  textDecoration: 'none',
  color: theme.palette.primary.main,
  '&:hover': {
    textDecoration: 'underline',
  },
}));

// Helper for checking password rules
const getPasswordChecks = (pwd) => ({
  length: pwd.length >= 6,
  uppercase: /[A-Z]/.test(pwd),
  lowercase: /[a-z]/.test(pwd),
  digit: /\d/.test(pwd),
  special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(pwd)
});

const Signup = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const query = new URLSearchParams(location.search);
  const token = query.get('token');

  // Basic fields
  const [mobile, setMobile] = useState('');
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [userType, setUserType] = useState('');
  const [barcodeId, setBarcodeId] = useState('');
  const [caseIds, setCaseIds] = useState('');

  // Paralegal fields
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [courtOptions, setCourtOptions] = useState([]);
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedCourts, setSelectedCourts] = useState([]);

  // Password fields
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);

  // Existence checks
  const [phoneExists, setPhoneExists] = useState(false);
  const [emailExists, setEmailExists] = useState(false);

  // Global error handling
  const [errorOpen, setErrorOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [confirmPasswordError, setConfirmPasswordError] = useState('');

  const FORM_COLS = 7; 

  // Prefilled (token-based) flow
  const [clientData, setClientData] = useState({
    fname: '',
    lname: '',
    phonenumber: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [isPrefilled, setIsPrefilled] = useState(false);

  // Checkboxes
  const [whatsappOptIn, setWhatsappOptIn] = useState(false);
  const [tncChecked, setTncChecked] = useState(false);

  // Loading indicator
  const [loading, setLoading] = useState(false);

  // New state to hold field-specific errors
  const [formErrors, setFormErrors] = useState({});

  // Debounce refs for phone/email existence check
  const phoneDebounceRef = useRef(null);
  const emailDebounceRef = useRef(null);

  // Basic validations
  const isValidPhoneNumber = (number) => /^\d{10}$/.test(number);
  const isValidEmail = (em) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em);

  // Prefilled data fetch
  useEffect(() => {
    if (token) {
      const fetchPrefilledData = async () => {
        try {
          const response = await AxiosInstance.post('users/get-prefilled-data/', { token });
          if (response.status === 200) {
            setClientData({
              fname: response.data.fname || '',
              lname: response.data.lname || '',
              phonenumber: response.data.phonenumber || '',
              email: response.data.email || '',
              password: '',
              confirmPassword: '',
            });
            setIsPrefilled(true);
          } else {
            setErrorMessage('Invalid or expired token.');
            setErrorOpen(true);
          }
        } catch (error) {
          console.error('Error fetching prefilled data:', error);
          setErrorMessage('Failed to fetch prefilled data.');
          setErrorOpen(true);
        }
      };
      fetchPrefilledData();
    }
  }, [token]);

  // Fetch states for Paralegal
  useEffect(() => {
    if (userType === 'Paralegal') {
      const fetchStates = async () => {
        try {
          const response = await AxiosInstance.get('users/get-states/');
          if (response.status === 200) {
            setStates(response.data.states);
          }
        } catch (error) {
          console.error('Error fetching states:', error);
        }
      };
      fetchStates();
    } else {
      setSelectedState('');
      setSelectedDistrict('');
      setSelectedCourts([]);
      setStates([]);
      setDistricts([]);
      setCourtOptions([]);
    }
  }, [userType]);

  // Input change handlers
  const handleClientChange = (e) => {
    let { name, value } = e.target;
    if (name === 'phonenumber') {
      value = value.replace(/\D/g, '');
    }
    if (name === 'fname' || name === 'lname') {
      value = value.replace(/[^a-zA-Z\s]/g, '');
    }
    setClientData({ ...clientData, [name]: value });
  };

  const handleMobileChange = (e) => {
    let val = e.target.value.replace(/\D/g, '');
    setMobile(val);
    if (formErrors.mobile) {
      setFormErrors({ ...formErrors, mobile: '' });
    }
  };

  const handleFirstNameChange = (e) => {
    let val = e.target.value.replace(/[^a-zA-Z\s]/g, '');
    setFirstName(val);
    if (formErrors.firstName) {
      setFormErrors({ ...formErrors, firstName: '' });
    }
  };

  const handleLastNameChange = (e) => {
    let val = e.target.value.replace(/[^a-zA-Z\s]/g, '');
    setLastName(val);
  };

  const handleEmailChange = (e) => {
    setEmail(e.target.value);
    if (formErrors.email) {
      setFormErrors({ ...formErrors, email: '' });
    }
  };

  const handleStateChange = async (e) => {
    const st = e.target.value;
    setSelectedState(st);
    setSelectedDistrict('');
    setSelectedCourts([]);
    if (st) {
      try {
        const response = await AxiosInstance.get(`users/get-districts/?state=${st}`);
        if (response.status === 200) {
          setDistricts(response.data.districts);
        }
      } catch (error) {
        console.error('Error fetching districts:', error);
      }
    } else {
      setDistricts([]);
    }
  };

  const handleDistrictChange = async (e) => {
    const dist = e.target.value;
    setSelectedDistrict(dist);
    setSelectedCourts([]);
    if (dist) {
      try {
        const response = await AxiosInstance.get(`users/get-courts/?state=${selectedState}&district=${dist}`);
        if (response.status === 200) {
          setCourtOptions(response.data.courts);
        }
      } catch (error) {
        console.error('Error fetching courts:', error);
      }
    } else {
      setCourtOptions([]);
    }
  };

  const handleCourtSelection = (event, values) => {
    if (values.length > 3) {
      alert('You can select a maximum of 3 courts.');
      return;
    }
    setSelectedCourts(values);
  };

  // Debounce phone and email existence checks
  useEffect(() => {
    if (phoneDebounceRef.current) clearTimeout(phoneDebounceRef.current);
    if (mobile.length === 10) {
      phoneDebounceRef.current = setTimeout(() => {
        checkPhoneAPI(mobile);
      }, 500);
    }
  }, [mobile]);

  const checkPhoneAPI = async (phoneValue) => {
    if (!isValidPhoneNumber(phoneValue)) return;
    try {
      setLoading(true);
      const response = await AxiosInstance.post('users/check-existing-user/', {
        phonenumber: phoneValue,
      });
      setLoading(false);
      setPhoneExists(response.data.exists);
    } catch (error) {
      setLoading(false);
      console.error('Error checking phone existence', error);
      setPhoneExists(false);
    }
  };

  useEffect(() => {
    if (emailDebounceRef.current) clearTimeout(emailDebounceRef.current);
    if (isValidEmail(email)) {
      emailDebounceRef.current = setTimeout(() => {
        checkEmailAPI(email);
      }, 500);
    }
  }, [email]);

  const checkEmailAPI = async (emailValue) => {
    try {
      setLoading(true);
      const response = await AxiosInstance.post('users/check-existing-user/', {
        email: emailValue,
      });
      setLoading(false);
      setEmailExists(response.data.exists);
    } catch (error) {
      setLoading(false);
      console.error('Error checking email existence', error);
      setEmailExists(false);
    }
  };

  // Submit handlers
  const handleStandardSubmit = async (event) => {
    event.preventDefault();
    setFormErrors({});
    let errors = {};

    if (!firstName) errors.firstName = "First name is required.";
    if (!email) errors.email = "Email is required.";
    if (!mobile) errors.mobile = "Phone number is required.";
    if (!userType) errors.userType = "User type is required.";
    if (!password) errors.password = "Password is required.";
    if (!confirmPassword) errors.confirmPassword = "Please confirm your password.";
    if (password && confirmPassword && password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match.";
    }
    if (userType === 'Lawyer' && !barcodeId) {
      errors.barcodeId = "Barcode ID is required for Lawyer.";
    }
    if (userType === 'Paralegal') {
      if (!selectedState) errors.selectedState = "State is required.";
      if (!selectedDistrict) errors.selectedDistrict = "District is required.";
      if (selectedCourts.length === 0) errors.selectedCourts = "At least one court must be selected.";
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      setErrorMessage("Please fill in all required fields.");
      setErrorOpen(true);
      return;
    }

    const checks = getPasswordChecks(password);
    const allPassRules = Object.values(checks).every(Boolean);
    if (!allPassRules) {
      setErrorMessage('Password does not meet all the requirements.');
      setErrorOpen(true);
      return;
    }

    if (phoneExists || emailExists) {
      setErrorMessage('Phone or Email is already in use. Please change them or login.');
      setErrorOpen(true);
      return;
    }

    const payload = {
      phonenumber: mobile,
      email: email,
      firstname: firstName,
      lastname: lastName,
      user_type: userType,
      password: password,
      barcodeid: userType === 'Lawyer' ? barcodeId : '',
      case_ids:
        (userType === 'Lawyer' || userType === 'Client') && caseIds
          ? caseIds.split(',')
          : [],
      state: userType === 'Paralegal' ? selectedState : '',
      district: userType === 'Paralegal' ? selectedDistrict : '',
      courts: userType === 'Paralegal' ? selectedCourts : [],
      whatsappOptIn,
      agreedTnC: tncChecked,
    };
    const url = 'users/onboard/';

    try {
      setLoading(true);
      await AxiosInstance.post(url, payload);
      setLoading(false);
      alert('Signup success! Check your email for verification, then please log in.');
      navigate('/login');
    } catch (error) {
      setLoading(false);
      console.error('Signup error:', error);
      setErrorMessage(error.message || 'Signup failed.');
      setErrorOpen(true);
    }
  };

  const handlePrefilledSubmit = async (event) => {
    event.preventDefault();
    setFormErrors({});
    let errors = {};
    const { fname, lname, phonenumber, email, password, confirmPassword } = clientData;
    if (!fname) errors.fname = "First name is required.";
    if (!phonenumber) errors.phonenumber = "Phone number is required.";
    if (!email) errors.email = "Email is required.";
    if (!password) errors.password = "Password is required.";
    if (!confirmPassword) errors.confirmPassword = "Please confirm your password.";
    if (password && confirmPassword && password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match.";
    }
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      setErrorMessage("Please fill in all required fields.");
      setErrorOpen(true);
      return;
    }
    const checks = getPasswordChecks(password);
    const allPassRules = Object.values(checks).every(Boolean);
    if (!allPassRules) {
      setErrorMessage('Password does not meet all the requirements.');
      setErrorOpen(true);
      return;
    }
    try {
      setLoading(true);
      const payload = {
        token,
        phonenumber,
        fname,
        lname,
        email,
        password,
        confirmPassword,
        whatsappOptIn,
        agreedTnC: tncChecked,
      };

      const response = await AxiosInstance.post('users/signup-user/', payload);
      setLoading(false);

      if (response.status === 201) {
        alert(
          "You've received a link in your email and WhatsApp to verify. Please navigate to the URL to activate your profile."
        );
        navigate('/login');
      } else {
        setErrorMessage('Signup failed');
        setErrorOpen(true);
      }
    } catch (error) {
      setLoading(false);
      console.error('Error submitting prefilled form', error);
      setErrorMessage(error.response?.data?.message || 'Failed to submit form.');
      setErrorOpen(true);
    }
  };

  const handleSubmit = (event) => {
    if (isPrefilled) {
      handlePrefilledSubmit(event);
    } else {
      handleStandardSubmit(event);
    }
  };

  const handleErrorClose = () => {
    setErrorOpen(false);
  };

  const handleTogglePasswordVisibility = () => {
    setShowPassword((prev) => !prev);
  };

  const renderValidationIcon = (valid) => {
    if (valid === null) return null;
    return valid ? (
      <CheckCircle sx={{ color: 'green', ml: 1 }} />
    ) : (
      <Cancel sx={{ color: 'red', ml: 1 }} />
    );
  };

  const phoneValidStatus = () => {
    if (!mobile) return null;
    return isValidPhoneNumber(mobile) && !phoneExists;
  };
  const emailValidStatus = () => {
    if (!email) return null;
    return isValidEmail(email) && !emailExists;
  };
  const firstNameValidStatus = () => {
    if (!firstName) return null;
    return /^[a-zA-Z\s]+$/.test(firstName);
  };
  const lastNameValidStatus = () => {
    if (!lastName) return null;
    return /^[a-zA-Z\s]+$/.test(lastName);
  };

  const renderPasswordRules = (pwd) => {
    const checks = getPasswordChecks(pwd);
    const ruleItems = [
      { label: 'At least 6 characters', valid: checks.length },
      { label: 'Uppercase letter (A-Z)', valid: checks.uppercase },
      { label: 'Lowercase letter (a-z)', valid: checks.lowercase },
      { label: 'Digit (0-9)', valid: checks.digit },
      { label: 'Special character', valid: checks.special }
    ];
    return (
      <Box mt={1}>
        {ruleItems.map((rule, idx) => (
          <Box
            key={idx}
            display="flex"
            alignItems="center"
            color={rule.valid ? 'green' : 'red'}
            fontSize="0.8rem"
          >
            {rule.valid ? <CheckCircle fontSize="small" /> : <Cancel fontSize="small" />}
            <Typography variant="body2" ml={0.5} fontSize="0.8rem">
              {rule.label}
            </Typography>
          </Box>
        ))}
      </Box>
    );
  };

  const HeadingBlock = () => (
    <Box textAlign="center" mb={3}>
      <Typography variant="h5" align="center" gutterBottom>
        <Link to="/">Mamla.Ai</Link>
      </Typography>
      <FormControl component="fieldset" fullWidth>
        <FormLabel component="legend" sx={{ textAlign: 'center' }}>
          Registration
        </FormLabel>
      </FormControl>
    </Box>
  );

  // Render prefilled form
  const renderPrefilledForm = () => (
    <>
      <HeadingBlock />
      <Box component="form" onSubmit={handleSubmit}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <SmallTextField
              size="small"
              label="First Name"
              name="fname"
              value={clientData.fname}
              onChange={handleClientChange}
              fullWidth
              required
              disabled={!!clientData.fname}
              error={Boolean(formErrors.fname)}
              helperText={formErrors.fname}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <SmallTextField
              size="small"
              label="Last Name"
              name="lname"
              value={clientData.lname}
              onChange={handleClientChange}
              fullWidth
              required
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <SmallTextField
              size="small"
              label="WhatsApp Number"
              name="phonenumber"
              value={clientData.phonenumber}
              onChange={handleClientChange}
              fullWidth
              required
              type="tel"
              inputProps={{ maxLength: 10 }}
              disabled={!!clientData.phonenumber}
              error={Boolean(formErrors.phonenumber)}
              helperText={formErrors.phonenumber}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <SmallTextField
              size="small"
              label="Email"
              name="email"
              type="email"
              value={clientData.email}
              onChange={handleClientChange}
              fullWidth
              required
              disabled={!!clientData.email}
              error={Boolean(formErrors.email)}
              helperText={formErrors.email}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <SmallTextField
              size="small"
              label="Password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              value={clientData.password}
              onFocus={() => setPasswordFocused(true)}
              onBlur={() => setPasswordFocused(false)}
              onChange={(e) => setClientData({ ...clientData, password: e.target.value })}
              fullWidth
              required
              error={Boolean(formErrors.password)}
              helperText={formErrors.password}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={handleTogglePasswordVisibility}
                      edge="end"
                      size="small"
                    >
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            {passwordFocused && renderPasswordRules(clientData.password)}
          </Grid>
          <Grid item xs={12} sm={6}>
            <SmallTextField
              size="small"
              label="Confirm Password"
              name="confirmPassword"
              type={showPassword ? 'text' : 'password'}
              value={clientData.confirmPassword}
              onChange={(e) => setClientData({ ...clientData, confirmPassword: e.target.value })}
              fullWidth
              required
              error={Boolean(formErrors.confirmPassword)}
              helperText={formErrors.confirmPassword}
            />
          </Grid>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={whatsappOptIn}
                  onChange={(e) => setWhatsappOptIn(e.target.checked)}
                />
              }
              label="I agree to receive WhatsApp communication."
            />
          </Grid>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={tncChecked}
                  onChange={(e) => setTncChecked(e.target.checked)}
                />
              }
              label={
                <>
                  I agree to the{' '}
                  <span style={{ textDecoration: 'underline', cursor: 'pointer' }}>
                    Terms and Conditions
                  </span>
                </>
              }
            />
          </Grid>
          <Grid item xs={12}>
            <GradientButton type="submit">
              Register
            </GradientButton>
          </Grid>
          <Grid item xs={12} textAlign="center">
            <Typography variant="body2" fontSize="0.9rem">
              Already registered?{' '}
              <StyledLink to="/login">Please login!</StyledLink>
            </Typography>
          </Grid>
        </Grid>
      </Box>
    </>
  );

  // Render standard form
  const renderStandardForm = () => (
    <>
      <HeadingBlock />
      <Box component="form" onSubmit={handleSubmit}>
        <Grid container spacing={2}>
          {/* Full Name */}
          <Grid item xs={12} sm={6}>
            <Box display="flex" alignItems="center">
              <SmallTextField
                size="small"
                label="First Name"
                value={firstName}
                onChange={handleFirstNameChange}
                fullWidth
                required
                error={Boolean(formErrors.firstName)}
                helperText={formErrors.firstName}
              />
              {renderValidationIcon(firstNameValidStatus())}
            </Box>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Box display="flex" alignItems="center">
              <SmallTextField
                size="small"
                label="Last Name"
                value={lastName}
                onChange={handleLastNameChange}
                fullWidth
              />
              {renderValidationIcon(lastNameValidStatus())}
            </Box>
          </Grid>
          {/* Email / Phone */}
          <Grid item xs={12} sm={6}>
            <Box display="flex" alignItems="center" width="100%">
              <SmallTextField
                size="small"
                label="Email"
                type="email"
                value={email}
                onChange={handleEmailChange}
                fullWidth
                required
                error={Boolean(formErrors.email) || emailExists}
                helperText={formErrors.email}
              />
              {renderValidationIcon(emailValidStatus())}
            </Box>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Box display="flex" alignItems="center" width="100%">
              <SmallTextField
                size="small"
                label="Phone Number"
                value={mobile}
                onChange={handleMobileChange}
                type="tel"
                inputProps={{ maxLength: 10 }}
                fullWidth
                required
                error={Boolean(formErrors.mobile) || phoneExists}
                helperText={formErrors.mobile}
              />
              {renderValidationIcon(phoneValidStatus())}
            </Box>
          </Grid>
          {/* User Type */}
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth required size="small" error={Boolean(formErrors.userType)}>
              <InputLabel id="user-type-label" sx={{ fontSize: '0.875rem' }}>
                User Type
              </InputLabel>
              <Select
                labelId="user-type-label"
                value={userType}
                onChange={(e) => {
                  setUserType(e.target.value);
                  setBarcodeId('');
                  setCaseIds('');
                  setSelectedState('');
                  setSelectedDistrict('');
                  setSelectedCourts([]);
                  if (formErrors.userType) {
                    setFormErrors({ ...formErrors, userType: '' });
                  }
                }}
                label="User Type"
                sx={{ fontSize: '0.875rem' }}
              >
                <MenuItem value="Lawyer" sx={{ fontSize: '0.875rem' }}>
                  Lawyer
                </MenuItem>
                <MenuItem value="Client" sx={{ fontSize: '0.875rem' }}>
                  Client
                </MenuItem>
              </Select>
              {formErrors.userType && (
                <FormHelperText>{formErrors.userType}</FormHelperText>
              )}
            </FormControl>
          </Grid>
          {/* Lawyer Fields */}
          {userType === 'Lawyer' && (
            <Grid item xs={12}>
              <FormHelperText sx={{ fontSize: '0.75rem' }}>
                Please provide your registration number (Barcode ID) for authorization.
              </FormHelperText>
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12} sm={6}>
                  <SmallTextField
                    size="small"
                    label="Barcode ID"
                    value={barcodeId}
                    onChange={(e) => {
                      setBarcodeId(e.target.value);
                      if (formErrors.barcodeId) {
                        setFormErrors({ ...formErrors, barcodeId: '' });
                      }
                    }}
                    fullWidth
                    error={Boolean(formErrors.barcodeId)}
                    helperText={formErrors.barcodeId}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <SmallTextField
                    size="small"
                    label="Case IDs (comma-separated)"
                    value={caseIds}
                    onChange={(e) => setCaseIds(e.target.value)}
                    fullWidth
                  />
                </Grid>
              </Grid>
            </Grid>
          )}
          {/* Client Fields */}
          {userType === 'Client' && (
            <Grid item xs={12}>
              <SmallTextField
                size="small"
                label="Case IDs (comma-separated)"
                value={caseIds}
                onChange={(e) => setCaseIds(e.target.value)}
                fullWidth
              />
            </Grid>
          )}
          {/* Paralegal Fields */}
          {userType === 'Paralegal' && (
            <Grid item xs={12}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth required size="small" error={Boolean(formErrors.selectedState)}>
                    <InputLabel id="state-label" sx={{ fontSize: '0.875rem' }}>
                      State
                    </InputLabel>
                    <Select
                      labelId="state-label"
                      value={selectedState}
                      onChange={handleStateChange}
                      label="State"
                      sx={{ fontSize: '0.875rem' }}
                    >
                      {states.map((st) => (
                        <MenuItem key={st} value={st} sx={{ fontSize: '0.875rem' }}>
                          {st}
                        </MenuItem>
                      ))}
                    </Select>
                    {formErrors.selectedState && (
                      <FormHelperText>{formErrors.selectedState}</FormHelperText>
                    )}
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  {selectedState && (
                    <FormControl fullWidth required size="small" error={Boolean(formErrors.selectedDistrict)}>
                      <InputLabel id="district-label" sx={{ fontSize: '0.875rem' }}>
                        District
                      </InputLabel>
                      <Select
                        labelId="district-label"
                        value={selectedDistrict}
                        onChange={handleDistrictChange}
                        label="District"
                        sx={{ fontSize: '0.875rem' }}
                      >
                        {districts.map((dist) => (
                          <MenuItem key={dist} value={dist} sx={{ fontSize: '0.875rem' }}>
                            {dist}
                          </MenuItem>
                        ))}
                      </Select>
                      {formErrors.selectedDistrict && (
                        <FormHelperText>{formErrors.selectedDistrict}</FormHelperText>
                      )}
                    </FormControl>
                  )}
                </Grid>
                {selectedDistrict && (
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" sx={{ mt: 1 }}>
                      Select Courts (at least 1, max 3):
                    </Typography>
                    <Autocomplete
                      multiple
                      options={courtOptions}
                      getOptionLabel={(option) => option}
                      value={selectedCourts}
                      onChange={handleCourtSelection}
                      filterSelectedOptions
                      renderInput={(params) => (
                        <SmallTextField
                          {...params}
                          variant="outlined"
                          label="Courts"
                          placeholder="Select courts"
                        />
                      )}
                    />
                    {formErrors.selectedCourts && (
                      <FormHelperText sx={{ fontSize: '0.75rem' }}>
                        {formErrors.selectedCourts}
                      </FormHelperText>
                    )}
                  </Grid>
                )}
              </Grid>
            </Grid>
          )}
          {/* Password Fields */}
          <Grid item xs={12} sm={6}>
            <SmallTextField
              size="small"
              label="Password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (formErrors.password) {
                  setFormErrors({ ...formErrors, password: '' });
                }
              }}
              onFocus={() => setPasswordFocused(true)}
              onBlur={() => setPasswordFocused(false)}
              type={showPassword ? 'text' : 'password'}
              fullWidth
              required
              error={Boolean(formErrors.password)}
              helperText={formErrors.password}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={handleTogglePasswordVisibility}
                      edge="end"
                      size="small"
                    >
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            {passwordFocused && renderPasswordRules(password)}
          </Grid>
          <Grid item xs={12} sm={6}>
            <SmallTextField
              size="small"
              label="Confirm Password"
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                if (formErrors.confirmPassword) {
                  setFormErrors({ ...formErrors, confirmPassword: '' });
                }
              }}
              fullWidth
              required
              error={Boolean(formErrors.confirmPassword)}
              helperText={formErrors.confirmPassword}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={handleTogglePasswordVisibility}
                      edge="end"
                      size="small"
                    >
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          {/* Checkboxes */}
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={whatsappOptIn}
                  onChange={(e) => setWhatsappOptIn(e.target.checked)}
                />
              }
              label="I agree to receive WhatsApp communication."
            />
          </Grid>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={tncChecked}
                  onChange={(e) => setTncChecked(e.target.checked)}
                />
              }
              label={
                <>
                  I agree to the{' '}
                  <span style={{ textDecoration: 'underline', cursor: 'pointer' }}>
                    Terms and Conditions
                  </span>
                </>
              }
            />
          </Grid>
          <Grid item xs={12}>
            <GradientButton type="submit">
              Register
            </GradientButton>
          </Grid>
          <Grid item xs={12} textAlign="center">
            <Typography variant="body2" fontSize="0.9rem">
              Already registered?{' '}
              <StyledLink to="/login">Please login!</StyledLink>
            </Typography>
          </Grid>
        </Grid>
      </Box>
    </>
  );

  return (
    <FullHeightBox>
      {/* LEFT BANNER  */}
      <Banner flex={1}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
          <Highlight>Intelligent</Highlight> Legal Management
        </Typography>
        <Typography variant="body1" sx={{ mb: 4, maxWidth: 360 }}>
          On‑board to manage cases, clients &amp; court schedules—all in one place.
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

      {/* RIGHT FORM PANEL */}
      <Grid
        item
        xs={12}
        md={FORM_COLS}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          px: { xs: 2, md: 6 },
          py: { xs: 4, md: 0 }
        }}
      >
        <FormWrapper>
          {/* ------------ INSERT THE WHOLE FORM UI YOU ALREADY HAVE ------------- */}
          {isPrefilled ? renderPrefilledForm() : renderStandardForm()}

          {/* your existing dialogs & overlays   */}
          <LoadingOverlay
            open={loading}
            message="Please wait, processing your request..."
          />

          <Dialog open={errorOpen} onClose={handleErrorClose}>
            <DialogTitle>Error</DialogTitle>
            <DialogContent>
              <DialogContentText>{errorMessage}</DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={handleErrorClose}>Close</Button>
            </DialogActions>
          </Dialog>
        </FormWrapper>
      </Grid>
    </FullHeightBox>
  );
};

export default Signup;
