import React from 'react';
import PublicNavbar from '../shared/PublicNavbar';
import PublicFooter from '../shared/PublicFooter';
import PageHero from '../shared/PageHero';
import Seo from '../shared/Seo';
import FeaturesSection from '../sections/FeaturesSection';
import SecuritySection from '../sections/SecuritySection';

export default function FeaturesPage() {
  return (
    <div className="bg-background-light text-ink antialiased">
      <Seo
        path="/features"
        title="Features — AI Legal Drafting, eCourts Tracking & More | Mamla AI"
        description="Explore Mamla AI features: AI legal drafting, eCourts case tracking, legal calendar, AI document analysis, case strategiser, citation search, legal CRM and enterprise security for Indian lawyers."
      />
      <PublicNavbar />
      <PageHero
        eyebrow="Product"
        title="Everything you need to run a modern legal practice"
        subtitle="AI legal drafting, eCourts case tracking, document analysis, case strategy, citation search and more — purpose-built for Indian lawyers, law firms and litigants."
        cta="Try Mamla AI Free"
      />
      <FeaturesSection />
      <SecuritySection />
      <PublicFooter />
    </div>
  );
}
