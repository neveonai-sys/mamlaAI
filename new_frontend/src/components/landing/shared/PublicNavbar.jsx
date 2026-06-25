import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import MamlaLogoIcon from '../../common/MamlaLogoIcon';
import NavDropdown from './NavDropdown';
import { PRODUCT_ITEMS, SOLUTION_ITEMS, RESOURCE_ITEMS } from './navConfig';

// Shared light, white, sticky top navigation used across the landing page and
// every public hub page. Dropdown / menu items route to dedicated pages so the
// whole product is discoverable from anywhere.
export default function PublicNavbar() {
  const [scrolled, setScrolled] = useState(false);
  const [openDD, setOpenDD] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mobileAcc, setMobileAcc] = useState(null);

  useEffect(() => {
    function onScroll() { setScrolled(window.scrollY > 8); }
    window.addEventListener('scroll', onScroll);
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    function onResize() { if (window.innerWidth >= 768) setMobileOpen(false); }
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const closeDD = () => setOpenDD(null);

  return (
    <nav className={`sticky top-0 z-[100] border-b bg-white transition-shadow ${scrolled ? 'border-slate-200 shadow-sm' : 'border-slate-100'}`}>
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">

        {/* Logo */}
        <Link to="/" className="flex flex-shrink-0 items-center gap-2">
          <MamlaLogoIcon size={34} />
          <span className="text-xl font-bold tracking-tight text-ink">Mamla.ai</span>
        </Link>

        {/* Desktop nav items */}
        <div className="hidden items-center gap-1 md:flex">
          <NavDropdown label="Product" items={PRODUCT_ITEMS} isOpen={openDD === 'product'} onToggle={() => setOpenDD(openDD === 'product' ? null : 'product')} onClose={closeDD} />
          <NavDropdown label="Solutions" items={SOLUTION_ITEMS} isOpen={openDD === 'solutions'} onToggle={() => setOpenDD(openDD === 'solutions' ? null : 'solutions')} onClose={closeDD} />
          <Link to="/pricing" className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:text-primary">Pricing</Link>
          <NavDropdown label="Resources" items={RESOURCE_ITEMS} isOpen={openDD === 'resources'} onToggle={() => setOpenDD(openDD === 'resources' ? null : 'resources')} onClose={closeDD} />
          <Link to="/about" className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:text-primary">About</Link>
        </div>

        {/* Right: auth + burger */}
        <div className="flex items-center gap-3">
          <Link to="/login" className="hidden px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:text-primary sm:block">Sign in</Link>
          <Link to="/signup" className="rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-primary-dark">
            Sign Up / Register
          </Link>
          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-700 md:hidden"
            aria-label="Toggle navigation"
          >
            <span className="material-symbols-outlined text-xl">{mobileOpen ? 'close' : 'menu'}</span>
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="app-fade-in fixed inset-0 top-20 z-[99] overflow-y-auto bg-white px-6 py-6 md:hidden">
          {[
            { key: 'product',   label: 'Product',   items: PRODUCT_ITEMS },
            { key: 'solutions', label: 'Solutions', items: SOLUTION_ITEMS },
            { key: 'resources', label: 'Resources', items: RESOURCE_ITEMS },
          ].map((group) => (
            <div key={group.key} className="border-b border-slate-100">
              <button
                type="button"
                onClick={() => setMobileAcc(mobileAcc === group.key ? null : group.key)}
                className="flex w-full items-center justify-between py-4 text-base font-semibold text-ink"
              >
                {group.label}
                <span className={`material-symbols-outlined text-slate-400 transition-transform duration-200 ${mobileAcc === group.key ? 'rotate-180' : ''}`}>
                  expand_more
                </span>
              </button>
              {mobileAcc === group.key && (
                <div className="pb-4 pl-3">
                  {group.items.map((item) => {
                    const inner = (
                      <>
                        <span className="material-symbols-outlined text-base text-primary">{item.icon}</span>
                        {item.label}
                      </>
                    );
                    const cls = 'flex items-center gap-3 py-3 text-sm text-slate-600';
                    return item.href ? (
                      <a key={item.label} href={item.href} target="_blank" rel="noopener noreferrer" onClick={() => setMobileOpen(false)} className={cls}>
                        {inner}
                      </a>
                    ) : (
                      <Link key={item.label} to={item.to} onClick={() => setMobileOpen(false)} className={cls}>
                        {inner}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
          {[{ label: 'Pricing', to: '/pricing' }, { label: 'About', to: '/about' }].map((item) => (
            <Link key={item.label} to={item.to} onClick={() => setMobileOpen(false)} className="block border-b border-slate-100 py-4 text-base font-semibold text-ink">
              {item.label}
            </Link>
          ))}
          <div className="mt-7 flex flex-col gap-3">
            <Link to="/login" onClick={() => setMobileOpen(false)} className="block rounded-xl border border-slate-200 py-3.5 text-center text-sm font-semibold text-ink">
              Sign in
            </Link>
            <Link to="/signup" onClick={() => setMobileOpen(false)} className="block rounded-xl bg-primary py-3.5 text-center text-sm font-bold text-white">
              Sign Up / Register
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
