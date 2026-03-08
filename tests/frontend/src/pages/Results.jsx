import { useState } from 'react';
import { CheckCircle, Circle, AlertTriangle, FileX, ChevronDown, ChevronUp, Share2, Home, RotateCcw } from 'lucide-react';
import Nav from '../components/Nav';
import { useLanguage } from '../context/LanguageContext';
import ScoreRing from '../components/ScoreRing';

const SCHEME_NAMES = {
  'pm-kisan': 'PM-KISAN', 'pm_kisan': 'PM-KISAN',
  'ayushman': 'Ayushman Bharat', 'ayushman_bharat': 'Ayushman Bharat',
  'ration': 'Ration Card', 'ration_card': 'Ration Card',
  'aadhaar': 'Aadhaar Services', 'aadhaar_services': 'Aadhaar Services',
  'pension': 'Social Pension', 'social_pension': 'Social Pension',
};

const MOCK_ACTIONS = [
  { id: 'a1', title: 'Upload Land Records', titleHi: 'भूमि रिकॉर्ड अपलोड करें', priority: 1, time: '2–3 days', done: false, cat: 'UPLOAD', steps: ['Visit Tehsildar office', 'Request Khasra/Khatauni copy', 'Upload scanned copy'] },
  { id: 'a2', title: 'Verify Aadhaar Details', titleHi: 'आधार विवरण सत्यापित करें', priority: 2, time: '1 day', done: false, cat: 'VERIFY', steps: ['Check name matches Aadhaar exactly', 'Verify date of birth', 'Correct via UIDAI if needed'] },
  { id: 'a3', title: 'Attach Bank Passbook', titleHi: 'बैंक पासबुक संलग्न करें', priority: 3, time: '30 min', done: true, cat: 'UPLOAD', steps: ['Take clear photo of first page', 'Ensure account number is visible'] },
];

function getRisk(score) {
  if (score >= 90) return { label: 'Low Risk', hi: 'कम जोखिम', color: 'var(--emerald)', bg: 'var(--emerald-bg)', border: 'var(--emerald-border)', badge: 'badge-green', icon: '✅', fillClass: 'fill-green' };
  if (score >= 70) return { label: 'Medium Risk', hi: 'मध्यम जोखिम', color: 'var(--yellow)', bg: 'var(--yellow-bg)', border: 'rgba(217,119,6,0.25)', badge: 'badge-yellow', icon: '⚠️', fillClass: 'fill-yellow' };
  return { label: 'High Risk', hi: 'अधिक जोखिम', color: 'var(--red)', bg: 'var(--red-bg)', border: 'var(--red-border)', badge: 'badge-red', icon: '🚨', fillClass: 'fill-red' };
}

function ActionCard({ action, onToggle }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`action-card${action.done ? ' done' : ''}`}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <button className={`check-btn${action.done ? ' checked' : ''}`} onClick={() => onToggle(action.id)}>
          {action.done ? <CheckCircle size={13} color="#fff" fill="#fff" /> : null}
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontWeight: 700, fontSize: '0.9rem', color: action.done ? 'var(--text3)' : 'var(--text)', textDecoration: action.done ? 'line-through' : 'none' }}>
              {action.title}
            </span>
            <span className={`badge badge-${action.cat === 'VERIFY' ? 'yellow' : 'blue'}`} style={{ fontSize: '0.65rem' }}>{action.cat}</span>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text3)', marginBottom: 8 }}>
            {action.titleHi} · ⏱ {action.time}
          </div>
          <button onClick={() => setOpen(!open)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text3)', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 4, padding: 0, transition: 'color 0.2s' }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--saffron)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text3)'}>
            {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {open ? 'Hide steps' : 'Show steps'}
          </button>
          {open && (
            <div className="anim-slide-down" style={{ marginTop: 12 }}>
              {action.steps.map((s, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 7, alignItems: 'flex-start' }}>
                  <div style={{ width: 20, height: 20, borderRadius: '50%', background: 'var(--saffron-bg)', border: '1px solid var(--saffron-border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.62rem', fontWeight: 700, color: 'var(--saffron)', flexShrink: 0 }}>{i + 1}</div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text2)', lineHeight: 1.5 }}>{s}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}



export default function Results({ data, onBack, onHome }) {
  const { t } = useLanguage();
  const TABS = [
    { id:'overview', label:t('overview') },
    { id:'actions',  label:t('actions')  },
    { id:'details',  label:t('details')  },
  ];
  const [actions, setActions] = useState(MOCK_ACTIONS);
  const [tab, setTab] = useState('overview');

  if (!data) return null;

  const score = data.readiness_score || 0;
  const risk = getRisk(score);
  const scheme = SCHEME_NAMES[data.scheme_detected] || data.scheme_detected || 'Government Document';
  const missing = data.missing_fields || [];
  const missingDocs = data.missing_documents || [];
  const doneCount = actions.filter(a => a.done).length;
  const donePct = Math.round((doneCount / actions.length) * 100);
  const pendingCount = actions.filter(a => !a.done).length;

  const toggle = (id) => setActions(prev => prev.map(a => a.id === id ? { ...a, done: !a.done } : a));

  const share = () => {
    const text = `My CAIS document readiness score: ${score}/100 (${risk.label}) for ${scheme}`;
    if (navigator.share) navigator.share({ title: 'CAIS Result', text });
    else navigator.clipboard?.writeText(text);
  };

  return (
    <div className="page" style={{ background: 'var(--bg)', overflowY: 'auto' }}>
      <Nav onBack={onBack} title={t('results')} />

      <div className="container" style={{ paddingBottom: 90 }}>
        {/* Score hero */}
        <div className="anim-up score-hero">
          <ScoreRing score={score} size={window.innerWidth < 380 ? 110 : 130} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className={`badge ${risk.badge}`} style={{ marginBottom: 8 }}>{risk.icon} {risk.label}</div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text3)', marginBottom: 6 }}>{risk.hi}</p>
            <h3 style={{ fontSize: 'clamp(0.92rem, 2vw, 1.1rem)', marginBottom: 4 }}>{scheme}</h3>
            <p style={{ fontSize: '0.73rem', color: 'var(--text3)' }}>
              {data.engine_used || 'OpenBharatOCR'} · {data.ocr_confidence ? Math.round(data.ocr_confidence * 100) + '% conf.' : ''}
            </p>
          </div>
        </div>

        {/* Risk banner */}
        <div className="anim-up d1" style={{ padding: '13px 16px', background: risk.bg, border: `1.5px solid ${risk.border}`, borderRadius: 14, marginBottom: 20, fontSize: '0.88rem', color: risk.color, fontWeight: 500 }}>
          {score >= 90 ? '✅ Your document looks well-prepared. Ready to submit!' :
           score >= 70 ? '⚠️ A few issues need attention. Review actions below.' :
           '🚨 Several critical issues found. Complete all actions before submitting.'}
        </div>

        {/* Progress tracker */}
        <div className="anim-up d2 card" style={{ marginBottom: 22, padding: '16px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 9 }}>
            <span style={{ fontWeight: 700, fontSize: '0.88rem' }}>Task Completion</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: donePct >= 100 ? 'var(--emerald)' : 'var(--saffron)', fontWeight: 700 }}>
              {doneCount}/{actions.length}
            </span>
          </div>
          <div className="progress-track sm">
            <div className={`progress-fill ${donePct >= 100 ? 'fill-green' : 'fill-saffron'}`} style={{ width: `${donePct}%` }} />
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text3)', marginTop: 7 }}>
            {donePct >= 100 ? '🎉 All tasks complete — ready to submit!' : `${pendingCount} task${pendingCount > 1 ? 's' : ''} remaining`}
          </p>
        </div>

        {/* Tabs */}
        <div className="anim-up d2 tab-bar" style={{ marginBottom: 20 }}>
          {TABS.map(t => (
            <button key={t.id} className={`tab-btn${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)}>
              {t.id === 'actions' ? `Actions (${pendingCount})` : t.label}
            </button>
          ))}
        </div>

        {/* Overview tab */}
        {tab === 'overview' && (
          <div className="anim-fade">
            {/* Score breakdown */}
            <div className="card" style={{ marginBottom: 16 }}>
              <p style={{ fontSize: '0.72rem', color: 'var(--text4)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 16 }}>Score Breakdown</p>
              {[
                { label: 'Fields Completeness', weight: '60%', val: Math.min(100, score + 14) },
                { label: 'Documents Present',   weight: '30%', val: Math.max(0, score - 8) },
                { label: 'Validation Pass',      weight: '10%', val: score >= 70 ? 100 : 58 },
              ].map(row => (
                <div key={row.label} style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text2)' }}>{row.label}</span>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text4)', background: 'var(--surface2)', padding: '1px 8px', borderRadius: 99, border: '1px solid var(--border)' }}>{row.weight}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 700, color: row.val >= 90 ? 'var(--emerald)' : row.val >= 70 ? 'var(--yellow)' : 'var(--red)' }}>{row.val}%</span>
                    </div>
                  </div>
                  <div className="progress-track sm">
                    <div className={`progress-fill ${row.val >= 90 ? 'fill-green' : row.val >= 70 ? 'fill-saffron' : 'fill-red'}`} style={{ width: `${row.val}%` }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Missing fields */}
            {missing.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <p style={{ fontSize: '0.72rem', color: 'var(--text4)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>Missing Fields ({missing.length})</p>
                {missing.map((f, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '10px 14px', marginBottom: 8, background: 'var(--red-bg)', border: '1.5px solid var(--red-border)', borderRadius: 12 }}>
                    <FileX size={15} color="var(--red)" style={{ flexShrink: 0 }} />
                    <span style={{ fontSize: '0.85rem', color: 'var(--red)' }}>{typeof f === 'string' ? f : f.field_name || JSON.stringify(f)}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Missing docs */}
            {missingDocs.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <p style={{ fontSize: '0.72rem', color: 'var(--text4)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>Missing Documents ({missingDocs.length})</p>
                {missingDocs.map((d, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '10px 14px', marginBottom: 8, background: 'var(--yellow-bg)', border: '1.5px solid rgba(217,119,6,0.25)', borderRadius: 12 }}>
                    <AlertTriangle size={15} color="var(--yellow)" style={{ flexShrink: 0 }} />
                    <span style={{ fontSize: '0.85rem', color: 'var(--yellow)' }}>{typeof d === 'string' ? d : d.doc_name || JSON.stringify(d)}</span>
                  </div>
                ))}
              </div>
            )}

            {/* OCR preview */}
            {data.text_preview && (
              <div className="card-flat" style={{ padding: 16 }}>
                <p style={{ fontSize: '0.72rem', color: 'var(--text4)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>Extracted Text Preview</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text2)', fontFamily: 'var(--font-mono)', lineHeight: 1.7 }}>{data.text_preview}</p>
              </div>
            )}
          </div>
        )}

        {/* Actions tab */}
        {tab === 'actions' && (
          <div className="anim-fade">
            <p style={{ fontSize: '0.85rem', color: 'var(--text2)', marginBottom: 18 }}>Complete these tasks to improve your readiness score.</p>
            {[...actions].sort((a, b) => a.done - b.done || a.priority - b.priority).map(a => (
              <ActionCard key={a.id} action={a} onToggle={toggle} />
            ))}
          </div>
        )}

        {/* Details tab */}
        {tab === 'details' && (
          <div className="anim-fade">
            <div className="card">
              {[
                { label: 'Document ID',       val: data.document_id },
                { label: 'Status',             val: data.status },
                { label: 'Document Type',      val: data.document_type },
                { label: 'Scheme Detected',    val: data.scheme_detected },
                { label: 'Scheme Confidence',  val: data.scheme_confidence != null ? `${Math.round(data.scheme_confidence * 100)}%` : null },
                { label: 'OCR Engine',         val: data.engine_used },
                { label: 'OCR Confidence',     val: data.ocr_confidence != null ? `${Math.round(data.ocr_confidence * 100)}%` : null },
                { label: 'Image Quality',      val: data.quality_score != null ? `${data.quality_score}/100` : null },
                { label: 'Risk Level',         val: data.risk_level },
              ].filter(r => r.val).map((row, i, arr) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '11px 0', borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none' }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text3)' }}>{row.label}</span>
                  <span style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--text)', fontWeight: 600 }}>{String(row.val)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom action bar */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        padding: '14px 20px 24px',
        background: 'linear-gradient(to top, var(--bg) 65%, transparent)',
        display: 'flex', gap: 10,
        maxWidth: 520, margin: '0 auto',
      }}>
        <button className="btn btn-secondary" style={{ flex: 1, gap: 6 }} onClick={onHome}>
          <Home size={15} /> {t('home')}
        </button>
        <button className="btn btn-secondary" style={{ flex: 1, gap: 6 }} onClick={onBack}>
          <RotateCcw size={14} /> {t('newScan')}
        </button>
        <button className="btn btn-primary" style={{ flex: 2, gap: 6 }} onClick={share}>
          <Share2 size={15} /> {t('share')}
        </button>
      </div>
    </div>
  );
}
