import React from 'react';
import SectionHeading from '../shared/SectionHeading';

const BENEFITS = [
  {
    icon: 'schedule',
    title: 'Real-time eCourts Status',
    desc: 'Live case status, hearing dates, orders and cause lists pulled directly from all 25 High Courts and District Courts across India.',
  },
  {
    icon: 'notifications_active',
    title: 'Smart Hearing Alerts',
    desc: 'Automated reminders for hearing dates and filing deadlines, so a missed date never costs you or your client.',
  },
  {
    icon: 'track_changes',
    title: 'Case Strategy & Insights',
    desc: 'AI analyses your matter — applicable law, precedents and likely next steps — to help you walk into court better prepared.',
  },
];

export default function CaseTrackingBenefits() {
  return (
    <section className="bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeading eyebrow="Why AI Case Tracking?" title="Stay ahead of every development in Indian courts" />
        <div className="grid gap-8 md:grid-cols-3">
          {BENEFITS.map((b) => (
            <div
              key={b.title}
              className="rounded-2xl border border-transparent bg-background-light p-10 text-center transition-all hover:-translate-y-1 hover:border-primary/30 hover:shadow-elevated"
            >
              <div className="mb-6 flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-sm">
                  <span className="material-symbols-outlined text-3xl text-primary">{b.icon}</span>
                </div>
              </div>
              <h3 className="mb-4 text-xl font-bold text-ink">{b.title}</h3>
              <p className="text-sm leading-relaxed text-graphite">{b.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
