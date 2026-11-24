import React from 'react';
import { AlertCircle } from 'lucide-react';

export const Disclaimer: React.FC = () => {
  return (
    <div style={{
      background: 'var(--color-petrol-800)',
      color: 'var(--color-brass-400)',
      borderBottom: '1px solid var(--color-petrol-900)',
      padding: '4px 16px',
      fontSize: 'var(--text-xs)',
      fontWeight: 500,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      letterSpacing: '0.02em',
      zIndex: 50,
      userSelect: 'none'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <AlertCircle size={13} style={{ color: 'var(--color-brass-500)' }} />
        <span>
          <strong style={{ color: '#FFFFFF', textTransform: 'uppercase' }}>Clinical Boundary:</strong> Draft for dentist review. Not a diagnosis. Autonomous clinical diagnosis and insurance approval are strictly prohibited.
        </span>
      </div>
      <div style={{ display: 'flex', gap: '14px', color: 'var(--surface-subtle)', opacity: 0.85 }}>
        <span>Offline Local-First Engine</span>
        <span>Zero Cloud Egress</span>
      </div>
    </div>
  );
};

