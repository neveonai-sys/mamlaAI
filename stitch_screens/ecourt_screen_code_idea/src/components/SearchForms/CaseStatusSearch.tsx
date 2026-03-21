import React, { useState } from 'react';
import { Users, Info, FileText, User, FileDigit, Gavel, FileCheck, Search, RotateCcw } from 'lucide-react';
import Captcha from '../Captcha';
import HowTo from '../HowTo';
import ResultsTable from '../ResultsTable';
import { CaseResult } from '../../types';

const tabs = [
  { id: 'Party Name', label: 'Party Name', icon: Users, color: 'text-teal-500', disabled: false },
  { id: 'Case Number', label: 'Case Number', icon: Info, color: 'text-orange-500', disabled: false },
  { id: 'Filing Number', label: 'Filing Number', icon: FileText, color: 'text-green-600', disabled: false },
  { id: 'Advocate', label: 'Advocate', icon: User, color: 'text-blue-500', disabled: false },
  { id: 'FIR Number', label: 'FIR Number', icon: FileDigit, color: 'text-pink-500', disabled: true },
  { id: 'Act', label: 'Act', icon: Gavel, color: 'text-orange-700', disabled: true },
  { id: 'Case Type', label: 'Case Type', icon: FileCheck, color: 'text-blue-800', disabled: true },
];

const mockResults: CaseResult[] = [
  { srNo: 1, caseNumber: 'ARBITRATION CASE/124/2024', partyName: 'M/S ABC CONSTRUCTION VS STATE OF BIHAR', status: 'Pending' },
  { srNo: 2, caseNumber: 'CIVIL APPEAL/45/2023', partyName: 'RAMESH KUMAR VS UNION OF INDIA', status: 'Disposed' },
  { srNo: 3, caseNumber: 'ARBITRATION CASE/89/2024', partyName: 'GLOBAL INFRA VS NHAI', status: 'Pending' },
];

export default function CaseStatusSearch() {
  const [activeTab, setActiveTab] = useState('Party Name');
  const [advocateSubTab, setAdvocateSubTab] = useState('Advocate Name');
  const [showResults, setShowResults] = useState(false);

  const handleSearch = () => {
    setShowResults(true);
  };

  const handleReset = () => {
    setShowResults(false);
  };
  
  const renderForm = () => {
    switch (activeTab) {
      case 'Party Name':
        return (
          <div className="space-y-6">
            <h3 className="text-blue-800 text-sm font-medium border-b border-gray-100 pb-2">Case Status : Search by Petitioner/Respondent</h3>
            <p className="text-red-600 text-[11px] italic">Fields marked with * are required</p>
            
            <div className="flex flex-wrap items-center gap-x-12 gap-y-6">
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                  <span className="text-red-500 mr-1">*</span>Petitioner/Respondent
                </label>
                <input 
                  type="text" 
                  placeholder="Enter Petitioner/Respondent"
                  className="border border-gray-300 rounded px-3 py-1.5 w-64 text-sm outline-none focus:border-blue-400"
                />
              </div>
              
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                  <span className="text-red-500 mr-1">*</span>Registration Year
                </label>
                <input 
                  type="text" 
                  placeholder="Enter Year"
                  className="border border-gray-300 rounded px-3 py-1.5 w-32 text-sm outline-none focus:border-blue-400"
                />
              </div>

              <div className="flex p-1 bg-gray-100 rounded-lg border border-gray-200">
                {['Pending', 'Disposed', 'Both'].map(status => (
                  <button
                    key={status}
                    type="button"
                    onClick={() => {}} // Add state if needed
                    className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
                      status === 'Pending' // Mock active state
                        ? 'bg-white text-legal-blue shadow-sm' 
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-12 pt-4">
              <div className="flex items-center gap-4">
                <label className="text-sm font-medium text-blue-900">Captcha</label>
                <Captcha />
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={handleSearch}
                  className="bg-legal-blue text-white px-10 py-2 rounded font-bold hover:bg-blue-900 transition-all shadow-sm flex items-center gap-2"
                >
                  <Search className="w-4 h-4" /> Go
                </button>
                <button 
                  onClick={handleReset}
                  className="bg-slate-500 text-white px-10 py-2 rounded font-bold hover:bg-slate-600 transition-all shadow-sm flex items-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" /> Reset
                </button>
              </div>
            </div>
          </div>
        );

      case 'Case Number':
        return (
          <div className="space-y-6">
            <h3 className="text-blue-800 text-sm font-medium border-b border-gray-100 pb-2">Case Status : Search by Case Number</h3>
            <p className="text-red-600 text-[11px] italic">Fields marked with * are required</p>
            
            <div className="flex flex-wrap items-center gap-x-12 gap-y-6">
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                  <span className="text-red-500 mr-1">*</span>Case Type
                </label>
                <select className="border border-gray-300 rounded px-3 py-1.5 w-64 text-sm outline-none focus:border-blue-400">
                  <option>Select Case Type</option>
                  <option>ARBITRATION CASE</option>
                  <option>ARBITRATION R.D.</option>
                  <option>CIVIL APPEAL</option>
                  <option>CIVIL REVISION</option>
                  <option>CRIMINAL APPEAL</option>
                  <option>CRIMINAL REVISION</option>
                  <option>WRIT PETITION</option>
                </select>
              </div>
              
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                  <span className="text-red-500 mr-1">*</span>Case Number
                </label>
                <input 
                  type="text" 
                  placeholder="Case Number"
                  className="border border-gray-300 rounded px-3 py-1.5 w-48 text-sm outline-none focus:border-blue-400"
                />
              </div>

              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                  <span className="text-red-500 mr-1">*</span>Year
                </label>
                <input 
                  type="text" 
                  placeholder="Year"
                  className="border border-gray-300 rounded px-3 py-1.5 w-24 text-sm outline-none focus:border-blue-400"
                />
              </div>
            </div>

            <div className="flex items-center gap-12 pt-4">
              <div className="flex items-center gap-4">
                <label className="text-sm font-medium text-blue-900">Captcha</label>
                <Captcha />
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={handleSearch}
                  className="bg-legal-blue text-white px-10 py-2 rounded font-bold hover:bg-blue-900 transition-all shadow-sm flex items-center gap-2"
                >
                  <Search className="w-4 h-4" /> Go
                </button>
                <button 
                  onClick={handleReset}
                  className="bg-slate-500 text-white px-10 py-2 rounded font-bold hover:bg-slate-600 transition-all shadow-sm flex items-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" /> Reset
                </button>
              </div>
            </div>
          </div>
        );

      case 'Filing Number':
        return (
          <div className="space-y-6">
            <h3 className="text-blue-800 text-sm font-medium border-b border-gray-100 pb-2">Case Status : Search by Filing Number</h3>
            <p className="text-red-600 text-[11px] italic">Fields marked with * are required</p>
            
            <div className="flex flex-wrap items-center gap-x-12 gap-y-6">
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                  <span className="text-red-500 mr-1">*</span>Filing Number
                </label>
                <input 
                  type="text" 
                  placeholder="Filing Number"
                  className="border border-gray-300 rounded px-3 py-1.5 w-64 text-sm outline-none focus:border-blue-400"
                />
              </div>
              
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                  <span className="text-red-500 mr-1">*</span>Year
                </label>
                <input 
                  type="text" 
                  placeholder="Year"
                  className="border border-gray-300 rounded px-3 py-1.5 w-24 text-sm outline-none focus:border-blue-400"
                />
              </div>
            </div>

            <div className="flex items-center gap-12 pt-4">
              <div className="flex items-center gap-4">
                <label className="text-sm font-medium text-blue-900">Captcha</label>
                <Captcha />
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={handleSearch}
                  className="bg-legal-blue text-white px-10 py-2 rounded font-bold hover:bg-blue-900 transition-all shadow-sm flex items-center gap-2"
                >
                  <Search className="w-4 h-4" /> Go
                </button>
                <button 
                  onClick={handleReset}
                  className="bg-slate-500 text-white px-10 py-2 rounded font-bold hover:bg-slate-600 transition-all shadow-sm flex items-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" /> Reset
                </button>
              </div>
            </div>
          </div>
        );

      case 'Advocate':
        return (
          <div className="space-y-6">
            <h3 className="text-blue-800 text-sm font-medium border-b border-gray-100 pb-2">Case Status : Search by Advocate</h3>
            <p className="text-red-600 text-[11px] italic">Fields marked with * are required</p>
            
            <div className="flex flex-wrap items-center gap-x-12 gap-y-6">
              <div className="flex p-1 bg-gray-100 rounded-lg border border-gray-200">
                {['Advocate Name', 'Bar Code', 'Date Case List'].map(tab => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setAdvocateSubTab(tab)}
                    className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
                      advocateSubTab === tab 
                        ? 'bg-white text-legal-blue shadow-sm' 
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {advocateSubTab === 'Advocate Name' && (
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                    <span className="text-red-500 mr-1">*</span>Advocate
                  </label>
                  <input 
                    type="text" 
                    placeholder="Advocate"
                    className="border border-gray-300 rounded px-3 py-1.5 w-64 text-sm outline-none focus:border-blue-400"
                  />
                </div>
              )}

              {(advocateSubTab === 'Bar Code' || advocateSubTab === 'Date Case List') && (
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                    <span className="text-red-500 mr-1">*</span>Advocate Bar Code
                  </label>
                  <div className="flex border border-gray-300 rounded overflow-hidden shadow-sm">
                    <input type="text" placeholder="statecc" className="w-16 px-2 py-1.5 border-r border-gray-300 text-sm outline-none" />
                    <input type="text" placeholder="barcod" className="w-16 px-2 py-1.5 border-r border-gray-300 text-sm outline-none" />
                    <input type="text" placeholder="year" className="w-16 px-2 py-1.5 text-sm outline-none" />
                  </div>
                </div>
              )}

              {advocateSubTab === 'Date Case List' && (
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-blue-900 whitespace-nowrap">
                    <span className="text-red-500 mr-1">*</span>Case List Date
                  </label>
                  <div className="relative">
                    <input 
                      type="text" 
                      defaultValue="20-03-2026"
                      className="border border-gray-300 rounded px-3 py-1.5 w-40 text-sm outline-none focus:border-blue-400"
                    />
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-red-400">📅</span>
                  </div>
                </div>
              )}

              <div className="flex p-1 bg-gray-100 rounded-lg border border-gray-200">
                {['Pending', 'Disposed', 'Both'].map(status => (
                  <button
                    key={status}
                    type="button"
                    onClick={() => {}} // Add state if needed
                    className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
                      status === 'Pending' // Mock active state
                        ? 'bg-white text-legal-blue shadow-sm' 
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-12 pt-4">
              <div className="flex items-center gap-4">
                <label className="text-sm font-medium text-blue-900">Captcha</label>
                <Captcha />
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={handleSearch}
                  className="bg-legal-blue text-white px-10 py-2 rounded font-bold hover:bg-blue-900 transition-all shadow-sm flex items-center gap-2"
                >
                  <Search className="w-4 h-4" /> Go
                </button>
                <button 
                  onClick={handleReset}
                  className="bg-slate-500 text-white px-10 py-2 rounded font-bold hover:bg-slate-600 transition-all shadow-sm flex items-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" /> Reset
                </button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };
  
  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="bg-legal-blue p-4 rounded-t-xl grid grid-cols-4 gap-6 shadow-lg">
        <div>
          <label className="block text-[10px] font-bold text-white uppercase tracking-widest mb-1 opacity-80">Select State</label>
          <select className="w-full border border-gray-400 rounded px-3 py-1.5 bg-white text-sm outline-none focus:ring-2 focus:ring-blue-500/30">
            <option>Bihar</option>
            <option>Delhi</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] font-bold text-white uppercase tracking-widest mb-1 opacity-80">Select District</label>
          <select className="w-full border border-gray-400 rounded px-3 py-1.5 bg-white text-sm outline-none focus:ring-2 focus:ring-blue-500/30">
            <option>Aurangabad</option>
            <option>New Delhi</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] font-bold text-white uppercase tracking-widest mb-1 opacity-80">Select Court Complex</label>
          <select className="w-full border border-gray-400 rounded px-3 py-1.5 bg-white text-sm outline-none focus:ring-2 focus:ring-blue-500/30">
            <option>Civil Court Complex, Aurangabad</option>
            <option>High Court of Delhi</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] font-bold text-white uppercase tracking-widest mb-1 opacity-80">Select Establishment</label>
          <select className="w-full border border-gray-400 rounded px-3 py-1.5 bg-white text-sm outline-none focus:ring-2 focus:ring-blue-500/30">
            <option>DJ Division Aurangabad</option>
            <option>Establishment 2</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-b-2xl shadow-2xl border border-gray-200 overflow-hidden">
        <div className="flex bg-[#f1f2f6] border-b border-gray-200">
          {tabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                disabled={tab.disabled}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-[11px] font-bold transition-all border-r border-gray-200 last:border-r-0 ${
                  activeTab === tab.id 
                    ? 'bg-white text-blue-700 border-b-2 border-b-blue-600' 
                    : tab.disabled 
                      ? 'text-gray-400 cursor-not-allowed bg-gray-50' 
                      : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Icon className={`w-4 h-4 ${activeTab === tab.id ? tab.color : 'text-gray-400'}`} />
                {tab.label}
              </button>
            );
          })}
        </div>
        
        <div className="p-10">
          {renderForm()}
          
          {showResults && (
            <div className="mt-12 pt-12 border-t border-gray-100 animate-in fade-in slide-in-from-top-4 duration-500">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-serif font-bold text-legal-blue">Search Results</h3>
                <span className="text-sm text-gray-500">{mockResults.length} cases found</span>
              </div>
              <ResultsTable results={mockResults} />
            </div>
          )}
        </div>
      </div>
      
      {!showResults && (
        <HowTo steps={[
          "Select State, District, Court Complex and Establishment from the dropdowns",
          "Select the search criteria tab (e.g., Party Name, Case Number)",
          "Enter the required details marked with *",
          "Enter the captcha and click on Go button"
        ]} />
      )}
    </div>
  );
}
