import React from 'react';
import { Bell, Search, User, ChevronRight } from 'lucide-react';

interface HeaderProps {
  title: string;
}

export default function Header({ title }: HeaderProps) {
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 shrink-0">
      <div className="flex items-center gap-4">
        <nav className="flex items-center gap-2 text-xs font-medium text-gray-400 uppercase tracking-widest">
          <span>Home</span>
          <ChevronRight className="w-3 h-3" />
          <span className="text-legal-blue">{title}</span>
        </nav>
      </div>
      
      <div className="flex items-center gap-6">
        <div className="relative">
          <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input 
            type="text" 
            placeholder="Global Search..." 
            className="bg-gray-50 border border-gray-200 rounded-full pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-legal-blue/10 w-64 transition-all"
          />
        </div>
        
        <div className="flex items-center gap-4">
          <button className="p-2 text-gray-400 hover:text-legal-blue transition-colors relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
          </button>
          <div className="h-8 w-px bg-gray-200"></div>
          <div className="flex items-center gap-3 cursor-pointer group">
            <div className="w-8 h-8 rounded-full bg-legal-accent/20 flex items-center justify-center text-legal-accent font-bold text-xs group-hover:bg-legal-accent group-hover:text-white transition-all">
              JD
            </div>
            <span className="text-sm font-semibold text-gray-700">John Doe</span>
          </div>
        </div>
      </div>
    </header>
  );
}
