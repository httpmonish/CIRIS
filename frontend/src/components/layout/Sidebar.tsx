'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Bell,
  FolderGit2,
  Network,
  Users,
  CreditCard,
  Building2,
  MapPin,
  Settings,
  ShieldCheck,
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Alerts', href: '/alerts', icon: Bell },
  { name: 'Cases', href: '/cases', icon: FolderGit2 },
  { name: 'Networks', href: '/networks/NET-DEMO-001', icon: Network },
  { name: 'Entities', href: '/entities/ENTITY_000001', icon: Users },
  { name: 'Transactions', href: '/transactions/TX_DEMO_001', icon: CreditCard },
  { name: 'ATM Intelligence', href: '/atms/ATM_000349', icon: Building2 },
  { name: 'GIS Map', href: '/map', icon: MapPin },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800/80 flex flex-col shrink-0 h-screen sticky top-0">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center gap-3">
        <div className="p-2 rounded-lg bg-blue-600/20 border border-blue-500/40 text-blue-400">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <h1 className="font-extrabold text-base tracking-wider text-white">CIRIS</h1>
          <p className="text-[10px] font-mono text-slate-400 tracking-tight">Predictive Cybercrime Intel</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-inner'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-500'}`} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/80 text-[10px] font-mono text-slate-500 text-center">
        CIRIS ML V4 Loaded | Phase 2 Active
      </div>
    </aside>
  );
};
