import React from 'react';
import { Link } from 'react-router-dom';
import PublicNavbar from '../shared/PublicNavbar';
import PublicFooter from '../shared/PublicFooter';
import Seo from '../shared/Seo';
import CaseTrackingHero from '../sections/CaseTrackingHero';
import CaseTrackingBenefits from '../sections/CaseTrackingBenefits';
import LiveCourtStats from '../sections/LiveCourtStats';
import FAQSection from '../sections/FAQSection';

export default function CaseTrackingPage() {
  return (
    <div className="bg-background-light text-ink antialiased">
      <Seo
        path="/case-tracking"
        title="AI Case Tracking for Indian Courts — Live eCourts Status | Mamla AI"
        description="Track case status, hearing dates, orders and cause lists from all 25 High Courts and District Courts in real time. AI-powered eCourts case tracking with smart hearing alerts for Indian lawyers and litigants."
      />
      <PublicNavbar />
      <CaseTrackingHero />
      <CaseTrackingBenefits />
      <LiveCourtStats />
      <FAQSection />

      {/* Bottom CTA */}
      <section className="bg-background-dark py-24 text-ivory">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <h2 className="mb-5 font-display text-3xl font-bold text-white md:text-4xl">
            Track every matter in one place
          </h2>
          <p className="mb-10 text-base font-medium leading-8 text-white/65">
            Start tracking your cases across Indian courts today — no card needed. Lock in early-adopter beta pricing.
          </p>
          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link to="/signup" className="rounded-xl bg-white px-8 py-4 text-[15px] font-bold text-primary-dark shadow-elevated transition-all hover:-translate-y-0.5 hover:bg-primary-soft">
              Start Free
            </Link>
            <Link to="/pricing" className="rounded-xl border border-white/15 bg-white/8 px-8 py-4 text-[15px] font-medium text-white/80 transition-all hover:bg-white/14">
              View Pricing
            </Link>
          </div>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
