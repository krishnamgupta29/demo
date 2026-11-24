import React from 'react';
import { useStudy } from '../../context/StudyContext';
import { Activity, FolderOpen } from 'lucide-react';

export const Header: React.FC = () => {
  const { currentStudy, currentStudyId, studies, selectStudy } = useStudy();

  return (
    <header style={{
      height: '56px',
      background: 'var(--surface-panel)',
      borderBottom: '1px solid var(--surface-border)',
      padding: '0 20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      userSelect: 'none',
      zIndex: 40,
    }}>
      {/* Brand Monogram & Product Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '32px',
          height: '32px',
          background: 'var(--color-petrol-800)',
          borderRadius: 'var(--radius-sm)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--color-brass-400)',
          fontWeight: 700,
          fontSize: '15px',
          letterSpacing: '0.05em',
          border: '1px solid var(--color-brass-500)',
        }}>
          DT
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontSize: '15px',
              fontWeight: 700,
              letterSpacing: '0.04em',
              color: 'var(--color-petrol-800)',
            }}>
              DENTRACE
            </span>
            <span className="badge badge-jade">
              Level 11 React Edition
            </span>
          </div>
          <p style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginTop: '-2px',
          }}>
            Panoramic Radiograph Anomaly Screener & Pre-Authorization Engine
          </p>
        </div>
      </div>

      {/* Center/Right: Active Case Selector & System Telemetry */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {/* Active Study Switcher */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'var(--surface-canvas)',
          padding: '4px 10px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--surface-border)',
        }}>
          <FolderOpen size={14} style={{ color: 'var(--color-jade-500)' }} />
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Active Case:
          </span>
          <select
            value={currentStudyId || ''}
            onChange={(e) => selectStudy(e.target.value)}
            style={{
              padding: '2px 8px',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              fontFamily: 'var(--font-mono)',
              background: '#FFFFFF',
              border: '1px solid var(--surface-border)',
              borderRadius: 'var(--radius-xs)',
              cursor: 'pointer',
              color: 'var(--color-petrol-800)',
            }}
          >
            {studies.map((s) => (
              <option key={s.study_id} value={s.study_id}>
                {s.study_id.substring(0, 16)} {s.patient_anonymous_id ? `(${s.patient_anonymous_id})` : ''} - {s.status}
              </option>
            ))}
          </select>

          {currentStudy && (
            <span className="badge badge-petrol" style={{ fontSize: '10px' }}>
              {currentStudy.findings?.length || 0} Anomalies
            </span>
          )}
        </div>

        {/* Telemetry Heartbeat Status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: 'var(--text-xs)',
          color: 'var(--text-secondary)',
          background: 'var(--surface-canvas)',
          padding: '4px 10px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--surface-border)',
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: 'var(--status-sound)',
            display: 'inline-block',
            boxShadow: '0 0 6px var(--status-sound)',
          }} />
          <Activity size={12} style={{ color: 'var(--color-jade-500)' }} />
          <span className="tabular-nums" style={{ fontWeight: 500 }}>127.0.0.1:8000</span>
          <span style={{ color: 'var(--text-muted)' }}>•</span>
          <span style={{ color: 'var(--color-petrol-700)', fontWeight: 600 }}>ONLINE</span>
        </div>
      </div>
    </header>
  );
};

