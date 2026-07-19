import React from 'react';
import PublicNavbar from '../shared/PublicNavbar';
import PublicFooter from '../shared/PublicFooter';
import PageHero from '../shared/PageHero';
import Seo from '../shared/Seo';
import PricingSection from '../sections/PricingSection';
import { LAWYER_PLANS } from '../data/pricing';

// Product + Offer structured data so pricing surfaces in search results.
const pricingJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Product',
  name: 'Mamla AI — Legal Practice Management Software',
  description: 'AI-powered legal practice management software for Indian lawyers, law firms, litigants and law students.',
  brand: { '@type': 'Brand', name: 'Mamla AI' },
  offers: LAWYER_PLANS
    // Skip non-numeric / custom-priced plans (e.g. the Firm "Custom" tier) so
    // structured data never emits a NaN/empty price.
    .filter((p) => !p.custom && /\d/.test(p.price))
    .map((p) => ({
      '@type': 'Offer',
      name: p.name,
      price: p.price.replace(/[^0-9]/g, '') || '0',
      priceCurrency: 'INR',
      availability: 'https://schema.org/InStock',
    })),
};

export default function PricingPage() {
  return (
    <div className="bg-background-light text-ink antialiased">
      <Seo
        path="/pricing"
        title="Pricing — Affordable AI Legal Software Plans | Mamla AI"
        description="Simple, affordable pricing for AI legal software. Plans for solo advocates, law students, litigants (Nagrik) and law firms. Start free, upgrade anytime."
        jsonLd={pricingJsonLd}
      />
      <PublicNavbar />
      <PageHero
        eyebrow="Pricing"
        title="Affordable plans for every practice"
        subtitle="From law students to multi-lawyer firms and citizens tracking their own matters — pick a plan that fits. Simple, transparent pricing with no hidden fees."
      />
      <PricingSection />
      <PublicFooter />
    </div>
  );
}
