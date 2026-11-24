import React from 'react';
import { TOOTH_NAMES } from '../3d/toothData';
import { Finding } from '../../api/types';

interface Odontogram2DProps {
  selectedFdi?: number | null;
  onSelectTooth?: (fdi: number) => void;
  findings?: Finding[];
}

export const Odontogram2D: React.FC<Odontogram2DProps> = ({
  selectedFdi = 16,
  onSelectTooth,
  findings = [],
}) => {
  // Quadrants definitions
  const q1 = [18, 17, 16, 15, 14, 13, 12, 11]; // Maxillary Right (Viewer Left)
  const q2 = [21, 22, 23, 24, 25, 26, 27, 28]; // Maxillary Left (Viewer Right)
  const q4 = [48, 47, 46, 45, 44, 43, 42, 41]; // Mandibular Right (Viewer Left)
  const q3 = [31, 32, 33, 34, 35, 36, 37, 38]; // Mandibular Left (Viewer Right)

  // Map findings to teeth
  const findingsByFdi = React.useMemo(() => {
    const map = new Map<number, Finding[]>();
    findings.forEach((f) => {
      if (f.tooth_fdi) {
        const list = map.get(f.tooth_fdi) || [];
        list.push(f);
        map.set(f.tooth_fdi, list);
      }
    });
    return map;
  }, [findings]);

  const renderToothCell = (fdi: number) => {
    const isSelected = selectedFdi === fdi;
    const toothFindings = findingsByFdi.get(fdi) || [];
    const hasFindings = toothFindings.length > 0;

    return (
      <button
        key={fdi}
        onClick={() => onSelectTooth && onSelectTooth(fdi)}
        title={`FDI #${fdi}: ${TOOTH_NAMES[fdi] || 'Tooth'}${hasFindings ? ` (${toothFindings[0].pathology_class})` : ''}`}
        style={{
          width: '38px',
          height: '46px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: isSelected
            ? 'var(--color-brass-500)'
            : hasFindings
            ? 'var(--color-terracotta-100)'
            : 'var(--surface-panel)',
          color: isSelected
            ? '#FFFFFF'
            : hasFindings
            ? 'var(--color-terracotta-700)'
            : 'var(--text-primary)',
          border: isSelected
            ? '2px solid var(--color-brass-600)'
            : hasFindings
            ? '1px solid var(--color-terracotta-500)'
            : '1px solid var(--surface-border)',
          borderRadius: 'var(--radius-xs)',
          cursor: 'pointer',
          padding: '2px',
          transition: 'all var(--transition-fast)',
        }}
      >
        <span
          className="tabular-nums"
          style={{
            fontSize: '11px',
            fontWeight: 700,
            fontFamily: 'var(--font-mono)',
          }}
        >
          {fdi}
        </span>
        <div style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          marginTop: '4px',
          background: isSelected
            ? '#FFFFFF'
            : hasFindings
            ? 'var(--status-caries)'
            : 'var(--status-sound)',
        }} />
      </button>
    );
  };

  return (
    <div style={{
      background: 'var(--surface-panel)',
      border: '1px solid var(--surface-border)',
      borderRadius: 'var(--radius-sm)',
      padding: '16px',
      userSelect: 'none',
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
        borderBottom: '1px solid var(--surface-border)',
        paddingBottom: '8px',
      }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-petrol-800)' }}>
          2D Clinical Odontogram (FDI 2-Digit Notation)
        </div>
        <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: 'var(--text-muted)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--status-sound)' }} /> Sound
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--status-caries)' }} /> Finding
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-brass-500)' }} /> Selected
          </span>
        </div>
      </div>

      {/* Maxillary Arch (Upper Jaw) */}
      <div style={{ marginBottom: '10px' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '10px',
          fontWeight: 700,
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginBottom: '4px',
        }}>
          <span>Maxillary Right (Q1)</span>
          <span>Maxillary Arch</span>
          <span>Maxillary Left (Q2)</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
          <div style={{ display: 'flex', gap: '3px' }}>
            {q1.map(renderToothCell)}
          </div>
          <div style={{ width: '1px', background: 'var(--surface-border-strong)' }} />
          <div style={{ display: 'flex', gap: '3px' }}>
            {q2.map(renderToothCell)}
          </div>
        </div>
      </div>

      {/* Arch Divider */}
      <div style={{
        height: '1px',
        background: 'var(--surface-border)',
        margin: '12px 0',
      }} />

      {/* Mandibular Arch (Lower Jaw) */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
          <div style={{ display: 'flex', gap: '3px' }}>
            {q4.map(renderToothCell)}
          </div>
          <div style={{ width: '1px', background: 'var(--surface-border-strong)' }} />
          <div style={{ display: 'flex', gap: '3px' }}>
            {q3.map(renderToothCell)}
          </div>
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '10px',
          fontWeight: 700,
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginTop: '6px',
        }}>
          <span>Mandibular Right (Q4)</span>
          <span>Mandibular Arch</span>
          <span>Mandibular Left (Q3)</span>
        </div>
      </div>
    </div>
  );
};

