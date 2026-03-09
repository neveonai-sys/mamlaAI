import React, { Suspense, useMemo } from 'react';
import { CircularProgress, Box } from '@mui/material';

// Lazy load FullCalendar
const FullCalendar = React.lazy(() => import('@fullcalendar/react'));
// Import plugins directly since they're not React components
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';

const LazyFullCalendar = React.forwardRef((props, ref) => {
  // Memoize plugins to prevent recreation on each render
  const plugins = useMemo(() => [
    dayGridPlugin,
    timeGridPlugin,
    interactionPlugin
  ], []);

  return (
    <Suspense 
      fallback={
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <CircularProgress />
        </Box>
      }
    >
      <FullCalendar
        ref={ref}
        plugins={plugins}
        initialView="dayGridMonth"
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay'
        }}
        {...props}
      />
    </Suspense>
  );
});

export default LazyFullCalendar;
