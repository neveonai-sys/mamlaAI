const reportWebVitals = onPerfEntry => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    // Only enable web-vitals in production for now to avoid dev issues
    if (process.env.NODE_ENV === 'production') {
      import('web-vitals').then((webVitals) => {
        // Use the most compatible API approach
        const { getCLS, getFID, getFCP, getLCP, getTTFB } = webVitals;
        if (getCLS) getCLS(onPerfEntry);
        if (getFID) getFID(onPerfEntry);
        if (getFCP) getFCP(onPerfEntry);
        if (getLCP) getLCP(onPerfEntry);
        if (getTTFB) getTTFB(onPerfEntry);
      }).catch(() => {
        console.log('Web Vitals not available in production');
      });
    } else {
      // In development, just log that web vitals would be measured
      console.log('Web Vitals measurement disabled in development');
    }
  }
};

export default reportWebVitals;
