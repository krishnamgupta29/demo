import React, { useState } from 'react';
import {
  ChevronRight,
  Sun,
  Moon,
  Box,
  ShieldCheck,
  FileText,
  Lock,
  Scan,
} from 'lucide-react';

/* ═══════════════════════════════════════════════════════════════════════════════
   DENTRACE — HERO SECTION (EXACT TEMPLATE RECREATION)
   Matches: C:\Users\krish\Downloads\gradient-dental-clinic-landing-page (6798216.jpg)
   Colors:
     Blue:   #0084ff
     Cyan:   #01e2fe / #00f0d3
     Teal:   #00f7cb / #47fbe2
     Text:   #0b2238 (heading), #556980 (body)
     Button: #01e2fe
     Font:   Quicksand, sans-serif
   ═══════════════════════════════════════════════════════════════════════════════ */

export interface HeroSectionExactProps {
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onStartExamination: () => void;
  systemHealth?: 'healthy' | 'degraded';
}

/* ─── Top-Right & Bottom Flowing Gradient Waves (Vector SVG) ────────────────── */
const TemplateCurves: React.FC<{ isDark: boolean }> = ({ isDark }) => (
  <svg
    viewBox="0 0 1440 900"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    preserveAspectRatio="none"
    style={{
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      zIndex: 1,
      pointerEvents: 'none',
    }}
  >
    <defs>
      {/* Top-Right Primary: Deep Blue to Cyan */}
      <linearGradient id="topRightWave1" x1="0.5" y1="0" x2="1" y2="0.9">
        <stop offset="0%" stopColor={isDark ? '#0066cc' : '#0084ff'} />
        <stop offset="60%" stopColor={isDark ? '#00b8a9' : '#00f0d3'} />
        <stop offset="100%" stopColor={isDark ? '#00e0c0' : '#01e2fe'} />
      </linearGradient>

      {/* Top-Right Secondary (Softer Cyan Glow) */}
      <linearGradient id="topRightWave2" x1="0.6" y1="0" x2="0.9" y2="0.7">
        <stop offset="0%" stopColor={isDark ? '#004c99' : '#0084ff'} stopOpacity="0.75" />
        <stop offset="100%" stopColor={isDark ? '#00c49e' : '#47fbe2'} stopOpacity="0.65" />
      </linearGradient>

      {/* Bottom Wave: Teal-Green to Cyan */}
      <linearGradient id="bottomWaveGreen" x1="0" y1="0.7" x2="0.6" y2="1">
        <stop offset="0%" stopColor={isDark ? '#008c73' : '#00f7cb'} />
        <stop offset="50%" stopColor={isDark ? '#00b396' : '#28f9e4'} />
        <stop offset="100%" stopColor={isDark ? '#00a3cc' : '#01e2fe'} />
      </linearGradient>

      <linearGradient id="bottomWaveCyan" x1="0.1" y1="0.9" x2="0.8" y2="1">
        <stop offset="0%" stopColor={isDark ? '#00594a' : '#00f7cb'} stopOpacity="0.7" />
        <stop offset="100%" stopColor={isDark ? '#0088aa' : '#01e2fe'} stopOpacity="0.45" />
      </linearGradient>
    </defs>

    {/* ── TOP-RIGHT FLOWING SWEEP (matches 6798216.jpg) ──────────────────── */}
    {/* Outer secondary curve */}
    <path
      d="M 680 0 Q 860 30 1020 90 Q 1180 160 1300 280 Q 1400 390 1440 540 L 1440 0 Z"
      fill="url(#topRightWave2)"
    />

    {/* Primary deep curve */}
    <path
      d="M 780 0 Q 940 30 1080 85 Q 1230 150 1340 260 Q 1420 360 1440 480 L 1440 0 Z"
      fill="url(#topRightWave1)"
    />

    {/* Thin white accent contour */}
    <path
      d="M 740 0 Q 910 32 1060 90 Q 1200 155 1320 270 Q 1410 375 1440 500"
      stroke={isDark ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.65)'}
      strokeWidth="2.5"
      fill="none"
    />

    {/* ── BOTTOM FLOWING WAVE (matches 6798216.jpg) ──────────────────────── */}
    {/* Background softer wave */}
    <path
      d="M 0 680 Q 120 640 280 670 Q 480 710 680 770 Q 880 830 1080 810 Q 1280 790 1440 840 L 1440 900 L 0 900 Z"
      fill="url(#bottomWaveCyan)"
    />

    {/* Foreground primary green/cyan wave */}
    <path
      d="M 0 740 Q 140 700 320 730 Q 520 770 720 820 Q 920 870 1140 840 Q 1300 815 1440 860 L 1440 900 L 0 900 Z"
      fill="url(#bottomWaveGreen)"
    />
  </svg>
);

/* ─── Exact Tooth Logo (Heart + Tooth + Magnifier) ──────────────────────────── */
const DentalCareLogo: React.FC<{ isDark: boolean }> = ({ isDark }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
    <svg width="44" height="44" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Cyan/Blue Tooth Body */}
      <path
        d="M24 6C18.5 6 15 9.5 14 14C13 18.5 14 23 15.5 28C16.2 30.5 17.5 32 19 32C20.5 32 21.2 30 21.8 27.5C22.3 25.5 23 25.5 23.5 27.5C24 30 24.8 32 26.2 32C27.8 32 29 30.5 29.8 28C31.2 23 32.2 18.5 31.2 14C30.2 9.5 26.8 6 24 6Z"
        fill="url(#logoToothGrad)"
      />
      {/* Heart on top-left */}
      <path
        d="M12.5 10C11.5 8.8 9.8 8.8 8.8 10C7.8 11.2 8.5 13 10.2 14.8L12.5 17L14.8 14.8C16.5 13 17.2 11.2 16.2 10C15.2 8.8 13.5 8.8 12.5 10Z"
        fill={isDark ? '#0084ff' : '#0066cc'}
      />
      {/* Magnifier lens on bottom-right */}
      <circle cx="34" cy="34" r="7" stroke={isDark ? '#01e2fe' : '#00f0d3'} strokeWidth="2.5" fill="none" />
      <line x1="39" y1="39" x2="44" y2="44" stroke={isDark ? '#01e2fe' : '#00f0d3'} strokeWidth="2.8" strokeLinecap="round" />

      <defs>
        <linearGradient id="logoToothGrad" x1="14" y1="6" x2="31" y2="32">
          <stop offset="0%" stopColor={isDark ? '#00e0c0' : '#a0ffff'} />
          <stop offset="100%" stopColor={isDark ? '#0084ff' : '#0084ff'} />
        </linearGradient>
      </defs>
    </svg>

    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <span
        style={{
          fontFamily: "'Quicksand', -apple-system, BlinkMacSystemFont, sans-serif",
          fontSize: '18px',
          fontWeight: 700,
          letterSpacing: '0.08em',
          color: isDark ? '#ffffff' : '#0b2238',
          textTransform: 'uppercase',
          lineHeight: 1.1,
        }}
      >
        DENTRACE
      </span>
      <span
        style={{
          fontFamily: "'Quicksand', sans-serif",
          fontSize: '10px',
          fontWeight: 600,
          letterSpacing: '0.14em',
          color: isDark ? '#01e2fe' : '#0084ff',
          textTransform: 'uppercase',
        }}
      >
        CLINICAL DECISION SUPPORT
      </span>
    </div>
  </div>
);

/* ═══════════════════════════════════════════════════════════════════════════════ */

export const HeroSectionExact: React.FC<HeroSectionExactProps> = ({
  theme,
  onToggleTheme,
  onStartExamination,
  systemHealth = 'healthy',
}) => {
  const [activeNav, setActiveNav] = useState<string>('Home');
  const isDark = theme === 'dark';

  // Palette from 6798216.jpg
  const BLUE = '#0084ff';
  const CYAN_BTN = '#01e2fe';
  const BG_COLOR = isDark ? '#091322' : '#ffffff';
  const HEADING_COLOR = isDark ? '#ffffff' : '#0b2238';
  const BODY_COLOR = isDark ? '#9db2cc' : '#556980';
  const NAV_LINK_COLOR = isDark ? '#01e2fe' : '#0084ff';

  const scrollToSection = (id: string, name: string) => {
    setActiveNav(name);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section
      id="hero"
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '100vh',
        backgroundColor: BG_COLOR,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        overflow: 'hidden',
        boxSizing: 'border-box',
        transition: 'background-color 0.35s ease',
        fontFamily: "'Quicksand', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* ─── Flowing Gradient Wave Curves ─────────────────────────────────────── */}
      <TemplateCurves isDark={isDark} />

      {/* ═══ 1. TOP NAVIGATION HEADER ══════════════════════════════════════════ */}
      <header
        style={{
          width: '100%',
          maxWidth: '1440px',
          margin: '0 auto',
          padding: '24px 56px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          zIndex: 40,
          boxSizing: 'border-box',
        }}
      >
        {/* Left: Logo */}
        <div
          style={{ cursor: 'pointer' }}
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        >
          <DentalCareLogo isDark={isDark} />
        </div>

        {/* Right: Navigation Links + Theme Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '38px' }}>
          <nav style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
            {[
              { label: 'Home', target: 'hero' },
              { label: 'About', target: 'technology' },
              { label: 'Make Appointments', target: 'workflow' },
              { label: 'Contact', target: 'contact' },
            ].map((item) => {
              const isActive = activeNav === item.label;
              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => scrollToSection(item.target, item.label)}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: '4px 0',
                    fontFamily: "'Quicksand', sans-serif",
                    fontSize: '14.5px',
                    fontWeight: isActive ? 700 : 600,
                    color: NAV_LINK_COLOR,
                    cursor: 'pointer',
                    letterSpacing: '0.01em',
                    borderBottom: isActive ? `2px solid ${NAV_LINK_COLOR}` : '2px solid transparent',
                    transition: 'all 0.15s ease',
                    opacity: isActive ? 1 : 0.85,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.opacity = '0.85';
                  }}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Theme Switcher Toggle */}
          <button
            type="button"
            onClick={onToggleTheme}
            aria-label={`Switch to ${isDark ? 'Light' : 'Dark'} mode`}
            title={`Switch to ${isDark ? 'Light' : 'Dark'} mode`}
            style={{
              background: isDark ? 'rgba(1, 226, 254, 0.12)' : 'rgba(0, 132, 255, 0.08)',
              border: `1.5px solid ${isDark ? '#01e2fe' : '#0084ff'}`,
              borderRadius: '9999px',
              padding: '6px 14px',
              color: NAV_LINK_COLOR,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              fontWeight: 700,
              fontFamily: "'Quicksand', sans-serif",
              transition: 'all 0.2s',
            }}
          >
            {isDark ? <Sun size={13} color="#facc15" /> : <Moon size={13} color={BLUE} />}
            <span>{isDark ? 'Light' : 'Dark'}</span>
          </button>
        </div>
      </header>

      {/* ═══ 2. MAIN BODY (LEFT: DENTAL CHAIR SETUP | RIGHT: TEXT & CTA) ═══════ */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          maxWidth: '1440px',
          width: '100%',
          margin: '0 auto',
          padding: '0 56px',
          zIndex: 20,
          boxSizing: 'border-box',
          gap: '40px',
        }}
      >
        {/* ─── LEFT: EXACT DENTAL CLINIC CHAIR WORKSTATION ILLUSTRATION ───── */}
        <div
          style={{
            flex: '1 1 52%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            maxHeight: '600px',
          }}
        >
          <img
            src="/assets/hero/dental_chair_transparent.png"
            alt="Dental Clinic Examination Workstation"
            style={{
              width: '100%',
              maxWidth: '640px',
              height: 'auto',
              maxHeight: '560px',
              objectFit: 'contain',
              display: 'block',
              filter: isDark ? 'drop-shadow(0 12px 30px rgba(0, 132, 255, 0.25))' : 'drop-shadow(0 8px 24px rgba(0, 0, 0, 0.06))',
              animation: 'floatChair 6s ease-in-out infinite',
            }}
            loading="eager"
          />
        </div>

        {/* ─── RIGHT: TEXT CONTENT & READ MORE / START EXAM BUTTON ─────────── */}
        <div
          style={{
            flex: '1 1 48%',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'flex-start',
            paddingLeft: '20px',
            zIndex: 10,
          }}
        >
          {/* Main Headline (All-caps, bold, Quicksand) */}
          <h1
            style={{
              fontFamily: "'Quicksand', -apple-system, sans-serif",
              fontSize: 'clamp(34px, 3.8vw, 54px)',
              fontWeight: 700,
              letterSpacing: '0.04em',
              lineHeight: 1.15,
              color: HEADING_COLOR,
              margin: '0 0 18px 0',
              textTransform: 'uppercase',
            }}
          >
            ONE STOP DENTAL CLINIC
          </h1>

          {/* Description Paragraph */}
          <p
            style={{
              fontFamily: "'Quicksand', sans-serif",
              fontSize: 'clamp(14px, 1.2vw, 16px)',
              fontWeight: 500,
              lineHeight: 1.7,
              color: BODY_COLOR,
              margin: '0 0 32px 0',
              maxWidth: '520px',
            }}
          >
            AI-assisted dental panoramic radiograph examination, tooth-wise pathology screening,
            and clinical pre-authorization reporting. Secure, fast, and local-first on your machine.
          </p>

          {/* Cyan Rounded Pill Button: "read more >" / Start Examination */}
          <button
            type="button"
            onClick={onStartExamination}
            style={{
              padding: '12px 36px',
              borderRadius: '9999px',
              border: 'none',
              backgroundColor: CYAN_BTN,
              color: '#ffffff',
              fontFamily: "'Quicksand', sans-serif",
              fontSize: '15px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 16px rgba(1, 226, 254, 0.45)',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 8px 24px rgba(1, 226, 254, 0.65)';
              e.currentTarget.style.filter = 'brightness(1.05)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 4px 16px rgba(1, 226, 254, 0.45)';
              e.currentTarget.style.filter = 'none';
            }}
          >
            <span>read more</span>
            <ChevronRight size={18} strokeWidth={2.8} />
          </button>
        </div>
      </div>

      {/* ═══ 3. BOTTOM FEATURE STRIP (5 CLINICAL PILLARS) ══════════════════════ */}
      <div
        style={{
          width: '100%',
          maxWidth: '1200px',
          margin: '0 auto 20px',
          padding: '14px 40px',
          zIndex: 30,
          boxSizing: 'border-box',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            width: '100%',
            padding: '14px 24px',
            borderRadius: '16px',
            backgroundColor: isDark ? 'rgba(9, 19, 34, 0.75)' : 'rgba(255, 255, 255, 0.85)',
            backdropFilter: 'blur(10px)',
            border: isDark ? '1px solid rgba(1, 226, 254, 0.25)' : '1px solid rgba(0, 132, 255, 0.15)',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)',
          }}
        >
          {[
            { icon: <Scan size={18} strokeWidth={2} />, l1: 'AI-Powered', l2: 'Screening' },
            { icon: <Box size={18} strokeWidth={2} />, l1: '3D Dental', l2: 'Anatomy' },
            { icon: <ShieldCheck size={18} strokeWidth={2} />, l1: 'Accurate', l2: 'FDI Mapping' },
            { icon: <FileText size={18} strokeWidth={2} />, l1: 'Clinical', l2: 'Report' },
            { icon: <Lock size={18} strokeWidth={2} />, l1: 'Local-First', l2: 'Privacy' },
          ].map((item, idx, arr) => (
            <React.Fragment key={idx}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  color: isDark ? '#ffffff' : '#0b2238',
                }}
              >
                <div style={{ color: BLUE }}>{item.icon}</div>
                <div style={{ fontSize: '12px', fontWeight: 700, lineHeight: 1.25 }}>
                  <div>{item.l1}</div>
                  <div style={{ color: BODY_COLOR, fontWeight: 600 }}>{item.l2}</div>
                </div>
              </div>
              {idx < arr.length - 1 && (
                <div style={{ height: '26px', width: '1px', backgroundColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,132,255,0.15)' }} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Floating animation keyframes */}
      <style>{`
        @keyframes floatChair {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }
      `}</style>
    </section>
  );
};
