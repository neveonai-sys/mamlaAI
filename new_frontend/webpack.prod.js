const { merge } = require('webpack-merge');
const common = require('./webpack.common');
const webpack = require('webpack');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');
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

const apiBaseUrl =
  process.env.REACT_APP_API_BASE_URL || 'https://mamla.ai/api/';

module.exports = merge(common, {
  mode: 'production',
  devtool: false, // no source maps in prod — keeps bundle lean and source private

  optimization: {
    minimizer: [
      new TerserPlugin({ parallel: true }),
      new CssMinimizerPlugin(),
    ],
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        // React core — tiny, cached forever
        reactVendor: {
          test: /[\\/]node_modules[\\/](react|react-dom|react-router-dom|react-redux|@reduxjs)[\\/]/,
          name: 'vendor-react',
          chunks: 'all',
          priority: 40,
        },
        // PDF viewer (pdfjs-dist) — 3 MB+, isolated so landing never parses it
        pdfVendor: {
          test: /[\\/]node_modules[\\/](react-pdf|pdfjs-dist)[\\/]/,
          name: 'vendor-pdf',
          chunks: 'all',
          priority: 35,
        },
        // Calendar — large, only needed on /calendar
        calendarVendor: {
          test: /[\\/]node_modules[\\/]@fullcalendar[\\/]/,
          name: 'vendor-calendar',
          chunks: 'all',
          priority: 30,
        },
        // Supabase auth client
        supabaseVendor: {
          test: /[\\/]node_modules[\\/]@supabase[\\/]/,
          name: 'vendor-supabase',
          chunks: 'all',
          priority: 25,
        },
        // Everything else in node_modules
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendor-common',
          chunks: 'all',
          priority: 10,
        },
      },
    },
  },

  plugins: [
    new MiniCssExtractPlugin({
      filename: '[name].[contenthash].css',
      chunkFilename: '[id].[contenthash].css',
    }),
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify('production'),
      'process.env.REACT_APP_API_BASE_URL': JSON.stringify(apiBaseUrl),
      'process.env.REACT_APP_SUPABASE_URL': JSON.stringify(process.env.REACT_APP_SUPABASE_URL || ''),
      'process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY': JSON.stringify(process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY || ''),
      'process.env.REACT_APP_POSTHOG_KEY': JSON.stringify(process.env.REACT_APP_POSTHOG_KEY || ''),
      'process.env.REACT_APP_POSTHOG_HOST': JSON.stringify(process.env.REACT_APP_POSTHOG_HOST || ''),
      'process.env.REACT_APP_ADMIN_EMAILS': JSON.stringify(process.env.REACT_APP_ADMIN_EMAILS || ''),
    }),
  ],
});
