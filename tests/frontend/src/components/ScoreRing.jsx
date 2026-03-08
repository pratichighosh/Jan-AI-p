import { useEffect, useState } from 'react';

const RADIUS = 46;
const CIRC = 2 * Math.PI * RADIUS;

function getColor(score) {
  if (score >= 90) return { stroke: '#16a34a', text: '#16a34a', label: 'Low Risk', labelHi: 'कम जोखिम', badge: 'badge-green', icon: '✅' };
  if (score >= 70) return { stroke: '#d97706', text: '#d97706', label: 'Medium Risk', labelHi: 'मध्यम जोखिम', badge: 'badge-yellow', icon: '⚠️' };
  return { stroke: '#dc2626', text: '#dc2626', label: 'High Risk', labelHi: 'अधिक जोखिम', badge: 'badge-red', icon: '🚨' };
}

export default function ScoreRing({ score = 0, size = 130, animated = true }) {
  const [shown, setShown] = useState(animated ? 0 : score);
  const colors = getColor(score);

  useEffect(() => {
    if (!animated) { setShown(score); return; }
    let frame, id;
    const start = performance.now();
    const dur = 1300;
    const tick = (now) => {
      const t = Math.min((now - start) / dur, 1);
      const e = 1 - Math.pow(1 - t, 4);
      setShown(Math.round(score * e));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    id = setTimeout(() => { frame = requestAnimationFrame(tick); }, 200);
    return () => { clearTimeout(id); cancelAnimationFrame(frame); };
  }, [score, animated]);

  const offset = CIRC - (shown / 100) * CIRC;
  const cx = size / 2;

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ position: 'absolute', transform: 'rotate(-90deg)' }}>
        <circle cx={cx} cy={cx} r={RADIUS} fill="none" stroke="var(--bg3)" strokeWidth="9" />
        <circle cx={cx} cy={cx} r={RADIUS} fill="none"
          stroke={colors.stroke} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={CIRC} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.04s linear', filter: `drop-shadow(0 0 6px ${colors.stroke}55)` }}
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: size * 0.21, fontWeight: 700, color: colors.text, lineHeight: 1 }}>
          {shown}
        </div>
        <div style={{ fontSize: size * 0.085, color: 'var(--text3)', marginTop: 2 }}>/ 100</div>
      </div>
    </div>
  );
}
