const { merge } = require('webpack-merge');
const common = require('./webpack.common');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');
const CompressionPlugin = require('compression-webpack-plugin');
const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
const webpack = require('webpack');

module.exports = merge(common, {
  mode: 'production',
  devtool: false, // DISABLE source maps - prevents code exposure in production

  output: {
    path: __dirname + '/dist',
    filename: 'static/js/[name].[contenthash:8].js',
    chunkFilename: 'static/js/[name].[contenthash:8].chunk.js',
    publicPath: '/',
    clean: true,
    pathinfo: false, // Don't include path info in bundles (security)
  },

  module: {
    rules: [
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader', 'postcss-loader'],
      },
    ],
  },

  plugins: [
    // Define environment variables
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify('production'),
      'process.env.REACT_APP_API_BASE_URL': JSON.stringify(process.env.REACT_APP_API_BASE_URL || 'https://mamla.ai/api/'),
      '__REACT_DEVTOOLS_GLOBAL_HOOK__': '({ isDisabled: true })', // Disable React DevTools
    }),
    new MiniCssExtractPlugin({
      filename: 'static/css/[name].[contenthash:8].css',
      chunkFilename: 'static/css/[name].[contenthash:8].chunk.css',
    }),
    // Gzip compression for production
    new CompressionPlugin({
      filename: '[path][base].gz',
      algorithm: 'gzip',
      test: /\.(js|css|html|svg)$/,
      threshold: 10240, // Only compress files > 10KB
      minRatio: 0.8,
    }),
    // Uncomment to analyze bundle size: npm run build:analyze
    process.env.BUNDLE_ANALYZE && new BundleAnalyzerPlugin({
      analyzerMode: 'static',
      openAnalyzer: false,
      reportFilename: 'bundle-report.html'
    }),
  ].filter(Boolean),

  optimization: {
    minimize: true,
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          parse: { ecma: 8 },
          compress: {
            ecma: 5,
            warnings: false,
            comparisons: false,
            inline: 2,
            drop_console: true, // Remove console.logs
            drop_debugger: true, // Remove debugger statements
            pure_funcs: ['console.log', 'console.info', 'console.debug'], // Remove specific functions
          },
          mangle: {
            safari10: true,
            // Don't mangle properties - breaks module imports
          },
          output: {
            ecma: 5,
            comments: false, // Remove all comments
            ascii_only: true,
          },
          // Keep class/function names for modules to work
          keep_classnames: true,
          keep_fnames: true,
        },
        parallel: true,
        extractComments: false, // Don't create separate license files
      }),
      new CssMinimizerPlugin(),
    ],
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        // Vendor chunk for node_modules
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10,
          reuseExistingChunk: true,
        },
        // MUI components in separate chunk
        mui: {
          test: /[\\/]node_modules[\\/]@mui[\\/]/,
          name: 'mui',
          priority: 20,
          reuseExistingChunk: true,
        },
        // Common code used across multiple chunks
        common: {
          minChunks: 2,
          priority: 5,
          reuseExistingChunk: true,
          enforce: true,
        },
      },
    },
    runtimeChunk: 'single',
    moduleIds: 'deterministic', // Better long-term caching
    usedExports: true, // Tree shaking - remove unused code
    sideEffects: false, // Assume no side effects for better tree shaking
  },

  performance: {
    hints: 'warning',
    maxEntrypointSize: 512000, // 500 KB
    maxAssetSize: 512000,
  },
});
