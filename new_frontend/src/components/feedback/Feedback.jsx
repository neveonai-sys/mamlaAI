import React, { useState } from 'react';
import apiClient from '../../services/api';
import { usePostHog } from '@posthog/react';

const CATEGORIES = ['UI/UX', 'AI Quality', 'Document Drafting', 'Search', 'Performance', 'Bug Report', 'Feature Request', 'Other'];
const RATINGS = [1, 2, 3, 4, 5];

export default function Feedback() {
  const posthog = usePostHog();
  const [form, setForm] = useState({
    category: 'General',
    rating: 0,
    message: '',
    email: '',
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.message.trim()) {
      setError('Please provide your feedback message.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await apiClient.post('users/feedback/', form);
      posthog?.capture('feedback_submitted', {
        category: form.category,
        rating: form.rating,
      });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to submit feedback. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 text-center p-8">
        <div className="size-20 bg-emerald-100 rounded-full flex items-center justify-center">
          <span className="material-symbols-outlined text-emerald-600 text-4xl icon-filled">check_circle</span>
        </div>
        <div>
          <h2 className="text-2xl font-black text-ink mb-2">Thank You!</h2>
          <p className="text-slate-500 max-w-sm">
            Your feedback has been submitted successfully. We&apos;ll use it to improve Mamla.AI.
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => { setSuccess(false); setForm({ category: 'General', rating: 0, message: '', email: '' }); }}
        >
          Submit Another
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-8">
        <h2 className="text-2xl font-black text-ink tracking-tight">Share Feedback</h2>
        <p className="text-slate-500 text-sm mt-1">
          Help us improve Mamla.AI. Your insights are invaluable.
        </p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Category */}
          <div>
            <label className="block text-sm font-semibold mb-3 text-slate-700">Category</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, category: cat }))}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-full border transition-all ${
                    form.category === cat
                      ? 'bg-primary text-ivory border-primary'
                      : 'bg-white text-slate-600 border-slate-200 hover:border-primary/50'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Star rating */}
          <div>
            <label className="block text-sm font-semibold mb-3 text-slate-700">
              Overall Rating
            </label>
            <div className="flex gap-2">
              {RATINGS.map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, rating: star }))}
                  className="transition-transform hover:scale-110"
                >
                  <span
                    className={`material-symbols-outlined text-3xl ${
                      form.rating >= star ? 'text-amber-400 icon-filled' : 'text-slate-300'
                    }`}
                  >
                    star
                  </span>
                </button>
              ))}
              {form.rating > 0 && (
                <span className="text-sm text-slate-500 self-center ml-2">
                  {['', 'Poor', 'Fair', 'Good', 'Great', 'Excellent'][form.rating]}
                </span>
              )}
            </div>
          </div>

          {/* Message */}
          <div>
            <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="message">
              Your Feedback *
            </label>
            <textarea
              id="message"
              name="message"
              required
              rows={6}
              value={form.message}
              onChange={handleChange}
              placeholder="Tell us what you think, what works well, or what could be improved…"
              className="input-base resize-none"
            />
          </div>

          {/* Optional email */}
          <div>
            <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="feedback-email">
              Contact Email <span className="text-slate-400 font-normal">(optional — for follow-up)</span>
            </label>
            <input
              id="feedback-email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              placeholder="your@email.com"
              className="input-base"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <span className="material-symbols-outlined text-base">error</span>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="material-symbols-outlined text-base animate-spin">progress_activity</span>
                Submitting…
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-base">send</span>
                Submit Feedback
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
