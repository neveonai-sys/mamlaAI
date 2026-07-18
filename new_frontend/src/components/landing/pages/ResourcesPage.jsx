import React from 'react';
import PublicNavbar from '../shared/PublicNavbar';
import PublicFooter from '../shared/PublicFooter';
import PageHero from '../shared/PageHero';
import Seo from '../shared/Seo';
import ResourcesSection from '../sections/ResourcesSection';
import LiveCourtStats from '../sections/LiveCourtStats';

export default function ResourcesPage() {
  return (
    <div className="bg-background-light text-ink antialiased">
      <Seo
        path="/resources"
        title="Legal Resources — Live Court Data, Citation & Cause List Search | Mamla AI"
        description="Legal research resources and AI legal insights: real-time eCourts case data, Supreme Court and High Court intelligence, citation search, cause list search and legal news."
      />
      <PublicNavbar />
      <PageHero
        eyebrow="Resources"
        title="Legal intelligence at your fingertips"
        subtitle="Real-time court data, citation and cause list search, and AI legal insights — everything you need to stay ahead, in one place."
      />
      <ResourcesSection />
      <LiveCourtStats />
      <PublicFooter />
    </div>
  );
}
