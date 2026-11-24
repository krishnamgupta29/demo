import React, { useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Disclaimer } from './Disclaimer';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export const Shell: React.FC = () => {
  const navigate = useNavigate();

  // Keyboard navigation shortcuts [1-7]
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts if focus is in an input or textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
        return;
      }
      if (e.key === '1') navigate('/overview');
      if (e.key === '2') navigate('/upload');
      if (e.key === '3') navigate('/workstation');
      if (e.key === '4') navigate('/fdi');
      if (e.key === '5') navigate('/evidence');
      if (e.key === '6') navigate('/preauth');
      if (e.key === '7') navigate('/settings');
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      width: '100vw',
      height: '100vh',
      overflow: 'hidden',
    }}>
      <Disclaimer />
      <Header />
      <div style={{
        display: 'flex',
        flex: 1,
        overflow: 'hidden',
      }}>
        <Sidebar />
        <main style={{
          flex: 1,
          height: '100%',
          overflowY: 'auto',
          background: 'var(--surface-canvas)',
          position: 'relative',
        }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
};

