import React, { useState } from 'react';
import Captcha from '../Captcha';
import HowTo from '../HowTo';
import ResultsTable from '../ResultsTable';
import { Search, RotateCcw, HelpCircle, Info } from 'lucide-react';

export default function CNRSearch() {
  const [showResults, setShowResults] = useState(false);

  const mockResults = [
    { srNo: 1, caseNumber: "MHAU01-001234-2015", partyName: "State of Maharashtra vs John Doe", status: "Pending", date: "20-03-2026" },
    { srNo: 2, caseNumber: "MHAU01-005678-2018", partyName: "Jane Smith vs Municipal Corp", status: "Disposed", date: "15-01-2024" },
  ];

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      {/* Header Section */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-legal-blue rounded-xl flex items-center justify-center text-white shadow-lg shadow-legal-blue/20">
            <Search className="w-5 h-5" />
          </div>
          <h2 className="text-3xl font-serif font-bold text-gray-900">Search by CNR Number</h2>
        </div>
        <p className="text-gray-500 ml-13">Enter your 16-digit CNR Number to get instant case details</p>
      </div>

      {/* Search Card */}
      <div className="bg-white rounded-3xl shadow-2xl shadow-gray-200/50 border border-gray-100 overflow-hidden mb-10">
        <div className="p-8 md:p-12">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            {/* Left Column: Input */}
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider flex items-center gap-2">
                  CNR Number <span className="text-red-500">*</span>
                  <Info className="w-4 h-4 text-gray-400 cursor-help" />
                </label>
                <div className="relative group">
                  <input 
                    type="text" 
                    placeholder="e.g., MHAU019999992015"
                    className="w-full border-2 border-gray-100 bg-gray-50/50 rounded-2xl px-6 py-5 text-xl focus:border-legal-blue focus:bg-white focus:ring-8 focus:ring-legal-blue/5 outline-none transition-all font-mono placeholder:text-gray-300"
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-gray-400 bg-white px-2 py-1 rounded border border-gray-100">
                    16 DIGITS
                  </div>
                </div>
                <p className="mt-3 text-xs text-gray-400 italic">
                  Example: MHAU019999992015 (No spaces or hyphens)
                </p>
              </div>
            </div>

            {/* Right Column: Captcha & Actions */}
            <div className="space-y-8">
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Verification</label>
                <div className="bg-gray-50/50 p-4 rounded-2xl border border-gray-100">
                  <Captcha />
                </div>
              </div>

              <div className="flex gap-4">
                <button 
                  onClick={() => setShowResults(true)}
                  className="flex-1 bg-legal-blue text-white px-8 py-5 rounded-2xl font-bold hover:bg-legal-blue/90 transition-all shadow-xl shadow-legal-blue/20 flex items-center justify-center gap-2 group active:scale-95"
                >
                  <Search className="w-5 h-5 group-hover:scale-110 transition-transform" />
                  Search Case
                </button>
                <button 
                  onClick={() => setShowResults(false)}
                  className="bg-gray-900 text-white px-8 py-5 rounded-2xl font-bold hover:bg-black transition-all flex items-center justify-center gap-2 active:scale-95"
                >
                  <RotateCcw className="w-5 h-5" />
                  Reset
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Info */}
        <div className="bg-gray-50 border-t border-gray-100 px-8 py-4 flex items-center gap-2 text-xs text-gray-500">
          <HelpCircle className="w-4 h-4" />
          <span>If you don't know the CNR number, you can search by Case Status, Court Orders, or Cause List.</span>
        </div>
      </div>

      {/* Results or HowTo */}
      {showResults ? (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-gray-900">Search Results</h3>
            <button 
              onClick={() => setShowResults(false)}
              className="text-sm font-bold text-legal-blue hover:underline"
            >
              Clear Results
            </button>
          </div>
          <ResultsTable results={mockResults} />
        </div>
      ) : (
        <HowTo steps={[
          "Locate your 16-digit CNR number on your case documents.",
          "Enter the alphanumeric CNR number without any spaces or hyphens.",
          "Complete the captcha verification for security.",
          "Click on 'Search Case' to view the current status and history."
        ]} />
      )}
    </div>
  );
}
