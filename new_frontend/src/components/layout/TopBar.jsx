import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';

export default function TopBar({ onToggleSidebar, title }) {
  const navigate = useNavigate();
  const { firstname, user_type } = useSelector((s) => s.user);

  return (
    <header className="h-16 bg-ivory border-b border-primary/10 flex items-center px-6 gap-4 flex-shrink-0 z-10">
      {/* Mobile hamburger */}
      <button
        className="lg:hidden p-1.5 rounded-md hover:bg-primary/5 text-ink/40 hover:text-primary transition-colors"
        onClick={onToggleSidebar}
        aria-label="Open menu"
      >
        <span className="material-symbols-outlined">menu</span>
      </button>

      {/* Search */}
      <div className="flex-1 max-w-lg">
        <div className="flex items-center gap-2 bg-primary/5 border border-primary/10 rounded-lg px-3 py-2">
          <span className="material-symbols-outlined text-ink/30 text-lg">search</span>
          <input
            type="text"
            placeholder="Search cases, drafts, contacts…"
            className="flex-1 bg-transparent text-sm text-ink placeholder:text-ink/30 outline-none"
          />
          <span className="text-xs text-ink/20 font-mono hidden sm:block">⌘K</span>
        </div>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2 ml-auto">
        {/* Quick draft */}
        <button
          className="hidden md:flex items-center gap-1.5 btn-primary text-xs px-3 py-2"
          onClick={() => navigate('/drafting')}
        >
          <span className="material-symbols-outlined text-sm">add</span>
          New Draft
        </button>

        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-primary/5 text-ink/40 hover:text-primary transition-colors">
          <span className="material-symbols-outlined text-xl">notifications</span>
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-primary"></span>
        </button>

        {/* Help */}
        <button className="p-2 rounded-lg hover:bg-primary/5 text-ink/40 hover:text-primary transition-colors">
          <span className="material-symbols-outlined text-xl">help_outline</span>
        </button>
      </div>
    </header>
  );
}
