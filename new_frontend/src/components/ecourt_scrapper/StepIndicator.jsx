/**
 * StepIndicator — displays real-time scraper progress as an inline stepper.
 *
 * Props:
 *   currentStep  string|null  — the `agent_state` value from the polled job doc
 *                                (e.g. "navigate", "solve_captcha", "parse").
 *                                Pass null/undefined to hide completely.
 *
 * The happy-path steps are shown in order; error/recovery steps are shown as a
 * separate amber status pill so the linear flow isn't broken.
 *
 * Usage:
 *   <StepIndicator currentStep={agentStep} />
 */
import React from 'react';

// Ordered main-path steps (label shown in stepper)
const MAIN_STEPS = [
  { key: 'classify',       label: 'Classify'    },
  { key: 'resolve_court',  label: 'Court type'  },
  { key: 'check_cache',    label: 'Cache'       },
  { key: 'acquire_browser',label: 'Browser'     },
  { key: 'navigate',       label: 'Navigate'    },
  { key: 'solve_captcha',  label: 'CAPTCHA'     },
  { key: 'fill_form',      label: 'Form'        },
  { key: 'submit',         label: 'Submit'      },
  { key: 'parse',          label: 'Parse'       },
  { key: 'finalize',       label: 'Done'        },
];

// Steps that mean "recovering" — shown separately so as not to confuse the linear flow
const RECOVERY_STEPS = new Set([
  'error_handler', 'self_heal', 'refresh_captcha',
]);

export default function StepIndicator({ currentStep }) {
  if (!currentStep) return null;

  const isRecovery = RECOVERY_STEPS.has(currentStep);
  const activeIndex = MAIN_STEPS.findIndex((s) => s.key === currentStep);

  // Determine per-step state: 'done' | 'active' | 'pending'
  function stepState(index) {
    if (isRecovery) return index < MAIN_STEPS.length - 1 ? 'done' : 'pending';
    if (index < activeIndex) return 'done';
    if (index === activeIndex) return 'active';
    return 'pending';
  }

  return (
    <div className="mt-4 rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
      <p className="mb-3 text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">
        Scraper progress
      </p>

      {/* Horizontal step list */}
      <div className="flex flex-wrap items-center gap-x-0 gap-y-2">
        {MAIN_STEPS.map((step, index) => {
          const state = stepState(index);
          const isLast = index === MAIN_STEPS.length - 1;

          return (
            <React.Fragment key={step.key}>
              <div className="flex flex-col items-center">
                {/* Circle */}
                <div
                  className={[
                    'flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-black transition-all',
                    state === 'done'
                      ? 'bg-primary text-white'
                      : state === 'active'
                        ? 'animate-pulse border-2 border-primary bg-primary/10 text-primary'
                        : 'border border-slate-200 bg-white text-slate-300',
                  ].join(' ')}
                >
                  {state === 'done' ? '✓' : index + 1}
                </div>
                {/* Label */}
                <span
                  className={[
                    'mt-1 text-[9px] font-bold uppercase tracking-[0.14em]',
                    state === 'done'
                      ? 'text-primary'
                      : state === 'active'
                        ? 'text-primary font-black'
                        : 'text-slate-300',
                  ].join(' ')}
                >
                  {step.label}
                </span>
              </div>
              {/* Connector line */}
              {!isLast && (
                <div
                  className={[
                    'mb-4 h-px flex-1 min-w-[12px]',
                    state === 'done' ? 'bg-primary/40' : 'bg-slate-200',
                  ].join(' ')}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Recovery pill */}
      {isRecovery && (
        <div className="mt-3 flex items-center gap-2 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2">
          <span className="text-[10px] font-black uppercase tracking-[0.18em] text-amber-700">
            {currentStep === 'error_handler' && 'Handling error…'}
            {currentStep === 'self_heal' && 'Attempting self-repair…'}
            {currentStep === 'refresh_captcha' && 'Refreshing CAPTCHA…'}
          </span>
        </div>
      )}
    </div>
  );
}
