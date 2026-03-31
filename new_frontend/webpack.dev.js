const { merge } = require('webpack-merge');
const common = require('./webpack.common');
const ReactRefreshWebpackPlugin = require('@pmmmwh/react-refresh-webpack-plugin');
const webpack = require('webpack');

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
      'process.env.REACT_APP_SUPABASE_ANON_KEY': JSON.stringify(process.env.REACT_APP_SUPABASE_ANON_KEY || ''),
    }),
  ],
});
