import React from 'react';
import { Info } from 'lucide-react';

interface HowToProps {
  steps: string[];
}

export default function HowTo({ steps }: HowToProps) {
  return (
    <div className="mt-12 bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div className="bg-gray-50 px-6 py-3 border-b border-gray-200 flex items-center gap-2">
        <Info className="w-4 h-4 text-legal-blue" />
        <h3 className="font-bold text-sm uppercase tracking-wider">How to Search</h3>
      </div>
      <div className="p-6">
        <ol className="space-y-2">
          {steps.map((step, idx) => (
            <li key={idx} className="flex gap-3 text-sm text-gray-600">
              <span className="font-bold text-legal-blue">{idx + 1}.</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
