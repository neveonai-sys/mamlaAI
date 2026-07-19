import React, { useState } from 'react';
import apiClient from '../../../services/api';

export default function ContactSection() {
  const [form, setForm] = useState({ name: '', email: '', phone: '', message: '' });
  const [status, setStatus] = useState('idle');

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus('sending');
    try {
      await apiClient.post('utils/contact/', form);
      setStatus('success');
      setForm({ name: '', email: '', phone: '', message: '' });
    } catch (err) {
      setStatus('error');
    }
  }

  const inputCls = 'w-full rounded-md border border-slate-300 px-4 py-3 text-sm text-ink shadow-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/30';

  return (
    <section id="contact" className="bg-slate-50 py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="rounded-3xl bg-white p-8 shadow-lg md:p-16">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Contact &amp; Support</p>
            <h2 className="font-display text-3xl font-bold text-ink md:text-4xl">
              Contact Mamla AI — AI Legal Software for Lawyers &amp; Law Firms
            </h2>
            <p className="mt-4 text-sm leading-7 text-slate-600">
              Schedule a demo and discover how AI-powered legal software can improve drafting, legal research, case
              management and client communication.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-12 md:grid-cols-3">
            {/* Form */}
            <div className="md:col-span-2">
              <form className="grid grid-cols-1 gap-6 sm:grid-cols-2" onSubmit={handleSubmit}>
                <input name="name" type="text" value={form.name} onChange={handleChange} required placeholder="Full Name" className={inputCls} />
                <input name="email" type="email" value={form.email} onChange={handleChange} required placeholder="Email Address" className={inputCls} />
                <div className="sm:col-span-2">
                  <input name="phone" type="tel" value={form.phone} onChange={handleChange} placeholder="Phone Number" className={inputCls} />
                </div>
                <div className="sm:col-span-2">
                  <textarea name="message" value={form.message} onChange={handleChange} rows={4} placeholder="Message" className={`${inputCls} resize-y`} />
                </div>
                <div className="sm:col-span-2">
                  <button
                    type="submit"
                    disabled={status === 'sending'}
                    className="w-full rounded-md bg-primary py-3.5 text-sm font-bold text-white transition-colors hover:bg-primary-dark disabled:opacity-60"
                  >
                    {status === 'sending' ? 'Sending…' : 'Submit Inquiry'}
                  </button>
                </div>
                {status === 'success' && (
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700 sm:col-span-2">
                    ✓ Message sent! We&apos;ll respond within one business day.
                  </div>
                )}
                {status === 'error' && (
                  <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700 sm:col-span-2">
                    Something went wrong. Please email us directly at{' '}
                    <a href="mailto:neveon.ai@gmail.com" className="underline">neveon.ai@gmail.com</a>.
                  </div>
                )}
              </form>
            </div>

            {/* Contact info */}
            <div className="space-y-6">
              <div>
                <h4 className="mb-3 font-bold text-ink">Contact</h4>
                {[
                  { label: 'Email', value: 'neveon.ai@gmail.com', href: 'mailto:neveon.ai@gmail.com' },
                  { label: 'Company', value: 'Neveon AI Technologies Pvt. Ltd.', href: null },
                  { label: 'Office', value: 'India (Remote-first)', href: null },
                  { label: 'Response', value: 'Within 1 business day', href: null },
                ].map((item) => (
                  <p key={item.label} className="mb-2 text-sm text-slate-600">
                    <span className="font-semibold text-ink">{item.label}:</span>{' '}
                    {item.href ? (
                      <a href={item.href} className="text-primary hover:underline">{item.value}</a>
                    ) : (
                      item.value
                    )}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
