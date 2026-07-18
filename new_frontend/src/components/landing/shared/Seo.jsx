import React from 'react';
import { Helmet } from 'react-helmet-async';

const SITE_URL = 'https://mamla.ai';

// Per-page SEO: title, meta description, canonical, Open Graph/Twitter and
// optional JSON-LD structured data. Rendered at the top of every public page
// so each route ships unique, crawlable metadata.
export default function Seo({ title, description, path = '/', jsonLd }) {
  const canonical = `${SITE_URL}${path}`;
  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={canonical} />

      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:type" content="website" />
      <meta property="og:url" content={canonical} />
      <meta property="og:locale" content="en_IN" />

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />

      {jsonLd && (
        <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
      )}
    </Helmet>
  );
}
