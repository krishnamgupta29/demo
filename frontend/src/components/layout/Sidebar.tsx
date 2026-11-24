import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  Crosshair,
  Orbit,
  FileCheck2,
  FileSignature,
  Settings2,
  ShieldAlert,
  LucideIcon,
} from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  keynum: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/overview', label: 'Overview', keynum: '1', icon: LayoutDashboard },
  { path: '/upload', label: 'Upload Intake', keynum: '2', icon: UploadCloud },
  { path: '/workstation', label: 'Workstation', keynum: '3', icon: Crosshair },
  { path: '/fdi', label: 'FDI Explorer', keynum: '4', icon: Orbit },
  { path: '/evidence', label: 'Clinical Evidence', keynum: '5', icon: FileCheck2 },
  { path: '/preauth', label: 'Pre-Auth Studio', keynum: '6', icon: FileSignature },
  { path: '/settings', label: 'System Settings', keynum: '7', icon: Settings2 },
];

export const Sidebar: React.FC = () => {
  return (
    <aside style={{
      width: '230px',
      background: 'var(--surface-panel)',
      borderRight: '1px solid var(--surface-border)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      height: '100%',
      userSelect: 'none',
    }}>
      {/* Navigation Links */}
      <div style={{ padding: '16px 10px' }}>
        <div style={{
          fontSize: 'var(--text-2xs)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--text-muted)',
          fontWeight: 700,
          padding: '0 10px 10px 10px',
        }}>
          Clinical Navigation
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => (isActive ? 'active-nav-link' : 'nav-link')}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '9px 12px',
                borderRadius: 'var(--radius-sm)',
                textDecoration: 'none',
                fontSize: 'var(--text-sm)',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? 'var(--color-petrol-800)' : 'var(--text-secondary)',
                background: isActive ? 'var(--color-jade-100)' : 'transparent',
                borderLeft: isActive ? '3px solid var(--color-jade-500)' : '3px solid transparent',
                transition: 'all var(--transition-fast)',
              })}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <item.icon
                  size={16}
                  style={{
                    color: 'inherit',
                  }}
                />
                <span>{item.label}</span>
              </div>
              <span style={{
                fontSize: '10px',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-muted)',
                background: 'rgba(0,0,0,0.04)',
                padding: '1px 5px',
                borderRadius: '2px',
              }}>
                {item.keynum}
              </span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Footer Regulatory Card */}
      <div style={{
        padding: '14px',
        borderTop: '1px solid var(--surface-border)',
        background: 'var(--surface-canvas)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
          <ShieldAlert size={13} style={{ color: 'var(--color-brass-600)' }} />
          <span style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-petrol-800)' }}>
            College Decision Support
          </span>
        </div>
        <p style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
          Not certified by FDA / CE / MDR. Requires verified licensed dentist signoff.
        </p>
      </div>
    </aside>
  );
};
