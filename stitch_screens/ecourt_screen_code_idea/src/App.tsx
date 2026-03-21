/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import CNRSearch from './components/SearchForms/CNRSearch';
import CaseStatusSearch from './components/SearchForms/CaseStatusSearch';
import CourtOrdersSearch from './components/SearchForms/CourtOrdersSearch';
import CauseListSearch from './components/SearchForms/CauseListSearch';
import CaveatSearch from './components/SearchForms/CaveatSearch';
import { Screen } from './types';

export default function App() {
  const [activeScreen, setActiveScreen] = useState<Screen>('CASE_STATUS');

  const renderScreen = () => {
    switch (activeScreen) {
      case 'CNR':
        return <CNRSearch />;
      case 'CASE_STATUS':
        return <CaseStatusSearch />;
      case 'COURT_ORDERS':
        return <CourtOrdersSearch />;
      case 'CAUSE_LIST':
        return <CauseListSearch />;
      case 'CAVEAT':
        return <CaveatSearch />;
      case 'DASHBOARD':
        return (
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            <h2 className="text-4xl font-serif font-bold mb-4">Welcome back, John</h2>
            <p className="text-gray-500 max-w-md">Select a search module from the sidebar to begin your legal workflow.</p>
          </div>
        );
      default:
        return (
          <div className="p-10 text-center">
            <h2 className="text-2xl font-serif font-bold">Screen Under Development</h2>
            <p className="text-gray-500">This feature will be available soon.</p>
          </div>
        );
    }
  };

  const getTitle = () => {
    switch (activeScreen) {
      case 'CNR': return 'CNR Number Search';
      case 'CASE_STATUS': return 'Case Status Inquiry';
      case 'COURT_ORDERS': return 'Court Orders Terminal';
      case 'CAUSE_LIST': return 'Cause List Search';
      case 'CAVEAT': return 'Caveat Search Portal';
      default: return activeScreen.charAt(0) + activeScreen.slice(1).toLowerCase().replace('_', ' ');
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-legal-cream">
      <Sidebar activeScreen={activeScreen} onNavigate={setActiveScreen} />
      
      <div className="flex-1 flex flex-col min-w-0">
        <Header title={getTitle()} />
        
        <main className="flex-1 overflow-y-auto p-8 lg:p-12">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeScreen}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {renderScreen()}
            </motion.div>
          </AnimatePresence>
        </main>
        
        <footer className="h-12 bg-legal-blue text-white/50 text-[10px] flex items-center justify-center gap-6 px-8 shrink-0 uppercase tracking-widest">
          <span>© 2024 Mamla.AI. All Rights Reserved.</span>
          <div className="flex gap-4">
            <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-white transition-colors">Contact Us</a>
          </div>
        </footer>
      </div>
    </div>
  );
}
