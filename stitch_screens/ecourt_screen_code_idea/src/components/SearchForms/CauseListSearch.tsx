import React, { useState } from 'react';
import { Calendar, Search, RotateCcw } from 'lucide-react';
import Captcha from '../Captcha';
import HowTo from '../HowTo';
import ResultsTable from '../ResultsTable';
import { CaseResult } from '../../types';

const mockResults: CaseResult[] = [
  { srNo: 1, caseNumber: 'WP(C) 12345/2023', partyName: 'State vs. John Doe & Ors', status: 'Pending' },
  { srNo: 2, caseNumber: 'CS(OS) 6789/2023', partyName: 'ABC Corp. vs. XYZ Ltd.', status: 'Disposed' },
  { srNo: 3, caseNumber: 'BAIL APPLN. 5432/2023', partyName: 'Rahul Gupta vs. State', status: 'Pending' },
  { srNo: 4, caseNumber: 'WP(C) 12345/2023', partyName: 'ABC Corp. vs. XYZ Ltd.', status: 'Pending' },
  { srNo: 5, caseNumber: 'CS(OS) 6789/2023', partyName: 'ABC Corp. vs. XYZ Ltd.', status: 'Disposed' },
];

export default function CauseListSearch() {
  const [showResults, setShowResults] = useState(false);

  const handleSearch = () => {
    setShowResults(true);
  };

  const handleReset = () => {
    setShowResults(false);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-0">
      {/* Top Selection Bar */}
      <div className="bg-[#2D2D2D] p-6 rounded-t-xl grid grid-cols-1 md:grid-cols-4 gap-6 mb-0">
        <div>
          <label className="block text-xs font-bold text-white uppercase tracking-wider mb-2">Select State</label>
          <select className="w-full bg-white border-none rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-legal-blue/50">
            <option>Bihar</option>
            <option>Gujarat</option>
            <option>Maharashtra</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-white uppercase tracking-wider mb-2">Select District</label>
          <select className="w-full bg-white border-none rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-legal-blue/50">
            <option>Aurangabad</option>
            <option>Ahmedabad</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-white uppercase tracking-wider mb-2">Select Court Complex</label>
          <select className="w-full bg-white border-none rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-legal-blue/50">
            <option>Sub divisional judicial court, Daudnagar</option>
            <option>Civil Court Complex, Aurangabad</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-white uppercase tracking-wider mb-2">Select Establishment</label>
          <select className="w-full bg-white border-none rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-legal-blue/50">
            <option>Select court establishment</option>
            <option>Civil Div. Aurangabad</option>
          </select>
        </div>
      </div>

      <div className="bg-white shadow-xl border-x border-gray-100 p-8 space-y-6">
        <p className="text-blue-700 text-xs italic border-b border-gray-100 pb-4">
          Cause list displayed may differ from the actual cause list. For further queries, contact court administrator.
        </p>

        <div className="space-y-8">
          <p className="text-red-600 text-xs italic">Fields marked with * are required</p>

          <div className="flex flex-wrap items-center gap-12">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                <span className="text-red-600 mr-1">*</span>Court Name
              </label>
              <select className="border border-gray-300 rounded px-3 py-2 text-sm w-72 focus:ring-1 focus:ring-legal-blue outline-none">
                <option>Select Court Name</option>
                <option>Court of DJ</option>
                <option>Court of ADJ</option>
              </select>
            </div>

            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                <span className="text-red-600 mr-1">*</span>Cause List Date
              </label>
              <div className="flex border border-gray-300 rounded overflow-hidden">
                <input 
                  type="text" 
                  defaultValue="21-03-2026"
                  className="px-3 py-2 text-sm w-48 outline-none"
                />
                <div className="bg-gray-100 px-3 flex items-center border-l border-gray-300">
                  <Calendar className="text-red-400 w-4 h-4" />
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-12">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-legal-blue">Captcha</label>
              <Captcha />
            </div>

            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                <span className="text-red-600 mr-1">*</span>Enter Captcha
              </label>
              <input 
                type="text" 
                placeholder="Enter Captcha"
                className="border border-gray-300 rounded px-3 py-2 text-sm w-48 focus:ring-1 focus:ring-legal-blue outline-none"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button 
              onClick={handleSearch}
              className="bg-legal-blue text-white px-12 py-2.5 rounded font-bold hover:bg-blue-900 transition-all shadow-sm"
            >
              Civil
            </button>
            <button 
              onClick={handleSearch}
              className="bg-legal-blue text-white px-12 py-2.5 rounded font-bold hover:bg-blue-900 transition-all shadow-sm"
            >
              Criminal
            </button>
          </div>
        </div>

        {showResults && (
          <div className="mt-12 pt-12 border-t border-gray-100 animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-serif font-bold text-legal-blue">Daily Cause List Preview</h3>
              <div className="flex gap-2">
                <button 
                  onClick={handleReset}
                  className="text-xs text-gray-500 hover:text-legal-blue flex items-center gap-1"
                >
                  <RotateCcw className="w-3 h-3" /> Clear Results
                </button>
              </div>
            </div>
            <ResultsTable results={mockResults} />
          </div>
        )}
      </div>

      {!showResults && (
        <HowTo steps={[
          "Select State, District, Court Complex and Establishment from the dropdowns",
          "Select the Court Name from the dropdown",
          "Select the Cause List Date",
          "Enter the captcha and click on Civil or Criminal button to view the cause list"
        ]} />
      )}
    </div>
  );
}
