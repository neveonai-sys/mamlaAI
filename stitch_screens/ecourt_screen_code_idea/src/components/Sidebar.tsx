import React from 'react';
import { 
  LayoutDashboard, 
  Search, 
  Scale, 
  FileText, 
  ListTodo, 
  ShieldAlert, 
  Settings, 
  User,
  Menu
} from 'lucide-react';
import { Screen, NavItem } from '../types';

const navItems: NavItem[] = [
  { id: 'DASHBOARD', label: 'Dashboard', icon: 'LayoutDashboard' },
  { id: 'CNR', label: 'CNR Number', icon: 'Search' },
  { id: 'CASE_STATUS', label: 'Case Status', icon: 'Scale' },
  { id: 'COURT_ORDERS', label: 'Court Orders', icon: 'FileText' },
  { id: 'CAUSE_LIST', label: 'Cause List', icon: 'ListTodo' },
  { id: 'CAVEAT', label: 'Caveat Search', icon: 'ShieldAlert' },
  { id: 'SETTINGS', label: 'Settings', icon: 'Settings' },
];

interface SidebarProps {
  activeScreen: Screen;
  onNavigate: (screen: Screen) => void;
}

const IconMap: Record<string, React.ElementType> = {
  LayoutDashboard,
  Search,
  Scale,
  FileText,
  ListTodo,
  ShieldAlert,
  Settings,
  User,
};

export default function Sidebar({ activeScreen, onNavigate }: SidebarProps) {
  return (
    <div className="w-64 bg-legal-blue h-screen flex flex-col text-white shrink-0">
      <div className="p-6 flex items-center gap-2 border-b border-white/10">
        <Scale className="text-legal-accent w-8 h-8" />
        <div>
          <h1 className="text-xl font-bold tracking-tight">Mamla.AI</h1>
          <p className="text-[10px] text-white/50 uppercase tracking-widest">Premium Legal Platform</p>
        </div>
      </div>
      
      <div className="flex-1 py-6">
        <div className="px-4 mb-4">
          <p className="text-[10px] font-semibold text-white/30 uppercase tracking-wider px-4">Search Menu</p>
        </div>
        <nav className="space-y-1 px-2">
          {navItems.map((item) => {
            const Icon = IconMap[item.icon];
            const isActive = activeScreen === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group ${
                  isActive 
                    ? 'bg-legal-accent/10 text-legal-accent border-r-4 border-legal-accent' 
                    : 'text-white/70 hover:bg-white/5 hover:text-white'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-legal-accent' : 'text-white/40 group-hover:text-white/70'}`} />
                <span className="font-medium text-sm">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
      
      <div className="p-4 border-t border-white/10">
        <button 
          onClick={() => onNavigate('PROFILE')}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-white/70 hover:bg-white/5 transition-colors"
        >
          <User className="w-5 h-5 text-white/40" />
          <span className="font-medium text-sm">My Profile</span>
        </button>
      </div>
    </div>
  );
}
