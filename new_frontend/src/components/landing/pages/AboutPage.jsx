import React from 'react';
import PublicNavbar from '../shared/PublicNavbar';
import PublicFooter from '../shared/PublicFooter';
import PageHero from '../shared/PageHero';
import Seo from '../shared/Seo';
import AboutSection from '../sections/AboutSection';
import FAQSection from '../sections/FAQSection';
import ContactSection from '../sections/ContactSection';
import { FAQS } from '../data/faqs';

// FAQPage structured data so questions can appear as rich results.
const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQS.map((f) => ({
    '@type': 'Question',
    name: f.q,
    acceptedAnswer: { '@type': 'Answer', text: f.a },
  })),
};

export default function AboutPage() {
  return (
    <div className="bg-background-light text-ink antialiased">
      <Seo
        path="/about"
        title="About Mamla AI — AI Legal Software Built for Indian Lawyers | Contact & FAQ"
        description="Learn about Mamla AI and Neveon AI Technologies. Read frequently asked questions about AI legal software, and contact our team to schedule a demo."
        jsonLd={faqJsonLd}
      />
      <PublicNavbar />
      <PageHero
        eyebrow="About Mamla.AI"
        title="AI legal software built for Indian lawyers"
        subtitle="We combine deep understanding of Indian law with cutting-edge AI to give every advocate, firm and litigant the tools they deserve."
      />
      <AboutSection />
      <FAQSection />
      <ContactSection />
      <PublicFooter />
    </div>
  );
}
