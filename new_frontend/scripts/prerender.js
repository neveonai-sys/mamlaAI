/*
 * Build-time prerender for the public hub pages.
 *
 * react-snap's bundled Chromium (78) is too old to parse the modern JS in our
 * vendor bundles (optional chaining `?.`). So we drive react-snap with the
 * modern Chrome that the `puppeteer` package downloads, resolved at runtime so
 * this stays portable across machines/CI.
 *
 * Each listed route is rendered to dist/<route>/index.html as static HTML, so
 * search engines get real content and the page hydrates fast. The landing page
 * ("/") is intentionally excluded — it keeps its hand-tuned static-LCP markup
 * baked into public/index.html.
 */
const { run } = require('react-snap');
const puppeteer = require('puppeteer');

run({
  source: 'dist',
  include: ['/features', '/case-tracking', '/solutions', '/pricing', '/resources', '/about'],
  crawl: false,
  inlineCss: false,
  // Render one page at a time. react-helmet-async flushes head changes on an
  // animation frame; backgrounded tabs (concurrency > 1) get rAF throttled, so
  // only the foreground tab's metadata lands. Single tab = always foreground.
  concurrency: 1,
  // Give helmet-async time to flush <title>/<meta>/JSON-LD before capture.
  waitFor: 1500,
  // Block third-party + same-origin API calls (e.g. the auth check) so the
  // capture is deterministic and not held up by failing requests.
  skipThirdPartyRequests: true,
  puppeteerArgs: [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    // Belt-and-braces against rAF/timer throttling during prerender.
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding',
  ],
  puppeteerExecutablePath: puppeteer.executablePath(),
}).catch((err) => {
  console.error(err);
  process.exit(1);
});
