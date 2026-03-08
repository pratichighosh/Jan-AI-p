import { FileText, XCircle, FolderCheck, ChevronRight, Globe, Shield, Zap } from 'lucide-react';
import Nav from '../components/Nav';
import IndiaMap from '../components/IndiaMap';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';

const SCHEMES = [
  { icon: '🌾', name: 'PM-KISAN',        color: '#16a34a' },
  { icon: '🏥', name: 'Ayushman Bharat', color: '#2563eb' },
  { icon: '🍚', name: 'Ration Card',     color: '#d97706' },
  { icon: '🪪', name: 'Aadhaar',         color: '#7c3aed' },
  { icon: '👴', name: 'Social Pension',  color: '#db2777' },
];

export default function Home({ onUpload, onLanguageClick }) {
  const { t, heroTitle1, heroTitle2, lang } = useLanguage();
  const { isDark } = useTheme();

  const FLOWS = [
    { id:'form',     Icon:FileText,   color:'var(--saffron)', bg:'var(--saffron-bg)', border:'var(--saffron-border)', title:t('flow1Title'), sub:t('flow1Sub'), desc:t('flow1Desc') },
    { id:'rejected', Icon:XCircle,    color:'var(--red)',     bg:'var(--red-bg)',     border:'var(--red-border)',     title:t('flow2Title'), sub:t('flow2Sub'), desc:t('flow2Desc') },
    { id:'check',    Icon:FolderCheck,color:'var(--emerald)', bg:'var(--emerald-bg)',border:'var(--emerald-border)', title:t('flow3Title'), sub:t('flow3Sub'), desc:t('flow3Desc') },
  ];

  const recent = (() => { try { return JSON.parse(localStorage.getItem('cais_recent')||'[]'); } catch { return []; } })();

  return (
    <div className="page" style={{ background:'var(--bg)', overflowY:'auto' }}>
      <Nav onLanguageClick={onLanguageClick} />

      {/* ── HERO ── */}
      <div style={{
        display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(280px, 1fr))',
        minHeight:'clamp(260px,42vh,420px)',
        background: isDark
          ? 'linear-gradient(135deg,#0D1D38 0%,#112240 100%)'
          : 'linear-gradient(135deg,#FFF9F5 0%,#EEF4FF 100%)',
        borderBottom:'1px solid var(--border)', overflow:'hidden',
      }}>
        {/* Left */}
        <div style={{ padding:'clamp(28px,5vw,60px)', display:'flex', flexDirection:'column', justifyContent:'center' }}>
          <div className="anim-up" style={{ marginBottom:12 }}>
            <span className="badge badge-saffron">🇮🇳 {t('government')}</span>
          </div>
          <h1 className="anim-up d1" style={{ marginBottom:12 }}>
            {heroTitle1()}<br />
            <span style={{ color:'var(--saffron)' }}>{heroTitle2()}</span>
          </h1>
          <p className="anim-up d2" style={{ maxWidth:420, marginBottom:22, fontSize:'clamp(0.88rem,2vw,1rem)' }}>
            {t('heroDesc')}
          </p>
          <div className="anim-up d3" style={{ display:'flex', gap:10, flexWrap:'wrap' }}>
            <button className="btn btn-primary" onClick={() => onUpload('form')}>{t('getStarted')}</button>
            <button className="btn btn-secondary" onClick={onLanguageClick}>
              <Globe size={15} /> {lang?.name || t('changeLanguage')}
            </button>
          </div>
        </div>

        {/* Right — India map */}
        <div className="anim-fade d2" style={{ display:'flex', alignItems:'center', justifyContent:'center', padding:20, minHeight:180 }}>
          <div style={{ position:'relative', width:'min(380px,55vw)', aspectRatio:'4/5' }}>
            <IndiaMap style={{ width:'100%', height:'100%' }} />
          </div>
        </div>
      </div>

      <div className="container-lg" style={{ paddingBottom:70 }}>
        {/* Stats */}
        <div style={{ padding:'clamp(24px,4vw,40px) 0 0' }}>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:'clamp(8px,2vw,16px)', marginBottom:36 }}>
            {[{v:'22',l:'Languages'},{v:'5+',l:'Schemes'},{v:'94%',l:'Accuracy'}].map(({v,l}) => (
              <div key={l} className="stat-card anim-up d1">
                <div className="stat-value">{v}</div>
                <div style={{ fontSize:'0.78rem', color:'var(--text3)', marginTop:5, fontWeight:600 }}>{l}</div>
              </div>
            ))}
          </div>

          {/* Flows */}
          <p className="anim-up d1" style={{ fontSize:'0.72rem', color:'var(--text4)', letterSpacing:'0.06em', textTransform:'uppercase', marginBottom:14 }}>
            {t('whatNeed')}
          </p>
          <div style={{ display:'flex', flexDirection:'column', gap:12, marginBottom:36 }}>
            {FLOWS.map(({ id, Icon, color, bg, border, title, sub, desc }, i) => (
              <button key={id} className={`flow-card anim-up d${i+2}`} onClick={() => onUpload(id)}>
                <div className="flow-icon" style={{ width:50, height:50, borderRadius:14, flexShrink:0, background:bg, border:`1.5px solid ${border}`, display:'flex', alignItems:'center', justifyContent:'center' }}>
                  <Icon size={22} color={color} />
                </div>
                <div style={{ flex:1, textAlign:'left' }}>
                  <div style={{ fontWeight:700, fontSize:'clamp(0.88rem,2vw,0.97rem)', color:'var(--text)', marginBottom:3 }}>{title}</div>
                  <div style={{ fontSize:'0.78rem', color:'var(--text3)' }}>{sub} · {desc}</div>
                </div>
                <ChevronRight size={18} color="var(--text4)" style={{ flexShrink:0 }} />
              </button>
            ))}
          </div>

          {/* Schemes */}
          <p className="anim-up d4" style={{ fontSize:'0.72rem', color:'var(--text4)', letterSpacing:'0.06em', textTransform:'uppercase', marginBottom:14 }}>
            {t('schemesLabel')}
          </p>
          <div className="anim-up d4" style={{ display:'flex', gap:10, overflowX:'auto', paddingBottom:8 }}>
            {SCHEMES.map(s => (
              <div key={s.name} className="scheme-pill">
                <span style={{ fontSize:26 }}>{s.icon}</span>
                <span style={{ fontSize:'0.72rem', fontWeight:700, color:'var(--text)', textAlign:'center', lineHeight:1.3 }}>{s.name}</span>
              </div>
            ))}
          </div>

          {/* Recent */}
          {recent.length > 0 && (
            <div style={{ marginTop:32 }}>
              <p style={{ fontSize:'0.72rem', color:'var(--text4)', letterSpacing:'0.06em', textTransform:'uppercase', marginBottom:14 }}>{t('recentActivity')}</p>
              {recent.slice(0,3).map((d,i) => (
                <div key={i} className="card" style={{ marginBottom:10, display:'flex', gap:14, alignItems:'center', padding:'14px 16px' }}>
                  <div style={{ width:38, height:38, borderRadius:10, background:'var(--saffron-bg)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                    <FileText size={17} color="var(--saffron)" />
                  </div>
                  <div style={{ flex:1 }}>
                    <div style={{ fontWeight:600, fontSize:'0.88rem', color:'var(--text)' }}>{d.scheme||'Document'}</div>
                    <div style={{ fontSize:'0.75rem', color:'var(--text3)' }}>Score: {d.score}/100 · {d.date}</div>
                  </div>
                  <div style={{ fontWeight:700, fontFamily:'var(--font-mono)', color: d.score>=90?'var(--emerald)':d.score>=70?'var(--yellow)':'var(--red)' }}>{d.score}</div>
                </div>
              ))}
            </div>
          )}

          {/* How it works */}
          <div style={{ marginTop:36 }}>
            <p style={{ fontSize:'0.72rem', color:'var(--text4)', letterSpacing:'0.06em', textTransform:'uppercase', marginBottom:18 }}>{t('howWorks')}</p>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:12 }}>
              {[
                { emoji:'📄', step:t('step1'), desc:t('step1d') },
                { emoji:'🤖', step:t('step2'), desc:t('step2d') },
                { emoji:'✅', step:t('step3'), desc:t('step3d') },
              ].map(({ emoji, step, desc }) => (
                <div key={step} className="card-flat" style={{ textAlign:'center', padding:'clamp(14px,3vw,20px) 10px' }}>
                  <div style={{ fontSize:'clamp(1.4rem,4vw,2rem)', marginBottom:8 }}>{emoji}</div>
                  <div style={{ fontWeight:700, fontSize:'0.85rem', color:'var(--text)', marginBottom:4 }}>{step}</div>
                  <div style={{ fontSize:'0.72rem', color:'var(--text3)' }}>{desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}