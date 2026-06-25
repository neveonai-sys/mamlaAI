import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

// Desktop dropdown menu used in the (light) public navbar. Items may be
// internal (`to`) react-router links or external (`href`) anchors.
export default function NavDropdown({ label, items, isOpen, onToggle, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!isOpen) return;
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen, onClose]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={onToggle}
        className={`flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          isOpen ? 'text-primary' : 'text-slate-600 hover:text-primary'
        }`}
      >
        {label}
        <span className={`material-symbols-outlined text-base transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}>
          expand_more
        </span>
      </button>

      {isOpen && (
        <div className="app-fade-in absolute left-0 top-[calc(100%+8px)] z-[200] w-[min(280px,calc(100vw-2rem))] rounded-2xl border border-slate-200 bg-white p-2 shadow-elevated" style={{ maxWidth: 'calc(100vw - 1rem)' }}>
          {items.map((item) => {
            const inner = (
              <>
                <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-slate-100">
                  <span className="material-symbols-outlined text-base text-primary">{item.icon}</span>
                </span>
                <div>
                  <div className="text-[13.5px] font-semibold text-ink">{item.label}</div>
                  {item.desc && <div className="mt-0.5 text-[11px] text-slate-400">{item.desc}</div>}
                </div>
              </>
            );
            const cls = 'flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-slate-50';
            return item.href ? (
              <a key={item.label} href={item.href} target="_blank" rel="noopener noreferrer" onClick={onClose} className={cls}>
                {inner}
              </a>
            ) : (
              <Link key={item.label} to={item.to} onClick={onClose} className={cls}>
                {inner}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
