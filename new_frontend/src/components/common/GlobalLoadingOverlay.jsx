import React, { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';

export default function GlobalLoadingOverlay() {
  const { blockingCount, message } = useSelector((state) => state.ui);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (blockingCount > 0) {
      const timer = window.setTimeout(() => setVisible(true), 120);
      return () => window.clearTimeout(timer);
    }
    setVisible(false);
    return undefined;
  }, [blockingCount]);

  const active = visible && blockingCount > 0;

  // Always rendered — CSS visibility toggle avoids the reflow caused by mount/unmount.
  return (
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center bg-background-dark/45 backdrop-blur-sm transition-opacity duration-150"
      style={{ visibility: active ? 'visible' : 'hidden', opacity: active ? 1 : 0 }}
      aria-hidden={!active}
    >
      <div className="mx-4 flex w-full max-w-sm flex-col items-center rounded-[1.75rem] border border-white/10 bg-background-dark px-8 py-7 text-center text-white shadow-elevated">
        <div className="flex size-14 items-center justify-center rounded-full border border-white/10 bg-white/6">
          <span className="material-symbols-outlined animate-spin text-3xl text-primary-soft">progress_activity</span>
        </div>
        <p className="mt-5 text-[11px] font-semibold uppercase tracking-[0.22em] text-primary-soft/84">Mamla.AI</p>
        <h2 className="mt-2 font-display text-3xl font-semibold text-white">Please wait</h2>
        <p className="mt-3 text-sm font-medium leading-6 text-white/78">{message}</p>
      </div>
    </div>
  );
}
