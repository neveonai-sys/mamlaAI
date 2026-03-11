import React, { useEffect, useState } from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { clearUser } from '../../features/userSlice';
import apiClient from '../../services/api';
import clsx from 'clsx';

// ─── Navigation items ────────────────────────────────────────────────────────
const LAWYER_NAV = [
  { label: 'Dashboard',          path: '/dashboard',      icon: 'dashboard' },
  { label: 'Command Center',     path: '/command-center', icon: 'gavel' },
  { label: 'AI Drafting',        path: '/drafting',       icon: 'edit_note' },
  { label: 'Document Intel',     path: '/documents',      icon: 'description' },
  { label: 'Calendar & Events',  path: '/calendar',       icon: 'calendar_month' },
  { label: 'Court Updates',      path: '/court-updates',  icon: 'account_balance' },
  { label: 'eCourts',            path: '/ecourts',        icon: 'search' },
  { label: 'Clients',            path: '/clients',        icon: 'people' },
  { label: 'Sessions',           path: '/sessions',       icon: 'forum' },
  { label: 'Feedback',           path: '/feedback',       icon: 'rate_review' },
];

const CLIENT_NAV = [
  { label: 'Dashboard',          path: '/dashboard',      icon: 'dashboard' },
  { label: 'Document Intel',     path: '/documents',      icon: 'description' },
  { label: 'Calendar & Events',  path: '/calendar',       icon: 'calendar_month' },
  { label: 'Sessions',           path: '/sessions',       icon: 'forum' },
  { label: 'Feedback',           path: '/feedback',       icon: 'rate_review' },
];

function navItems(userType) {
  if (userType === 'Client') return CLIENT_NAV;
  return LAWYER_NAV;
}

export default function Sidebar({ collapsed, onToggleCollapse }) {
  const [expanded, setExpanded] = useState(false);
  const { firstname, lastname, user_type } = useSelector((s) => s.user);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();

  const links = navItems(user_type);

  async function handleSignOut() {
    try {
      await apiClient.post('users/sign-out-user/', { scope: 'local' });
    } catch (_) { /* ignore — cookie will be cleared by backend */ }
    dispatch(clearUser());
    navigate('/login', { replace: true });
  }

  const initials = `${firstname?.[0] ?? ''}${lastname?.[0] ?? ''}`.toUpperCase() || 'U';

  return (
    <aside
      className={clsx(
        'flex flex-col bg-ivory border-r border-primary/10 h-screen flex-shrink-0 transition-all duration-200 z-20',
        collapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* ── Logo ────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 h-16 border-b border-primary/10 flex-shrink-0">
        {!collapsed && (
          <Link to="/dashboard" className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-2xl icon-filled">gavel</span>
            <span className="font-bold text-lg text-ink">
              Mamla<span className="text-primary">.AI</span>
            </span>
          </Link>
        )}
        {collapsed && (
          <span className="material-symbols-outlined text-primary text-2xl icon-filled mx-auto">gavel</span>
        )}
        <button
          onClick={onToggleCollapse}
          className="ml-auto p-1 rounded-md hover:bg-primary/5 text-ink/40 hover:text-primary transition-colors"
          aria-label="Toggle sidebar"
        >
          <span className="material-symbols-outlined text-lg">
            {collapsed ? 'chevron_right' : 'chevron_left'}
          </span>
        </button>
      </div>

      {/* ── Nav links ───────────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto custom-scrollbar py-3">
        {links.map((item) => {
          const active = location.pathname.startsWith(item.path);
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={clsx(
                'flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-all',
                active
                  ? 'sidebar-active'
                  : 'text-ink/60 hover:bg-primary/5 hover:text-ink',
              )}
              title={collapsed ? item.label : undefined}
            >
              <span
                className={clsx(
                  'material-symbols-outlined text-xl flex-shrink-0',
                  active ? 'icon-filled' : '',
                )}
              >
                {item.icon}
              </span>
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* ── User footer ─────────────────────────────────────────────────── */}
      <div className="border-t border-primary/10 p-3 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-primary text-ivory flex items-center justify-center text-xs font-bold flex-shrink-0">
            {initials}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-ink truncate">
                {firstname} {lastname}
              </p>
              <p className="text-xs text-ink/50 truncate">{user_type}</p>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={handleSignOut}
              className="p-1 rounded-md hover:bg-primary/5 text-ink/40 hover:text-red-500 transition-colors"
              title="Sign out"
            >
              <span className="material-symbols-outlined text-lg">logout</span>
            </button>
          )}
        </div>
        {collapsed && (
          <button
            onClick={handleSignOut}
            className="w-full mt-2 flex justify-center p-1 rounded-md hover:bg-primary/5 text-ink/40 hover:text-red-500 transition-colors"
            title="Sign out"
          >
            <span className="material-symbols-outlined text-lg">logout</span>
          </button>
        )}
      </div>
    </aside>
  );
}
