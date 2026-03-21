import React from 'react';
import { RefreshCcw, Volume2 } from 'lucide-react';

export default function Captcha() {
  return (
    <div className="flex items-center gap-3">
      <div className="bg-white border border-gray-200 p-2 rounded flex items-center justify-center select-none shadow-inner">
        <span className="font-serif italic text-2xl tracking-widest text-gray-700 bg-gray-50 px-4 py-1 rounded border border-dashed border-gray-300">
          7z4k9a
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <button type="button" className="p-1 hover:bg-gray-100 rounded transition-colors text-gray-500" title="Audio Captcha">
          <Volume2 className="w-4 h-4" />
        </button>
        <button type="button" className="p-1 hover:bg-gray-100 rounded transition-colors text-gray-500" title="Refresh Captcha">
          <RefreshCcw className="w-4 h-4" />
        </button>
      </div>
      <input 
        type="text" 
        placeholder="Enter Captcha" 
        className="border border-gray-300 rounded px-3 py-2 w-32 focus:ring-2 focus:ring-legal-blue/20 focus:border-legal-blue outline-none transition-all"
      />
    </div>
  );
}
