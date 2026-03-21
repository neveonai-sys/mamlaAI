import React, { useState } from 'react';
import Captcha from '../Captcha';
import HowTo from '../HowTo';
import ResultsTable from '../ResultsTable';
import { Search, RotateCcw, ShieldCheck, MapPin, Building2, Gavel } from 'lucide-react';

export default function CaveatSearch() {
  const [showResults, setShowResults] = useState(false);
  const [searchType, setSearchType] = useState('anywhere');

  const mockResults = [
    { srNo: 1, caseNumber: "CAV/123/2026", partyName: "Reliance Ind vs Tata Motors", status: "Active", date: "10-03-2026" },
    { srNo: 2, caseNumber: "CAV/456/2026", partyName: "Adani Group vs SEBI", status: "Active", date: "12-03-2026" },
  ];

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      {/* Header Section */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-legal-blue rounded-xl flex items-center justify-center text-white shadow-lg shadow-legal-blue/20">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h2 className="text-3xl font-serif font-bold text-gray-900">Caveat Search Portal</h2>
        </div>
        <p className="text-gray-500 ml-13">Search for caveats filed in various courts across the country</p>
      </div>

      {/* Top Selection Bar */}
      <div className="bg-[#2D2D2D] p-6 rounded-t-3xl shadow-2xl flex flex-wrap gap-4 items-center border-b border-white/10">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
            <MapPin className="w-3 h-3" /> State
          </label>
          <select className="w-full bg-[#3D3D3D] text-white border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-legal-accent/50 outline-none transition-all appearance-none cursor-pointer hover:bg-[#4D4D4D]">
            <option>Select State</option>
            <option>Maharashtra</option>
            <option>Delhi</option>
            <option>Karnataka</option>
          </select>
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
            <MapPin className="w-3 h-3" /> District
          </label>
          <select className="w-full bg-[#3D3D3D] text-white border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-legal-accent/50 outline-none transition-all appearance-none cursor-pointer hover:bg-[#4D4D4D]">
            <option>Select District</option>
          </select>
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
            <Building2 className="w-3 h-3" /> Court Complex
          </label>
          <select className="w-full bg-[#3D3D3D] text-white border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-legal-accent/50 outline-none transition-all appearance-none cursor-pointer hover:bg-[#4D4D4D]">
            <option>Select Court Complex</option>
          </select>
        </div>
      </div>

      {/* Search Form Card */}
      <div className="bg-white p-8 md:p-10 rounded-b-3xl shadow-xl border-x border-b border-gray-100 mb-10">
        {/* Search Type Selector */}
        <div className="flex flex-wrap items-center gap-6 mb-10 p-4 bg-gray-50 rounded-2xl border border-gray-100">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-widest mr-2">Search Mode:</span>
          {[
            { id: 'anywhere', label: 'Anywhere' },
            { id: 'starting', label: 'Starting with' },
            { id: 'subordinate', label: 'Subordinate Court' },
            { id: 'number', label: 'Caveat Number' }
          ].map((type) => (
            <label key={type.id} className="flex items-center gap-2.5 cursor-pointer group">
              <div className="relative flex items-center justify-center">
                <input 
                  type="radio" 
                  name="searchType" 
                  className="peer sr-only"
                  checked={searchType === type.id}
                  onChange={() => setSearchType(type.id)}
                />
                <div className="w-5 h-5 border-2 border-gray-300 rounded-full peer-checked:border-legal-blue peer-checked:bg-legal-blue transition-all"></div>
                <div className="absolute w-2 h-2 bg-white rounded-full opacity-0 peer-checked:opacity-100 transition-opacity"></div>
              </div>
              <span className={`text-sm font-bold transition-colors ${searchType === type.id ? 'text-legal-blue' : 'text-gray-500 group-hover:text-gray-700'}`}>
                {type.label}
              </span>
            </label>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">Caveator Name</label>
              <input 
                type="text" 
                placeholder="Enter name of caveator"
                className="w-full border-2 border-gray-100 bg-gray-50/50 rounded-xl px-5 py-3.5 focus:border-legal-blue focus:bg-white focus:ring-4 focus:ring-legal-blue/5 outline-none transition-all" 
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">Caveatee Name</label>
              <input 
                type="text" 
                placeholder="Enter name of caveatee"
                className="w-full border-2 border-gray-100 bg-gray-50/50 rounded-xl px-5 py-3.5 focus:border-legal-blue focus:bg-white focus:ring-4 focus:ring-legal-blue/5 outline-none transition-all" 
              />
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">Verification</label>
              <div className="bg-gray-50/50 p-4 rounded-xl border border-gray-100">
                <Captcha />
              </div>
            </div>
            
            <div className="flex gap-4 pt-2">
              <button 
                onClick={() => setShowResults(true)}
                className="flex-1 bg-legal-blue text-white px-8 py-4 rounded-xl font-bold hover:bg-legal-blue/90 transition-all shadow-lg shadow-legal-blue/20 flex items-center justify-center gap-2 group active:scale-95"
              >
                <Search className="w-5 h-5 group-hover:scale-110 transition-transform" />
                Search Caveat
              </button>
              <button 
                onClick={() => setShowResults(false)}
                className="bg-gray-900 text-white px-8 py-4 rounded-xl font-bold hover:bg-black transition-all flex items-center justify-center gap-2 active:scale-95"
              >
                <RotateCcw className="w-5 h-5" />
                Reset
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Results or HowTo */}
      {showResults ? (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Gavel className="w-5 h-5 text-legal-accent" />
              Caveat Results
            </h3>
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
          "Select the State, District, and Court Complex where the caveat might be filed.",
          "Choose the search mode (Anywhere, Starting with, etc.).",
          "Enter the Caveator or Caveatee name as per records.",
          "Complete the captcha and click 'Search Caveat' to view details."
        ]} />
      )}
    </div>
  );
}
