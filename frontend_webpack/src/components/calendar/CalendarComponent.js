import React, { useState, useEffect } from 'react';
import {
Box,
Button,
TextField,
FormControl,
Grid,
InputLabel,
Select,
MenuItem,
Dialog,
DialogActions,
DialogContent,
Typography,
DialogTitle,
Snackbar,
Checkbox,
FormControlLabel,
IconButton,
Alert
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { useSelector } from 'react-redux';
import AxiosInstance from '../common/AxiosInstance';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import CloseIcon from '@mui/icons-material/Close';
import LazyDataGrid from '../common/LazyDataGrid';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import FormatListBulletedIcon from '@mui/icons-material/FormatListBulleted';
// Styled Components using the global theme
const BackgroundBox = styled(Box)(({ theme }) => ({
padding: theme.spacing(2),
backgroundColor: theme.palette.background.default, // Using global background default
minHeight: '100vh'
}));
const StyledButton = styled(Button)(({ theme }) => ({
backgroundColor: theme.palette.primary.main, // Using primary from theme
color: theme.palette.common.white,
'&:hover': {
backgroundColor: theme.palette.primary.dark
}
}));
const FilterBox = styled(Box)(({ theme }) => ({
display: 'flex',
gap: theme.spacing(2),
flexWrap: 'wrap',
alignItems: 'center'
}));
const DialogTitleStyled = styled(DialogTitle)(({ theme }) => ({
backgroundColor: theme.palette.primary.main,
color: theme.palette.common.white
}));
const DialogContentStyled = styled(DialogContent)(({ theme }) => ({
padding: theme.spacing(3)
}));
const DialogActionsStyled = styled(DialogActions)(({ theme }) => ({
padding: theme.spacing(2)
}));
const CalendarContainer = styled(Box)(({ theme }) => ({
padding: theme.spacing(3),
backgroundColor: theme.palette.background.paper,
borderRadius: theme.shape.borderRadius,
boxShadow: theme.shadows[2],
margin: theme.spacing(3),
fontFamily: 'Roboto, sans-serif'
}));
const Calendar = () => {
const { firstname, lastname, email, user_type } = useSelector((state) => state.user);
const [view, setView] = useState('calendar');
const readOnly = user_type === 'Client';
const [events, setEvents] = useState([]);
const [filteredEvents, setFilteredEvents] = useState([]);
const [filters, setFilters] = useState({ eventType: 'All' });
const [open, setOpen] = useState(false);
const [isEditing, setIsEditing] = useState(false);
const [errorMessage, setErrorMessage] = useState('');
const [successMessage, setSuccessMessage] = useState(false);
const [eventData, setEventData] = useState({
id: null,
title: '',
description: '',
startDate: '',
endDate: '',
startTime: '',
endTime: '',
partyBEmail: '',
meetingtype: '',
caseId: '',
courtName: '',
courtNumber: '',
clientName: '',
judgeName: '',
taskType: 'Personal',
eventType: '',
sendReminder: 'None',
allDay: false,
occurrence: 'only once'
});
const [initialEventData, setInitialEventData] = useState(null);
// Determine current month range
const today = new Date();
const year = today.getFullYear();
const month = today.getMonth();
const firstDayOfMonth = new Date(year, month, 1);
const lastDayOfMonth = new Date(year, month + 1, 0);
const [currentDateRange, setCurrentDateRange] = useState({
start: firstDayOfMonth.toISOString().split('T')[0],
end: lastDayOfMonth.toISOString().split('T')[0],
});
// columns for list view
const columns = [
 { field: 'title', headerName: 'Title', flex: 1 },
 { field: 'start', headerName: 'Start', flex: 1 },
 { field: 'end', headerName: 'End', flex: 1 },
 { field: 'eventType', headerName: 'Type', flex: 1 },
 { field: 'partyBEmail', headerName: 'Party B Email', flex: 1 },
// add more as needed…
];
// When the date range changes, fetch events
useEffect(() => {
if (currentDateRange.start && currentDateRange.end) {
fetchEvents(currentDateRange.start, currentDateRange.end);
}
}, [currentDateRange]);
useEffect(() => {
applyFilters();
}, [filters, events]);
const applyFilters = () => {
const newFilteredEvents = events.filter((ev) => {
return filters.eventType === 'All' || ev.extendedProps.eventType === filters.eventType;
});
setFilteredEvents(newFilteredEvents);
};
const handleFilterChange = (filterName, value) => {
setFilters((prev) => ({ ...prev, [filterName]: value }));
};
const clearFilters = () => {
setFilters({ eventType: 'All' });
};
// Fetch events from the backend
const fetchEvents = (startDate, endDate) => {
const calendar_start = startDate || currentDateRange.start;
const calendar_end = endDate || currentDateRange.end;
AxiosInstance.get(`calendar/get-all-events?start_date=${calendar_start}&end_date=${calendar_end}`)
.then((response) => {
const meetings = response.data.events.meetings;
const fetchedEvents = [];
for (const key in meetings) {
if (Object.hasOwn(meetings, key)) {
const event = meetings[key];
const { title, start, end, allDay, eventType, description, ...rest } = event;
let backgroundColor = '#6a11cb';
const normType = (eventType || '').toLowerCase().trim();
if (normType === 'case date') backgroundColor = '#ffb74d';
else if (normType === 'client appointment') backgroundColor = '#4db6ac';
else if (normType === 'court officer appointment') backgroundColor = '#9575cd';
fetchedEvents.push({
id: key,
title,
start,
end,
allDay,
backgroundColor,
borderColor: backgroundColor,
textColor: '#fff',
extendedProps: { eventType, description: description || '', ...rest }
});
}
}
setEvents(fetchedEvents);
})
.catch((error) => {
console.error('Error fetching events:', error);
setErrorMessage('Error fetching events.');
});
};
const handleDatesSet = (dateInfo) => {
const startDate = dateInfo.view.currentStart.toISOString().split('T')[0];
const endDateObj = new Date(dateInfo.view.currentEnd);
endDateObj.setDate(endDateObj.getDate() + 1);
const endDate = endDateObj.toISOString().split('T')[0];
setCurrentDateRange({ start: startDate, end: endDate });
};
const handleDateSelect = (selectInfo) => {
if (readOnly) {
console.warn('Client attempted to create an event. Action blocked.');
return;
}
const isAllDay = selectInfo.allDay;
const startDate = selectInfo.startStr.split('T')[0];
let endDate = selectInfo.endStr ? selectInfo.endStr.split('T')[0] : '';
setIsEditing(false);
setEventData({
id: null,
title: '',
description: '',
startDate: startDate,
endDate: endDate,
startTime: isAllDay ? '' : selectInfo.startStr.split('T')[1] || '09:00',
endTime: isAllDay ? '' : selectInfo.endStr.split('T')[1] || '10:00',
allDay: isAllDay,
partyBEmail: '',
meetingtype: '',
caseId: '',
courtName: '',
courtNumber: '',
clientName: '',
judgeName: '',
taskType: 'Personal',
eventType: '',
sendReminder: 'None',
occurrence: 'only once'
});
setOpen(true);
};
const handleEventClick = (clickInfo) => {
const event = clickInfo.event;
const isAllDay = event.allDay;
let startDate = event.startStr?.split('T')[0];
let endDate = event.endStr?.split('T')[0];
if (isAllDay && endDate) {
const endDateObj = new Date(endDate);
endDateObj.setDate(endDateObj.getDate() - 1);
endDate = endDateObj.toISOString().split('T')[0];
}
const newEventData = {
id: event.id,
title: event.title,
description: event.extendedProps.description || '',
startDate: startDate || '',
endDate: endDate || '',
startTime: isAllDay ? '' : event.startStr.split('T')[1]?.slice(0, 5) || '09:00',
endTime: isAllDay && !event.endStr ? '' : event.endStr?.split('T')[1]?.slice(0, 5) || '10:00',
allDay: isAllDay,
partyBEmail: event.extendedProps.partyBEmail || '',
meetingtype: event.extendedProps.meetingtype || '',
caseId: event.extendedProps.caseId || '',
courtName: event.extendedProps.courtName || '',
courtNumber: event.extendedProps.courtNumber || '',
clientName: event.extendedProps.clientName || '',
judgeName: event.extendedProps.judgeName || '',
taskType: event.extendedProps.taskType || 'Personal',
eventType: event.extendedProps.eventType || '',
sendReminder: event.extendedProps.sendReminder || 'None',
recurring: event.extendedProps.recurring || false,
occurrence: event.extendedProps.occurrence || 'only once'
};
setIsEditing(true);
setInitialEventData(newEventData);
setEventData(newEventData);
setOpen(true);
};
const getUpdatedFields = () => {
if (!initialEventData) return [];
const updated = [];
for (const key in eventData) {
if (eventData[key] !== initialEventData[key]) {
updated.push(key);
}
}
return updated;
};
const handleEventSubmit = async () => {
if (readOnly) {
console.warn('Client attempted to submit an event. Action blocked.');
setOpen(false);
return;
}
try {
if (!eventData.title || !eventData.startDate || !eventData.endDate) {
throw new Error('Title, Start Date, and End Date are required.');
}
if (eventData.title.length > 100) {
throw new Error('Title cannot exceed 100 characters.');
}
if (eventData.description && eventData.description.length > 500) {
throw new Error('Description cannot exceed 500 characters.');
}
if (eventData.partyBEmail) {
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/i;
if (!emailRegex.test(eventData.partyBEmail)) {
throw new Error('Invalid Party B Email address.');
}
if (eventData.partyBEmail.length > 100) {
throw new Error('Party B Email cannot exceed 100 characters.');
}
}
if (eventData.caseId && eventData.caseId.length > 50) {
throw new Error('Case ID cannot exceed 50 characters.');
}
if (eventData.courtName && eventData.courtName.length > 100) {
throw new Error('Court Name cannot exceed 100 characters.');
}
if (eventData.courtNumber && eventData.courtNumber.length > 50) {
throw new Error('Court Number cannot exceed 50 characters.');
}
if (eventData.clientName && eventData.clientName.length > 100) {
throw new Error('Client Name cannot exceed 100 characters.');
}
if (eventData.judgeName && eventData.judgeName.length > 100) {
throw new Error('Judge Name cannot exceed 100 characters.');
}
const startDateObj = new Date(eventData.startDate);
const endDateObj = new Date(eventData.endDate);
if (endDateObj < startDateObj) {
throw new Error('End Date cannot be before Start Date.');
}
if (!eventData.allDay && eventData.startDate === eventData.endDate) {
const [startHours, startMinutes] = eventData.startTime.split(':').map(Number);
const [endHours, endMinutes] = eventData.endTime.split(':').map(Number);
const startTimeInMinutes = startHours*60 + startMinutes;
const endTimeInMinutes = endHours*60 + endMinutes;
if (endTimeInMinutes <= startTimeInMinutes) {
throw new Error('End Time must be after Start Time.');
}
}
let eventId = eventData.id;
if (!isEditing) {
const now = new Date();
const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
const timeStr = `${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
eventId = eventData.title.toLowerCase().replace(/\\s+/g, '') + '' + dateStr + timeStr;
}
let start, end;
if (eventData.allDay) {
start = eventData.startDate;
const endObj = new Date(eventData.endDate);
endObj.setDate(endObj.getDate() + 1);
end = endObj.toISOString().split('T')[0];
} else {
start = `${eventData.startDate}T${eventData.startTime}`;
end = `${eventData.endDate}T${eventData.endTime}`;
}
const payload = {
id: eventId,
title: eventData.title,
description: eventData.description,
start,
end,
eventType: eventData.eventType,
partyBEmail: eventData.partyBEmail,
meetingtype: eventData.meetingtype,
caseId: eventData.caseId,
Status: 'Y',
courtName: eventData.courtName,
courtNumber: eventData.courtNumber,
clientName: eventData.clientName,
judgeName: eventData.judgeName,
taskType: eventData.taskType,
sendReminder: eventData.sendReminder,
allDay: eventData.allDay,
occurrence: eventData.occurrence,
};
if (new Date(eventData.endDate) - new Date(eventData.startDate) >= 86400000) {
payload.recurring = true;
} else {
payload.recurring = isEditing && eventData.recurring ? eventData.recurring : false;
}
if (isEditing) {
const updatedFields = getUpdatedFields();
if (updatedFields.length === 0) {
setOpen(false);
return;
}
payload.updatedFields = updatedFields;
}
let response;
if (isEditing && eventData.id) {
response = await AxiosInstance.post(`calendar/update-event/`, payload);
} else {
response = await AxiosInstance.post(`calendar/add-event/`, payload);
}
const returnedEvent = response.data.event || response.data;
let backgroundColor = '#6a11cb';
const normType = (eventData.eventType || '').toLowerCase().trim();
if (normType === 'case date') backgroundColor = '#ffb74d';
else if (normType === 'client appointment') backgroundColor = '#4db6ac';
else if (normType === 'court officer appointment') backgroundColor = '#9575cd';
const newEvent = {
id: returnedEvent.id || eventId,
title: returnedEvent.title || payload.title,
description: returnedEvent.description || payload.description,
start: returnedEvent.start || payload.start,
end: returnedEvent.end || payload.end,
allDay: eventData.allDay,
backgroundColor,
borderColor: backgroundColor,
textColor: '#fff',
extendedProps: {
eventType: eventData.eventType,
description: eventData.description,
...returnedEvent
}
};
if (isEditing) {
setEvents((prev) => prev.map((evt) => (evt.id === newEvent.id ? newEvent : evt)));
} else {
setEvents((prev) => [...prev, newEvent]);
}
setOpen(false);
setIsEditing(false);
setEventData({
id: null,
title: '',
description: '',
startDate: '',
endDate: '',
startTime: '',
endTime: '',
partyBEmail: '',
meetingtype: '',
caseId: '',
courtName: '',
courtNumber: '',
clientName: '',
judgeName: '',
taskType: 'Personal',
eventType: '',
sendReminder: 'None',
allDay: false,
occurrence: 'only once',
});
setErrorMessage('');
setSuccessMessage(true);
} catch (error) {
console.error('Error submitting event:', error);
let message = 'Please try again.';
if (error.message) {
message = error.message;
} else if (error.response?.data?.response) {
message = error.response.data.response;
}
setErrorMessage(message);
}
};
const handleDeleteEvent = async () => {
if (readOnly) {
console.warn('Client attempted to delete an event. Action blocked.');
setOpen(false);
return;
}
try {
if (!eventData.id) {
throw new Error('Event ID is missing.');
}
const del_payload = {
id: eventData.id,
title: eventData.title,
partyBEmail: eventData.partyBEmail,
occurrence: eventData.occurrence,
recurring: eventData.recurring
};
await AxiosInstance.post(`calendar/delete-event/`, { data: del_payload });
setEvents((prev) => prev.filter((evt) => evt.id !== eventData.id));
setOpen(false);
setIsEditing(false);
setSuccessMessage(true);
} catch (error) {
console.error('Error deleting event:', error);
setErrorMessage('Error deleting event.');
}
};
const handleEventTypeChange = (e) => {
const eventType = e.target.value;
setEventData((prev) => ({ ...prev, eventType }));
if (eventType === 'Case date') {
setEventData((prev) => ({ ...prev, courtName: '', courtNumber: '', caseId: '', judgeName: '' }));
} else if (eventType === 'Client appointment') {
setEventData((prev) => ({ ...prev, caseId: '', judgeName: '', courtName: '', courtNumber: '' }));
} else if (eventType === 'Court officer appointment') {
setEventData((prev) => ({ ...prev, courtName: '', caseId: '', courtNumber: '', judgeName: '' }));
}
};
const handleSnackbarClose = (event, reason) => {
if (reason === 'clickaway') return;
setSuccessMessage(false);
setErrorMessage('');
};
const renderEventContent = (eventInfo) => {
let timeText = '';
if (!eventInfo.event.allDay) {
timeText = eventInfo.timeText + ' ';
}
return (
<div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
<span>{`${timeText}${eventInfo.event.title}`}</span>
</div>
);
};
const eventDidMount = (info) => {
const normalizedType = (info.event.extendedProps.eventType || '').toLowerCase().trim();
let backgroundColor = '#6a11cb';
if (normalizedType === 'case date') backgroundColor = '#ffb74d';
else if (normalizedType === 'client appointment') backgroundColor = '#4db6ac';
else if (normalizedType === 'court officer appointment') backgroundColor = '#9575cd';
info.el.style.backgroundColor = backgroundColor;
info.el.style.borderColor = backgroundColor;
info.el.style.color = '#fff';
};
return (
<BackgroundBox>
    <Typography variant="h4" gutterBottom>
      Events
    </Typography>

    {/* Toolbar: View Toggle + Actions */}
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        mb: 2
      }}
    >
      {/* View Toggle */}
      <ToggleButtonGroup
        value={view}
        exclusive
        onChange={(e, next) => next !== null && setView(next)}
        size="small"
        sx={{ borderRadius: 1 }}
      >
        <ToggleButton value="calendar">
          <CalendarMonthIcon fontSize="small" sx={{ mr: 0.5 }} />
          Calendar View
        </ToggleButton>
        <ToggleButton value="list">
          <FormatListBulletedIcon fontSize="small" sx={{ mr: 0.5 }} />
          Event List
        </ToggleButton>
      </ToggleButtonGroup>

      {/* Create / Filter / Refresh */}
      <Box
        sx={{
          display: 'flex',
          gap: 1,
          flexWrap: 'wrap',
          alignItems: 'center'
        }}
      >
        {!readOnly && (
          <StyledButton
            onClick={() => {
              setIsEditing(false);
              setErrorMessage('');
              setEventData({
                id: null,
                title: '',
                description: '',
                startDate: '',
                endDate: '',
                startTime: '',
                endTime: '',
                partyBEmail: '',
                meetingtype: '',
                caseId: '',
                courtName: '',
                courtNumber: '',
                clientName: '',
                judgeName: '',
                taskType: 'Personal',
                eventType: '',
                sendReminder: 'None',
                allDay: false,
                occurrence: 'only once'
              });
              setOpen(true);
            }}
          >
            Create Event
          </StyledButton>
        )}

        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Event Type</InputLabel>
          <Select
            label="Event Type"
            value={filters.eventType}
            onChange={(e) => handleFilterChange('eventType', e.target.value)}
          >
            <MenuItem value="All">All</MenuItem>
            <MenuItem value="Case date">Case Date</MenuItem>
            <MenuItem value="Client appointment">Client Appointment</MenuItem>
            <MenuItem value="Court officer appointment">
              Court Officer Appointment
            </MenuItem>
          </Select>
        </FormControl>

        <StyledButton variant="outlined" onClick={clearFilters}>
          Clear Filters
        </StyledButton>
        <StyledButton variant="outlined" onClick={() => fetchEvents()}>
          Refresh
        </StyledButton>
      </Box>
    </Box>

    {/* Main Content */}
    {view === 'calendar' ? (
      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        events={filteredEvents}
        select={handleDateSelect}
        datesSet={handleDatesSet}
        eventClick={handleEventClick}
        editable={!readOnly}
        selectable={!readOnly}
        eventStartEditable={!readOnly}
        eventDurationEditable={!readOnly}
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay'
        }}
        height="auto"
        eventTimeFormat={{
          hour: 'numeric',
          minute: '2-digit',
          meridiem: 'short'
        }}
        eventContent={renderEventContent}
        eventDidMount={eventDidMount}
      />
    ) : (
      <Box sx={{ height: 600, width: '100%' }}>
        <LazyDataGrid
          // map each event to a flat row, with fallbacks to ''
          rows={filteredEvents.map(evt => ({
            id: evt.id,
            title: evt.title || '',
            start: evt.start || '',
            end: evt.end || '',
            eventType: evt.extendedProps?.eventType || '',
            partyBEmail: evt.extendedProps?.partyBEmail || ''
          }))}
          columns={columns}
          pageSize={10}
          rowsPerPageOptions={[10, 25, 50]}
          disableSelectionOnClick
        />
      </Box>
    )}
<Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md">
<DialogTitleStyled>
{isEditing && readOnly ? 'View Event' : isEditing ? 'Update Event' : 'Create Event'}
</DialogTitleStyled>
<DialogContentStyled>
<Box component="form">
<Grid container spacing={2}>
<Grid item xs={12}>
<TextField
label="Title"
fullWidth
margin="dense"
value={eventData.title}
onChange={(e) => setEventData({ ...eventData, title: e.target.value })}
required
error={!eventData.title || eventData.title.length > 100}
helperText={
!eventData.title
? 'Title is required'
: eventData.title.length > 100
? 'Title cannot exceed 100 characters'
: ''
}
inputProps={{ maxLength: 100 }}
disabled={readOnly}
/>
</Grid>
<Grid item xs={12}>
<TextField
label="Description"
fullWidth
margin="dense"
multiline
rows={4}
value={eventData.description}
onChange={(e) => setEventData({ ...eventData, description: e.target.value })}
inputProps={{ maxLength: 500 }}
helperText={
eventData.description && eventData.description.length > 500
? 'Description cannot exceed 500 characters'
: ''
}
disabled={readOnly}
/>
</Grid>
{isEditing && eventData.recurring && !readOnly && (
<Grid item xs={12}>
<FormControl fullWidth margin="dense" required>
<InputLabel>Occurrence</InputLabel>
<Select
value={eventData.occurrence}
onChange={(e) => setEventData({ ...eventData, occurrence: e.target.value })}
label="Occurrence"
>
<MenuItem value="only once">Only once</MenuItem>
<MenuItem value="entire series">Entire series</MenuItem>
</Select>
</FormControl>
</Grid>
)}
<Grid item xs={12} sm={6}>
<FormControl fullWidth margin="dense" required>
<InputLabel>Event Type</InputLabel>
<Select
value={eventData.eventType}
onChange={handleEventTypeChange}
required
label="Event Type"
error={!eventData.eventType}
disabled={readOnly}
>
<MenuItem value="Case date">Case Date</MenuItem>
<MenuItem value="Client appointment">Client Appointment</MenuItem>
<MenuItem value="Court officer appointment">Court Officer Appointment</MenuItem>
</Select>
</FormControl>
</Grid>
{eventData.eventType === 'Case date' && (
<>
<Grid item xs={12} sm={6}>
<TextField
label="Court Name"
fullWidth
margin="dense"
value={eventData.courtName}
onChange={(e) => setEventData({ ...eventData, courtName: e.target.value })}
inputProps={{ maxLength: 100 }}
helperText={
eventData.courtName && eventData.courtName.length > 100
? 'Court Name cannot exceed 100 characters'
: ''
}
disabled={readOnly}
/>
</Grid>
<Grid item xs={12} sm={6}>
<TextField
label="Court Number"
fullWidth
margin="dense"
value={eventData.courtNumber}
onChange={(e) => setEventData({ ...eventData, courtNumber: e.target.value })}
inputProps={{ maxLength: 50 }}
helperText={
eventData.courtNumber && eventData.courtNumber.length > 50
? 'Court Number cannot exceed 50 characters'
: ''
}
disabled={readOnly}
/>
</Grid>
</>
)}
{eventData.eventType === 'Client appointment' && (
<Grid item xs={12} sm={6}>
<TextField
label="Client Name"
fullWidth
margin="dense"
value={eventData.clientName || ''}
onChange={(e) => setEventData({ ...eventData, clientName: e.target.value })}
inputProps={{ maxLength: 100 }}
helperText={
eventData.clientName && eventData.clientName.length > 100
? 'Client Name cannot exceed 100 characters'
: ''
}
disabled={readOnly}
/>
</Grid>
)}
{eventData.eventType === 'Court officer appointment' && (
<Grid item xs={12} sm={6}>
<TextField
label="Judge Name"
fullWidth
margin="dense"
value={eventData.judgeName}
onChange={(e) => setEventData({ ...eventData, judgeName: e.target.value })}
inputProps={{ maxLength: 100 }}
helperText={
eventData.judgeName && eventData.judgeName.length > 100
? 'Judge Name cannot exceed 100 characters'
: ''
}
disabled={readOnly}
/>
</Grid>
)}
<Grid item xs={12}>
<FormControlLabel
control={
<Checkbox
checked={eventData.allDay}
onChange={(e) =>
setEventData({ ...eventData, allDay: e.target.checked })
}
disabled={readOnly}
/>
}
label="All Day Event"
/>
</Grid>
<Grid item xs={12} sm={6}>
<TextField
label="Start Date"
type="date"
fullWidth
margin="dense"
value={eventData.startDate}
onChange={(e) =>
setEventData({ ...eventData, startDate: e.target.value })
}
InputLabelProps={{ shrink: true }}
required
error={!eventData.startDate}
helperText={!eventData.startDate ? 'Start Date is required' : ''}
disabled={readOnly}
/>
</Grid>
<Grid item xs={12} sm={6}>
<TextField
label="End Date"
type="date"
fullWidth
margin="dense"
value={eventData.endDate}
onChange={(e) =>
setEventData({ ...eventData, endDate: e.target.value })
}
InputLabelProps={{ shrink: true }}
required
error={!eventData.endDate}
helperText={!eventData.endDate ? 'End Date is required' : ''}
disabled={readOnly}
/>
</Grid>
{!eventData.allDay && (
<>
<Grid item xs={12} sm={6}>
<TextField
label="Start Time"
type="time"
fullWidth
margin="dense"
value={eventData.startTime}
onChange={(e) =>
setEventData({ ...eventData, startTime: e.target.value })
}
InputLabelProps={{ shrink: true }}
required
error={!eventData.startTime}
helperText={!eventData.startTime ? 'Start Time is required' : ''}
disabled={readOnly}
/>
</Grid>
<Grid item xs={12} sm={6}>
<TextField
label="End Time"
type="time"
fullWidth
margin="dense"
value={eventData.endTime}
onChange={(e) =>
setEventData({ ...eventData, endTime: e.target.value })
}
InputLabelProps={{ shrink: true }}
required
error={!eventData.endTime}
helperText={!eventData.endTime ? 'End Time is required' : ''}
disabled={readOnly}
/>
</Grid>
</>
)}
<Grid item xs={12} sm={6}>
<TextField
label="Party B Email"
fullWidth
margin="dense"
value={eventData.partyBEmail}
onChange={(e) =>
setEventData({ ...eventData, partyBEmail: e.target.value })
}
error={
!!(
eventData.partyBEmail &&
(!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/i.test(eventData.partyBEmail) ||
eventData.partyBEmail.length > 100)
)
}
helperText={
eventData.partyBEmail &&
!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/i.test(eventData.partyBEmail)
? 'Invalid email format'
: eventData.partyBEmail && eventData.partyBEmail.length > 100
? 'Party B Email cannot exceed 100 characters'
: ''
}
inputProps={{ maxLength: 100 }}
disabled={readOnly}
/>
</Grid>
<Grid item xs={12} sm={6}>
<FormControl fullWidth margin="dense">
<InputLabel>Meeting Type</InputLabel>
<Select
label="Meeting Type"
value={eventData.meetingtype}
onChange={(e) =>
setEventData({ ...eventData, meetingtype: e.target.value })
}
disabled={readOnly}
>
<MenuItem value="InPerson">In Person</MenuItem>
<MenuItem value="VideoCall">Video Call</MenuItem>
<MenuItem value="VoiceCall">Voice Call</MenuItem>
</Select>
</FormControl>
</Grid>
<Grid item xs={12} sm={6}>
<TextField
label="Case ID"
fullWidth
margin="dense"
value={eventData.caseId}
onChange={(e) =>
setEventData({ ...eventData, caseId: e.target.value })
}
inputProps={{ maxLength: 50 }}
helperText={
eventData.caseId && eventData.caseId.length > 50
? 'Case ID cannot exceed 50 characters'
: ''
}
disabled={readOnly}
/>
</Grid>
<Grid item xs={12} sm={6}>
<FormControl fullWidth margin="dense">
<InputLabel>Send Reminder</InputLabel>
<Select
label="Send Reminder"
value={eventData.sendReminder}
onChange={(e) =>
setEventData({ ...eventData, sendReminder: e.target.value })
}
disabled={readOnly}
>
<MenuItem value="None">None</MenuItem>
<MenuItem value="Email">Email</MenuItem>
<MenuItem value="WhatsApp">WhatsApp</MenuItem>
<MenuItem value="Both">Both</MenuItem>
</Select>
</FormControl>
</Grid>
{errorMessage && (
<Grid item xs={12}>
<Typography color="error">{errorMessage}</Typography>
</Grid>
)}
</Grid>
</Box>
</DialogContentStyled>
<DialogActionsStyled>
<Button onClick={() => setOpen(false)} color="secondary">
{readOnly ? 'Close' : 'Cancel'}
</Button>
{!readOnly && (
<>
<StyledButton onClick={handleEventSubmit}>
{isEditing ? 'Update Event' : 'Submit'}
</StyledButton>
{isEditing && (
<Button onClick={handleDeleteEvent} color="error" sx={{ color: 'red' }}>
Delete Event
</Button>
)}
</>
)}
</DialogActionsStyled>
</Dialog>
<Snackbar
open={successMessage || !!errorMessage}
autoHideDuration={6000}
onClose={handleSnackbarClose}
message={successMessage ? 'Event submitted successfully!' : errorMessage}
action={
<IconButton size="small" color="inherit" onClick={handleSnackbarClose}>
<CloseIcon fontSize="small" />
</IconButton>
}
/>
</BackgroundBox>
);
};
export default Calendar;