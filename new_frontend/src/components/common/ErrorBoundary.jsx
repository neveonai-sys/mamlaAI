import React from 'react';
import { useNavigate } from 'react-router-dom';
import posthog from 'posthog-js';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
    posthog?.captureException(error, { extra: { componentStack: info?.componentStack } });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-screen gap-6 bg-background-light">
          <span className="material-symbols-outlined text-primary text-6xl">error</span>
          <div className="text-center max-w-sm">
            <h1 className="text-2xl font-bold text-ink mb-2">Something went wrong</h1>
            <p className="text-sm text-ink/60 mb-6">
              An unexpected error occurred. Please refresh the page or navigate back to the dashboard.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              className="btn-primary"
              onClick={() => window.location.reload()}
            >
              Refresh Page
            </button>
            <button
              className="btn-ghost"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.href = '/dashboard';
              }}
            >
              Go to Dashboard
            </button>
          </div>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="mt-4 max-w-lg text-xs text-red-600 bg-red-50 p-3 rounded-lg border border-red-200">
              <summary className="cursor-pointer font-semibold">Error details (dev only)</summary>
              <pre className="mt-2 whitespace-pre-wrap">{this.state.error.toString()}</pre>
            </details>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
