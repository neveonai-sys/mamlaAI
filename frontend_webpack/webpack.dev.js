const { merge } = require('webpack-merge');
const common = require('./webpack.common');
const ReactRefreshWebpackPlugin = require('@pmmmwh/react-refresh-webpack-plugin');

module.exports = merge(common, {
  mode: 'development',

  devtool: 'cheap-module-source-map',

  devServer: {
  port: 3000,
  host: 'localhost',
  hot: true,
  historyApiFallback: true,
  allowedHosts: 'auto',

  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      secure: false,
    },
  },
},

  plugins: [
    new ReactRefreshWebpackPlugin(),
  ],

  module: {
    rules: [
      {
        test: /\.(js|jsx|ts|tsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            plugins: ['react-refresh/babel'],
          },
        },
      },
    ],
  },
});
