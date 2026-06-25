import React from 'react';
import PublicNavbar from '../shared/PublicNavbar';
import PublicFooter from '../shared/PublicFooter';
import PageHero from '../shared/PageHero';
import Seo from '../shared/Seo';
import SolutionsSection from '../sections/SolutionsSection';

export default function SolutionsPage() {
  return (
    <div className="bg-background-light text-ink antialiased">
      <Seo
        path="/solutions"
        title="Solutions for Lawyers, Litigants, Law Students & Law Firms | Mamla AI"
        description="Legal software solutions tailored to lawyers, litigants, law students and law firms in India — AI drafting, eCourts tracking, legal research, client management and firm-wide collaboration."
      />
      <PublicNavbar />
      <PageHero
        eyebrow="Solutions"
        title="Built for every kind of legal professional"
        subtitle="Whether you're a solo advocate, a litigant tracking your own case, a law student or a multi-lawyer firm — Mamla AI adapts to how you work."
        cta="Get Started Free"
      />
      <SolutionsSection />
      <PublicFooter />
    </div>
  );
}
