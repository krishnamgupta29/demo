import React, { useState, memo } from 'react';
import { DentalArchGLTF } from './DentalArchGLTF';
import { ToothCutaway3D } from './ToothCutaway3D';
import { Finding } from '../../api/types';
import { Grid, Eye } from 'lucide-react';

export interface DentalArch3DProps {
  selectedFdi?: number | null;
  onSelectTooth?: (fdi: number) => void;
  findings?: Finding[];
  height?: number | string;
  onSelectAnatomicalStructure?: (structure: string) => void;
  activeAnatomicalStructure?: string | null;
}

export const DentalArch3D = memo<DentalArch3DProps>(({
  selectedFdi = null,
  onSelectTooth,
  findings = [],
  height = '100%',
  onSelectAnatomicalStructure,
  activeAnatomicalStructure,
}) => {
  const [activeView, setActiveView] = useState<'arch' | 'cutaway'>('arch');

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: typeof height === 'number' ? `${height}px` : height,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        backgroundColor: '#0A0D0C',
      }}
    >
      {/* ─── Top View Switcher (Only Full Dental Arch / Tooth Anatomy) ───────── */}
      <div
        style={{
          position: 'absolute',
          top: 8,
          left: 8,
          zIndex: 35,
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'rgba(10, 15, 14, 0.90)',
          backdropFilter: 'blur(8px)',
          padding: '3px',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.35)',
        }}
      >
        <button
          onClick={() => setActiveView('arch')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 600,
            border: 'none',
            cursor: 'pointer',
            backgroundColor: activeView === 'arch' ? '#0F766E' : 'transparent',
            color: activeView === 'arch' ? '#FFFFFF' : '#94A3B8',
            transition: 'all 0.15s ease',
          }}
        >
          <Grid style={{ width: 13, height: 13 }} />
          <span>Full Dental Arch</span>
        </button>

        <button
          onClick={() => setActiveView('cutaway')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 600,
            border: 'none',
            cursor: 'pointer',
            backgroundColor: activeView === 'cutaway' ? '#0F766E' : 'transparent',
            color: activeView === 'cutaway' ? '#FFFFFF' : '#94A3B8',
            transition: 'all 0.15s ease',
          }}
        >
          <Eye style={{ width: 13, height: 13 }} />
          <span>Tooth Anatomy</span>
        </button>
      </div>

      {/* ─── 3D Viewer Canvas Container ────────────────────────────────────── */}
      <div style={{ flex: 1, width: '100%', height: '100%', position: 'relative', minHeight: 0 }}>
        {/* Keep both mounted; toggle visibility to prevent Three.js remount on view switch */}
        <div style={{ position: 'absolute', inset: 0, display: activeView === 'arch' ? 'block' : 'none' }}>
          <DentalArchGLTF
            selectedFdi={selectedFdi}
            onSelectTooth={onSelectTooth}
            findings={findings}
            height="100%"
          />
        </div>
        <div style={{ position: 'absolute', inset: 0, display: activeView === 'cutaway' ? 'block' : 'none' }}>
          <ToothCutaway3D
            height="100%"
            selectedFdi={selectedFdi}
            selectedPathology={
              findings.find((f) => f.tooth_fdi === selectedFdi)?.pathology_class ||
              findings[0]?.pathology_class
            }
            onSelectAnatomicalStructure={onSelectAnatomicalStructure}
            activeAnatomicalStructure={activeAnatomicalStructure}
          />
        </div>
      </div>
    </div>
  );
});

DentalArch3D.displayName = 'DentalArch3D';
