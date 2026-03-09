module.exports = (api) => {
  const isDevelopment = api.env('development');
  const isProduction = api.env('production');
  
  return {
    presets: [
      ['@babel/preset-env', { 
        useBuiltIns: 'usage',
        corejs: 3,
        targets: '> 0.25%, not dead, not op_mini all',
        modules: false
      }],
      ['@babel/preset-react', {
        runtime: 'automatic',
        development: isDevelopment,
        importSource: '@emotion/react'
      }],
      '@babel/preset-typescript'
    ],
    plugins: [
      '@babel/plugin-transform-runtime',
      '@babel/plugin-proposal-class-properties',
      ['babel-plugin-direct-import', {
        modules: ['@mui/material', '@mui/icons-material']
      }],
      isDevelopment && 'react-refresh/babel',
      // Remove console.logs in production (keep error and warn)
      isProduction && ['./babel-plugin-remove-console.js', { exclude: ['error', 'warn'] }],
      // Optimize React in production
      isProduction && '@babel/plugin-transform-react-inline-elements'
    ].filter(Boolean),
    overrides: [
      {
        test: /node_modules\/@mui/,
        plugins: [
          '@babel/plugin-transform-runtime',
          '@babel/plugin-proposal-class-properties',
          ['babel-plugin-direct-import', {
            modules: ['@mui/material', '@mui/icons-material']
          }]
          // no react-refresh for @mui
        ]
      }
    ],
    assumptions: {
      setPublicClassFields: true,
      privateFieldsAsSymbols: true,
      setClassMethods: true
    }
  }
};
