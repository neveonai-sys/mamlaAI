import React, { useState } from 'react';
import { Users, Info, Gavel, Calendar, Search, RotateCcw } from 'lucide-react';
import Captcha from '../Captcha';
import HowTo from '../HowTo';
import ResultsTable from '../ResultsTable';

const tabs = [
  { id: 'Party Name', icon: Users },
  { id: 'Case Number', icon: Info },
  { id: 'Court Number', icon: Gavel },
  { id: 'Order Date', icon: Calendar },
];

export default function CourtOrdersSearch() {
  const [activeTab, setActiveTab] = useState('Party Name');
  const [showResults, setShowResults] = useState(false);
  const [orderType, setOrderType] = useState('Both');

  const handleSearch = () => {
    setShowResults(true);
  };

  const handleReset = () => {
    setShowResults(false);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Top Selection Bar */}
      <div className="bg-[#2D2D2D] p-6 rounded-t-xl grid grid-cols-1 md:grid-cols-4 gap-6 mb-0">
        <div>
          <label className="block text-xs font-bold text-white uppercase tracking-wider mb-2">Select State</label>
          <select className="w-full bg-white border-none rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-legal-blue/50">
            <option>Select state</option>
            <option>Gujarat</option>
            <option>Bihar</option>
            <option>Maharashtra</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-white uppercase tracking-wider mb-2">Select District</label>
          <select className="w-full bg-white border-none rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-legal-blue/50">
            <option>Select district</option>
            <option>Ahmedabad</option>
            <option>Aurangabad</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-white uppercase tracking-wider mb-2">Select Court Complex</label>
          <select className="w-full bg-white border-none rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-legal-blue/50">
            <option>Select court complex</option>
            <option>Dhandhuka</option>
            <option>Civil Court Complex, Aurangabad</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-white uppercase tracking-wider mb-2">Select Establishment</label>
          <select className="w-full bg-white border-none rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-legal-blue/50">
            <option>Select establishment</option>
            <option>Civil Div. Aurangabad</option>
          </select>
        </div>
      </div>

      <div className="bg-white shadow-xl border border-gray-100 overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-gray-200 bg-gray-50/50">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-4 text-sm font-semibold transition-all border-r border-gray-200 last:border-r-0 ${
                activeTab === tab.id 
                  ? 'bg-white border-b-2 border-b-legal-blue text-legal-blue' 
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              <tab.icon size={18} className={activeTab === tab.id ? 'text-legal-accent' : 'text-gray-400'} />
              {tab.id}
            </button>
          ))}
        </div>
        
        <div className="p-8">
          <div className="mb-6">
            <h3 className="text-legal-blue font-semibold text-sm border-b border-gray-100 pb-2 mb-6">
              Court Orders : Search by {activeTab}
            </h3>
            
            <p className="text-red-600 text-xs mb-6 italic">Fields marked with * are required</p>

            <div className="flex flex-wrap items-end gap-6 mb-8">
              {activeTab === 'Party Name' && (
                <>
                  <div className="flex items-center gap-4">
                    <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                      <span className="text-red-600 mr-1">*</span>Petitioner/Respondent
                    </label>
                    <input 
                      type="text" 
                      placeholder="Enter Petitioner/Respondent"
                      className="border border-gray-300 rounded px-3 py-2 text-sm w-64 focus:ring-1 focus:ring-legal-blue outline-none"
                    />
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                      <span className="text-red-600 mr-1">*</span>Year
                    </label>
                    <input 
                      type="text" 
                      placeholder="Year"
                      className="border border-gray-300 rounded px-3 py-2 text-sm w-24 focus:ring-1 focus:ring-legal-blue outline-none"
                    />
                  </div>
                </>
              )}

              {activeTab === 'Case Number' && (
                <>
                  <div className="flex items-center gap-4">
                    <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                      <span className="text-red-600 mr-1">*</span>Case Type
                    </label>
                    <select className="border border-gray-300 rounded px-3 py-2 text-sm w-64 focus:ring-1 focus:ring-legal-blue outline-none">
                      <option>Select Case Type</option>
                      <option>Civil</option>
                      <option>Criminal</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                      <span className="text-red-600 mr-1">*</span>Case Number
                    </label>
                    <input 
                      type="text" 
                      placeholder="Enter Case number"
                      className="border border-gray-300 rounded px-3 py-2 text-sm w-64 focus:ring-1 focus:ring-legal-blue outline-none"
                    />
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                      <span className="text-red-600 mr-1">*</span>Year
                    </label>
                    <input 
                      type="text" 
                      placeholder="Year"
                      className="border border-gray-300 rounded px-3 py-2 text-sm w-24 focus:ring-1 focus:ring-legal-blue outline-none"
                    />
                  </div>
                </>
              )}

              {activeTab === 'Court Number' && (
                <div className="flex items-center gap-4">
                  <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                    <span className="text-red-600 mr-1">*</span>Court Number
                  </label>
                  <select className="border border-gray-300 rounded px-3 py-2 text-sm w-80 focus:ring-1 focus:ring-legal-blue outline-none">
                    <option>Select Court Number</option>
                    <option>Court 1</option>
                    <option>Court 2</option>
                  </select>
                </div>
              )}

              {activeTab === 'Order Date' && (
                <>
                  <div className="flex items-center gap-4">
                    <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                      <span className="text-red-600 mr-1">*</span>From Date
                    </label>
                    <div className="relative">
                      <input 
                        type="text" 
                        placeholder="Enter From Date"
                        className="border border-gray-300 rounded px-3 py-2 text-sm w-48 focus:ring-1 focus:ring-legal-blue outline-none pr-10"
                      />
                      <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 text-red-400" size={16} />
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="text-sm font-medium text-legal-blue whitespace-nowrap">
                      <span className="text-red-600 mr-1">*</span>To Date
                    </label>
                    <div className="relative">
                      <input 
                        type="text" 
                        placeholder="Enter To Date"
                        className="border border-gray-300 rounded px-3 py-2 text-sm w-48 focus:ring-1 focus:ring-legal-blue outline-none pr-10"
                      />
                      <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 text-red-400" size={16} />
                    </div>
                  </div>
                </>
              )}

              <div className="flex items-center gap-4 ml-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="orderType" 
                    checked={orderType === 'Interim Orders'}
                    onChange={() => setOrderType('Interim Orders')}
                    className="w-4 h-4 text-legal-blue" 
                  />
                  <span className="text-sm font-medium">Interim Orders</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="orderType" 
                    checked={orderType === 'Final Orders'}
                    onChange={() => setOrderType('Final Orders')}
                    className="w-4 h-4 text-legal-blue" 
                  />
                  <span className="text-sm font-medium">Final Orders</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="orderType" 
                    checked={orderType === 'Both'}
                    onChange={() => setOrderType('Both')}
                    className="w-4 h-4 text-legal-blue" 
                  />
                  <span className="text-sm font-medium">Both</span>
                </label>
              </div>
            </div>

            <div className="flex flex-col items-start gap-6">
              <Captcha />
              
              <div className="flex gap-3">
                <button 
                  onClick={handleSearch}
                  className="bg-legal-blue text-white px-8 py-2 rounded-md font-semibold hover:bg-legal-blue/90 transition-all flex items-center gap-2"
                >
                  <Search size={18} />
                  Go
                </button>
                <button 
                  onClick={handleReset}
                  className="bg-[#5D6D7E] text-white px-8 py-2 rounded-md font-semibold hover:bg-[#4A5766] transition-all flex items-center gap-2"
                >
                  <RotateCcw size={18} />
                  Reset
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {showResults ? (
        <ResultsTable 
          type="orders"
          results={[
            { srNo: 1, caseNumber: 'CASE-2024-12345', partyName: 'State vs. John Doe', orderType: 'Interim Order', date: 'Nov 1, 2024', status: 'Issued' },
            { srNo: 2, caseNumber: 'CASE-2024-12346', partyName: 'ABC Corp. vs. XYZ Ltd.', orderType: 'Final Order', date: 'Oct 28, 2024', status: 'Issued' },
            { srNo: 3, caseNumber: 'CASE-2024-12347', partyName: 'Rahul Gupta vs. State', orderType: 'Interim Order', date: 'Oct 25, 2024', status: 'Issued' },
            { srNo: 4, caseNumber: 'CASE-2024-12348', partyName: 'Priya Sharma vs. Municipal Corp', orderType: 'Final Order', date: 'Oct 20, 2024', status: 'Issued' },
            { srNo: 5, caseNumber: 'CASE-2024-12349', partyName: 'Vikram Singh vs. Union of India', orderType: 'Interim Order', date: 'Oct 15, 2024', status: 'Issued' },
          ]} 
        />
      ) : (
        <HowTo steps={[
          "Select the State, District, and Court Complex.",
          "Choose the search criteria (Party Name, Case Number, etc.).",
          "Enter the required details and captcha.",
          "Click 'Go' to view the orders."
        ]} />
      )}
    </div>
  );
}
