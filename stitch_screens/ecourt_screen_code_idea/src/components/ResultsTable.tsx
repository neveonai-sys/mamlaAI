import React from 'react';
import { FileText } from 'lucide-react';
import { CaseResult } from '../types';

interface ResultsTableProps {
  results: CaseResult[];
  type?: 'orders' | 'cause-list';
}

export default function ResultsTable({ results, type = 'cause-list' }: ResultsTableProps) {
  return (
    <div className="mt-8 overflow-hidden border border-gray-200 rounded-xl shadow-sm bg-white">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-legal-blue text-white">
            <th className="px-6 py-4 font-semibold text-sm">Sr No</th>
            <th className="px-6 py-4 font-semibold text-sm">Case Number</th>
            <th className="px-6 py-4 font-semibold text-sm">Party Name</th>
            {type === 'orders' && (
              <>
                <th className="px-6 py-4 font-semibold text-sm">Order Type</th>
                <th className="px-6 py-4 font-semibold text-sm">Date</th>
                <th className="px-6 py-4 font-semibold text-sm">Status</th>
                <th className="px-6 py-4 font-semibold text-sm text-center">Action</th>
              </>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {results?.map((row) => (
            <tr key={row.srNo} className="hover:bg-gray-50 transition-colors">
              <td className="px-6 py-4 text-sm text-gray-500 font-mono">{row.srNo}</td>
              <td className="px-6 py-4 text-sm font-semibold text-legal-blue">{row.caseNumber}</td>
              <td className="px-6 py-4 text-sm text-gray-700">{row.partyName}</td>
              {type === 'orders' && (
                <>
                  <td className="px-6 py-4 text-sm text-gray-600">{row.orderType}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{row.date}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">
                      {row.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-center">
                    <button className="inline-flex items-center gap-1 text-legal-accent hover:underline font-medium">
                      <FileText className="w-4 h-4" />
                      View PDF
                    </button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
