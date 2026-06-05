import React from 'react';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import { store } from './store';
import App from './App';
import ErrorBoundary from './components/common/ErrorBoundary';
import './index.css';

import posthog from 'posthog-js';
import { PostHogProvider, PostHogErrorBoundary } from '@posthog/react';

posthog.init(process.env.REACT_APP_POSTHOG_KEY, {
  // Route through our own domain so ad blockers don't block eu.i.posthog.com
  api_host: process.env.REACT_APP_POSTHOG_HOST || 'https://eu.i.posthog.com',
  ui_host: 'https://eu.posthog.com',
  defaults: '2026-01-30',
  autocapture: false,
  capture_pageview: false,
  disable_session_recording: true,
});

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <React.StrictMode>
    <PostHogProvider client={posthog}>
      <PostHogErrorBoundary>
        <ErrorBoundary>
          <Provider store={store}>
            <App />
          </Provider>
        </ErrorBoundary>
      </PostHogErrorBoundary>
    </PostHogProvider>
  </React.StrictMode>
);
