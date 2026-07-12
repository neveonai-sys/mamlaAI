import React from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import MamlaLogoIcon from '../common/MamlaLogoIcon';
import { useSelector, useDispatch } from 'react-redux';
import { clearUser } from '../../features/userSlice';
import apiClient from '../../services/api';
import { NATIVE_TOKEN_KEY } from '../../services/api';
import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';
import clsx from 'clsx';

// ─── Navigation items ────────────────────────────────────────────────────────
const LAWYER_NAV = [
  { label: 'Dashboard',          path: '/dashboard',      icon: 'dashboard' },
  { label: 'Cases',              path: '/cases',          icon: 'folder_open' },
  { label: 'AI Drafting',        path: '/drafting',       icon: 'edit_note' },
  { label: 'Document Intel',     path: '/documents',      icon: 'description' },
  { label: 'Calendar & Events',  path: '/calendar',       icon: 'calendar_month' },
  // { label: 'Court Updates',      path: '/court-updates',  icon: 'account_balance' },
  { label: 'eCourts',            path: '/ecourts',        icon: 'search' },
  { label: 'Citation Search',    path: '/citations',      icon: 'gavel' },
  // Clients nav removed — onboarding now inline in Case creation
  // { label: 'Clients',            path: '/clients',        icon: 'people' },
  // { label: 'Sessions',           path: '/sessions',       icon: 'forum' },
  { label: 'Feedback',           path: '/feedback',       icon: 'rate_review' },
];

const CLIENT_NAV = [
  { label: 'Dashboard',          path: '/dashboard',      icon: 'dashboard' },
  { label: 'My Case',            path: '/my-case',        icon: 'folder_open' },
  { label: 'Document Intel',     path: '/documents',      icon: 'description' },
  { label: 'Calendar & Events',  path: '/calendar',       icon: 'calendar_month' },
  // { label: 'Sessions',           path: '/sessions',       icon: 'forum' },
  { label: 'Feedback',           path: '/feedback',       icon: 'rate_review' },
];

const OWNER_EXTRA = [
  { label: 'Analytics',          path: '/owner-dashboard', icon: 'monitoring' },
];

const ADMIN_EMAILS = (process.env.REACT_APP_ADMIN_EMAILS || '')
  .split(',').map((e) => e.trim()).filter(Boolean);

function navItems(userType, email) {
  if (userType === 'Client') return CLIENT_NAV;
  const isOwner = userType === 'owner' || userType === 'admin' || userType === 'Owner' || userType === 'Admin'
    || ADMIN_EMAILS.includes(email);
  return isOwner ? [...LAWYER_NAV, ...OWNER_EXTRA] : LAWYER_NAV;
}

export default function Sidebar({ collapsed, onToggleCollapse }) {
  const { firstname, lastname, user_type, email } = useSelector((s) => s.user);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();

  const links = navItems(user_type, email);

  async function handleSignOut() {
    try {
      await apiClient.post('users/sign-out-user/', { scope: 'local' });
    } catch (_) { /* ignore — cookie will be cleared by backend */ }
    if (Capacitor.isNativePlatform()) {
      await Preferences.remove({ key: NATIVE_TOKEN_KEY });
    }
    dispatch(clearUser());
    navigate('/login', { replace: true });
  }

  const initials = `${firstname?.[0] ?? ''}${lastname?.[0] ?? ''}`.toUpperCase() || 'U';

  return (
    <aside
      className={clsx(
        'flex flex-col h-screen flex-shrink-0 border-r border-white/10 bg-background-dark text-white transition-all duration-200 z-20 shadow-elevated',
        collapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* ── Logo ────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 h-16 border-b border-white/10 flex-shrink-0">
        {!collapsed && (
          <Link to="/dashboard" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5">
              <MamlaLogoIcon dark size={32} />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-primary-soft/82">Litigation OS</p>
              <span className="text-lg font-semibold tracking-tight text-white">
                Mamla<span className="text-primary-soft">.AI</span>
              </span>
            </div>
          </Link>
        )}
        {collapsed && (
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5">
            <MamlaLogoIcon dark size={32} />
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="ml-auto rounded-md p-1 text-white/65 transition-colors hover:bg-white/10 hover:text-white"
          aria-label="Toggle sidebar"
        >
          <span className="material-symbols-outlined text-lg">
            {collapsed ? 'chevron_right' : 'chevron_left'}
          </span>
        </button>
      </div>

      {!collapsed && (
        <div className="border-b border-white/10 px-4 py-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-primary-soft/82">Supreme-ready workspace</p>
            <p className="mt-2 text-sm font-medium leading-6 text-white/90">
              Draft, track, and review matters in a calmer navy shell built for chamber work.
            </p>
          </div>
        </div>
      )}

      {/* ── Nav links ───────────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto custom-scrollbar py-3">
        {links.map((item) => {
          const active = location.pathname.startsWith(item.path);
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={clsx(
                'mx-2 flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition-all',
                active
                  ? 'sidebar-active'
                  : 'text-white/88 hover:bg-white/8 hover:text-white',
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
      <div className="border-t border-white/10 p-3 flex-shrink-0">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-primary-dark text-xs font-bold flex-shrink-0">
              {initials}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">
                  {firstname} {lastname}
                </p>
                <p className="text-xs font-medium text-white/72 truncate">
                  {user_type === 'Client' ? 'Nagrik (Citizen)' : user_type}
                </p>
              </div>
            )}
            {!collapsed && (
              <button
                onClick={handleSignOut}
                className="rounded-md p-1 text-white/65 transition-colors hover:bg-white/10 hover:text-red-300"
                title="Sign out"
              >
                <span className="material-symbols-outlined text-lg">logout</span>
              </button>
            )}
          </div>
          {collapsed && (
            <button
              onClick={handleSignOut}
              className="mt-3 flex w-full justify-center rounded-md p-1 text-white/65 transition-colors hover:bg-white/10 hover:text-red-300"
              title="Sign out"
            >
              <span className="material-symbols-outlined text-lg">logout</span>
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
