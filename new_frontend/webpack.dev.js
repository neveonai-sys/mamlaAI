const { merge } = require('webpack-merge');
const common = require('./webpack.common');
const ReactRefreshWebpackPlugin = require('@pmmmwh/react-refresh-webpack-plugin');
const webpack = require('webpack');
const fs = require('fs');
const path = require('path');

// Load .env into process.env (only sets vars not already in environment)
const envPath = path.resolve(__dirname, '.env');
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, 'utf8').split('\n').forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) return;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx < 1) return;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim();
    if (!(key in process.env)) process.env[key] = val;
  });
}

module.exports = merge(common, {
  mode: 'development',
  devtool: 'cheap-module-source-map',

  devServer: {
    port: parseInt(process.env.DEV_PORT || '3001', 10),
    host: 'localhost',
    hot: true,
    historyApiFallback: true,
    allowedHosts: 'auto',
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
    },
    proxy: [
      {
        context: ['/api'],
        target: `http://127.0.0.1:${process.env.DEV_BACKEND_PORT || '8100'}`,
        changeOrigin: true,
        secure: false,
      },
    ],
  },

  plugins: [
    new ReactRefreshWebpackPlugin(),
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify('development'),
      'process.env.REACT_APP_API_BASE_URL': JSON.stringify(''),
      'process.env.REACT_APP_SUPABASE_URL': JSON.stringify(process.env.REACT_APP_SUPABASE_URL || ''),
      'process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY': JSON.stringify(process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY || ''),
      'process.env.REACT_APP_POSTHOG_KEY': JSON.stringify(process.env.REACT_APP_POSTHOG_KEY || ''),
      'process.env.REACT_APP_POSTHOG_HOST': JSON.stringify(process.env.REACT_APP_POSTHOG_HOST || ''),
      'process.env.REACT_APP_ADMIN_EMAILS': JSON.stringify(process.env.REACT_APP_ADMIN_EMAILS || ''),
    }),
  ],
});
