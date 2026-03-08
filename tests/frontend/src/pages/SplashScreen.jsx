import { useEffect, useState } from 'react';
import { healthCheck } from '../api/client';
import { useTheme } from '../context/ThemeContext';
import IndiaMap from '../components/IndiaMap';

export default function SplashScreen({ onComplete }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('Starting…');
  const { isDark } = useTheme();

  useEffect(() => {
    const steps = [
      { target: 28, label: 'Loading resources…',         delay: 450 },
      { target: 58, label: 'Preparing language packs…',  delay: 700 },
      { target: 84, label: 'Connecting to CAIS…',        delay: 600 },
      { target: 100, label: 'Ready!',                    delay: 350 },
    ];
    let cur = 0;
    const run = async (i) => {
      if (i >= steps.length) { setTimeout(onComplete, 380); return; }
      const s = steps[i];
      await new Promise(r => setTimeout(r, s.delay));
      if (i === 2) { setStatus('Checking server…'); await healthCheck(); }
      setStatus(s.label);
      const from = cur, to = s.target, dur = s.delay * 0.45;
      const t0 = Date.now();
      const tick = () => {
        const t = Math.min((Date.now() - t0) / dur, 1);
        const e = 1 - Math.pow(1 - t, 3);
        setProgress(Math.round(from + (to - from) * e));
        if (t < 1) requestAnimationFrame(tick);
        else { cur = to; run(i + 1); }
      };
      requestAnimationFrame(tick);
    };
    const id = setTimeout(() => run(0), 120);
    return () => clearTimeout(id);
  }, [onComplete]);

  return (
    <div style={{
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: isDark
        ? 'radial-gradient(ellipse at 30% 20%, rgba(255,107,0,0.10) 0%, transparent 55%), radial-gradient(ellipse at 75% 80%, rgba(21,96,171,0.08) 0%, transparent 55%), #0A1628'
        : 'radial-gradient(ellipse at 30% 20%, rgba(232,93,4,0.06) 0%, transparent 55%), radial-gradient(ellipse at 75% 80%, rgba(21,96,171,0.05) 0%, transparent 55%), #F4F6FB',
      padding: '24px 24px 40px',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Subtle bg rings */}
      {[200, 340, 480].map((r, i) => (
        <div key={i} style={{
          position: 'absolute',
          width: r, height: r,
          borderRadius: '50%',
          border: `1px solid ${isDark ? 'rgba(255,107,0,0.06)' : 'rgba(232,93,4,0.05)'}`,
          left: '50%', top: '50%',
          transform: 'translate(-50%,-50%)',
          pointerEvents: 'none',
        }} />
      ))}

      <div style={{ textAlign: 'center', position: 'relative', zIndex: 1, width: '100%', maxWidth: 360 }}>

        {/* ── INDIA MAP LOGO ── */}
        <div className="anim-float" style={{ marginBottom: 28 }}>
          <div style={{
            width: 100, height: 100,
            borderRadius: '50%',
            background: isDark
              ? 'linear-gradient(135deg, rgba(255,107,0,0.12), rgba(21,96,171,0.10))'
              : 'linear-gradient(135deg, rgba(232,93,4,0.09), rgba(21,96,171,0.07))',
            border: `2.5px solid ${isDark ? 'rgba(255,107,0,0.35)' : 'rgba(232,93,4,0.28)'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto',
            boxShadow: isDark
              ? '0 0 50px rgba(255,107,0,0.18), 0 0 100px rgba(255,107,0,0.06)'
              : '0 0 40px rgba(232,93,4,0.14), 0 8px 32px rgba(232,93,4,0.10)',
            overflow: 'hidden',
            padding: 10,
            position: 'relative',
          }}>
            {/* India Map fills the circle */}
            <IndiaMap mini style={{ width: '100%', height: '100%' }} />
          </div>
        </div>

        {/* Title */}
        <div className="anim-up d1">
          <h1 style={{
            fontSize: 'clamp(3rem, 10vw, 4.5rem)',
            letterSpacing: '-0.025em',
            marginBottom: 8, lineHeight: 1,
          }}>
            <span style={{ color: 'var(--saffron)' }}>C</span>AIS
          </h1>
        </div>

        <div className="anim-up d2" style={{ marginBottom: 6 }}>
          <p style={{
            fontSize: 'clamp(0.95rem, 3vw, 1.05rem)',
            fontWeight: 600,
            color: 'var(--text)',
          }}>
            नागरिक सहायक प्रणाली
          </p>
        </div>

        <div className="anim-up d3" style={{ marginBottom: 44 }}>
          <p style={{
            fontSize: '0.72rem',
            color: 'var(--text4)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}>
            Citizen Application Intelligence System
          </p>
        </div>

        {/* Progress bar */}
        <div className="anim-up d4" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10, fontSize: '0.82rem' }}>
            <span style={{ color: 'var(--text3)' }}>{status}</span>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--saffron)', fontWeight: 700 }}>
              {progress}%
            </span>
          </div>
          <div className="progress-track">
            <div className="progress-fill fill-saffron" style={{ width: `${progress}%` }} />
          </div>
        </div>

        {/* Tagline */}
        <div className="anim-up d5" style={{ marginTop: 38 }}>
          <p style={{ fontSize: '0.9rem', color: 'var(--text3)', fontStyle: 'italic' }}>
            "हर नागरिक का हक़, उनकी भाषा में"
          </p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text4)', marginTop: 5 }}>
            Every citizen's right, in their own language
          </p>
        </div>

      </div>

      {/* Bottom */}
      <div className="anim-fade d6" style={{
        position: 'absolute', bottom: 24, left: '50%', transform: 'translateX(-50%)',
        whiteSpace: 'nowrap',
      }}>
        <span style={{ fontSize: '0.7rem', color: 'var(--text4)' }}>
          Powered by Bhashini · 22 Indian Languages
        </span>
      </div>
    </div>
  );
}
