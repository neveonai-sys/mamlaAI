import React, { useId } from 'react';

/**
 * MamlaLogoIcon — Courthouse-M icon only (square viewport, no wordmark).
 *
 * Props:
 *   dark    {boolean}  — true for dark sidebar/nav backgrounds (lightens pillar/arch colours)
 *   size    {number}   — rendered px size (square). default 40
 *   className {string} — extra classes forwarded to <svg>
 */
export default function MamlaLogoIcon({ dark = false, size = 40, className = '' }) {
  const uid = useId().replace(/:/g, '_');

  // ── Colour tokens ──────────────────────────────────────────────────────────
  const navyA   = dark ? '#D8E3F2' : '#1a3a6b';
  const navyB   = dark ? '#BCCFE8' : '#0f2544';
  const pillarA = dark ? '#4A79BF' : '#1e4d8c';
  const pillarM = dark ? '#5A8FD4' : '#2a5aad';
  const pillarB = dark ? '#3A6BAF' : '#1a3a6b';
  const fluteC  = dark ? 'rgba(255,255,255,0.22)' : '#2a5aad';

  const ng  = `url(#${uid}ng)`;
  const ngh = `url(#${uid}ngh)`;
  const sg  = `url(#${uid}sg)`;
  const pg  = `url(#${uid}pg)`;
  const glow = `url(#${uid}glow)`;
  const soft = `url(#${uid}soft)`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 128 128"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Mamla.AI logo"
    >
      <defs>
        {/* Navy gradients */}
        <linearGradient id={`${uid}ng`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   style={{ stopColor: navyA }} />
          <stop offset="100%" style={{ stopColor: navyB }} />
        </linearGradient>
        <linearGradient id={`${uid}ngh`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   style={{ stopColor: navyA }} />
          <stop offset="100%" style={{ stopColor: navyB }} />
        </linearGradient>

        {/* Saffron gradient */}
        <linearGradient id={`${uid}sg`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   style={{ stopColor: '#FF9800' }} />
          <stop offset="100%" style={{ stopColor: '#FFB74D' }} />
        </linearGradient>

        {/* Pillar gradient */}
        <linearGradient id={`${uid}pg`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   style={{ stopColor: pillarA }} />
          <stop offset="50%"  style={{ stopColor: pillarM }} />
          <stop offset="100%" style={{ stopColor: pillarB }} />
        </linearGradient>

        {/* Glow filters */}
        <filter id={`${uid}glow`} x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="2" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id={`${uid}soft`} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="1.2" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* ── Courthouse content (same translate as full logo icon group) ─── */}
      <g transform="translate(10, 8)">

        {/* Dome arch */}
        <path d="M14,52 Q14,10 52,10 Q90,10 90,52"
          fill="none" stroke={ng} strokeWidth="4" strokeLinecap="round"
          filter={glow} />
        <path d="M22,52 Q22,20 52,20 Q82,20 82,52"
          fill="none" stroke="#FF9800" strokeWidth="1.2" strokeLinecap="round"
          opacity="0.5" />

        {/* Finial */}
        <circle cx="52" cy="8" r="4" fill={sg} filter={soft} />
        <circle cx="52" cy="8" r="2" fill="#fff" opacity="0.85" />
        <line x1="52" y1="4" x2="52" y2="0"
          stroke={sg} strokeWidth="2" strokeLinecap="round" />

        {/* Left pillar */}
        <rect x="10" y="48" width="18" height="5" rx="1.5" fill={pg} />
        <rect x="13" y="53" width="12" height="44" rx="1"   fill={pg} />
        <line x1="16" y1="55" x2="16" y2="95" stroke={fluteC} strokeWidth="0.7" opacity="0.5" />
        <line x1="19" y1="55" x2="19" y2="95" stroke={fluteC} strokeWidth="0.7" opacity="0.5" />
        <line x1="22" y1="55" x2="22" y2="95" stroke={fluteC} strokeWidth="0.7" opacity="0.5" />
        <rect x="10" y="95" width="18" height="5" rx="1.5" fill={sg} filter={soft} />

        {/* Right pillar */}
        <rect x="76" y="48" width="18" height="5" rx="1.5" fill={pg} />
        <rect x="79" y="53" width="12" height="44" rx="1"   fill={pg} />
        <line x1="82" y1="55" x2="82" y2="95" stroke={fluteC} strokeWidth="0.7" opacity="0.5" />
        <line x1="85" y1="55" x2="85" y2="95" stroke={fluteC} strokeWidth="0.7" opacity="0.5" />
        <line x1="88" y1="55" x2="88" y2="95" stroke={fluteC} strokeWidth="0.7" opacity="0.5" />
        <rect x="76" y="95" width="18" height="5" rx="1.5" fill={sg} filter={soft} />

        {/* M diagonals */}
        <line x1="19" y1="53" x2="52" y2="80"
          stroke={ng} strokeWidth="4.5" strokeLinecap="round" filter={glow} />
        <line x1="85" y1="53" x2="52" y2="80"
          stroke={ng} strokeWidth="4.5" strokeLinecap="round" filter={glow} />

        {/* Steps */}
        <rect x="4"  y="100" width="96"  height="3.5" rx="1.5" fill={ngh} opacity="0.8" />
        <rect x="0"  y="104" width="104" height="3"   rx="1.5" fill={sg}  opacity="0.6" filter={soft} />
        <rect x="-4" y="107" width="112" height="2.5" rx="1"   fill={ngh} opacity="0.3" />

        {/* Neural center node */}
        <circle cx="52" cy="80" r="4.5" fill={ng} stroke="#FF9800" strokeWidth="1.5" filter={soft} />
        <circle cx="52" cy="80" r="2"   fill="#FF9800" opacity="0.9" />
        <circle cx="52" cy="80" r="0.8" fill="#fff"    opacity="0.85" />

        {/* Neural sparks */}
        <line x1="52" y1="75" x2="52" y2="68"
          stroke="#FF9800" strokeWidth="1" opacity="0.5"
          strokeLinecap="round" strokeDasharray="2,2" />
        <line x1="48" y1="78" x2="40" y2="73"
          stroke="#FF9800" strokeWidth="1" opacity="0.4"
          strokeLinecap="round" strokeDasharray="2,2" />
        <line x1="56" y1="78" x2="64" y2="73"
          stroke="#FF9800" strokeWidth="1" opacity="0.4"
          strokeLinecap="round" strokeDasharray="2,2" />

        {/* Spark nodes */}
        <circle cx="52" cy="67" r="2"   fill="#FF9800" opacity="0.7" filter={soft} />
        <circle cx="39" cy="72" r="1.8" fill="#FFB74D" opacity="0.6" filter={soft} />
        <circle cx="65" cy="72" r="1.8" fill="#FFB74D" opacity="0.6" filter={soft} />

        {/* Pillar top AI nodes */}
        <circle cx="19" cy="50" r="3" fill={ng} stroke="#FF9800" strokeWidth="1.2" opacity="0.7" />
        <circle cx="19" cy="50" r="1.2" fill="#FF9800" opacity="0.8" />
        <circle cx="85" cy="50" r="3" fill={ng} stroke="#FF9800" strokeWidth="1.2" opacity="0.7" />
        <circle cx="85" cy="50" r="1.2" fill="#FF9800" opacity="0.8" />

        {/* Neural arc */}
        <path d="M22,50 Q52,35 82,50"
          fill="none" stroke="#FF9800" strokeWidth="0.8"
          opacity="0.25" strokeDasharray="3,3" />

      </g>
    </svg>
  );
}
