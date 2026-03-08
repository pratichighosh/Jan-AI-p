import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileImage, FileText, Camera, X, AlertCircle } from 'lucide-react';
import Nav from '../components/Nav';
import { useLanguage } from '../context/LanguageContext';
import { uploadDocument } from '../api/client';

const PROCESSING_STEPS_KEY = ['uploadTitle','uploadTitle','uploadTitle','uploadTitle','uploadTitle'];

export default function UploadPage({ flowType = 'form', onBack, onResult }) {
  const { langCode, t } = useLanguage();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stepMsg, setStepMsg] = useState('');

  const PROCESSING_STEPS = [
    t('uploadTitle') !== 'uploadTitle' ? t('uploadTitle') + '…' : 'Uploading…',
    'Enhancing image quality…',
    'Running OCR engine…',
    'Classifying document…',
    'Calculating readiness score…',
  ];

  const flowColor = flowType === 'rejected' ? 'var(--red)' : flowType === 'check' ? 'var(--emerald)' : 'var(--saffron)';
  const flowTitle = flowType === 'rejected' ? t('flow2Title') : flowType === 'check' ? t('flow3Title') : t('flow1Title');

  const onDrop = useCallback((accepted, rejected) => {
    setError('');
    if (rejected.length) {
      const e = rejected[0].errors[0];
      if (e.code === 'file-too-large') setError('File too large. Maximum 10 MB.');
      else if (e.code === 'file-invalid-type') setError('Only JPG, PNG or PDF accepted.');
      else setError(e.message);
      return;
    }
    if (!accepted.length) return;
    const f = accepted[0];
    setFile(f);
    setPreview(f.type.startsWith('image/') ? URL.createObjectURL(f) : null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/jpeg':[], 'image/png':[], 'application/pdf':[] },
    maxFiles: 1,
    maxSize: 10*1024*1024,
  });

  const handleSubmit = async () => {
    if (!file) return;
    setUploading(true); setError(''); setProgress(0);
    let si = 0;
    const targets = [18,40,62,82,96];
    const iv = setInterval(() => {
      if (si < PROCESSING_STEPS.length) { setStepMsg(PROCESSING_STEPS[si]); setProgress(targets[si]); si++; }
    }, 900);
    try {
      const result = await uploadDocument(file, langCode||'hi', flowType, null);
      clearInterval(iv); setProgress(100);
      try {
        const prev = JSON.parse(localStorage.getItem('cais_recent')||'[]');
        localStorage.setItem('cais_recent', JSON.stringify([
          { id:result.data?.document_id, scheme:result.data?.scheme_detected||'Document', score:result.data?.readiness_score||0, date:new Date().toLocaleDateString('en-IN') },
          ...prev.slice(0,4),
        ]));
      } catch {}
      setTimeout(() => onResult(result.data), 450);
    } catch (err) {
      clearInterval(iv); setUploading(false); setProgress(0);
      const d = err.response?.data?.detail;
      setError(typeof d==='object' ? (d.message_en||d.message||'Upload failed.') : (d||'Upload failed. Check connection.'));
    }
  };

  if (uploading) {
    return (
      <div className="page" style={{ background:'var(--bg)', alignItems:'center', justifyContent:'center', padding:24, minHeight:'100dvh' }}>
        <div style={{ textAlign:'center', maxWidth:340, width:'100%' }}>
          <div style={{ position:'relative', width:110, height:110, margin:'0 auto 32px' }}>
            <svg width="110" height="110" style={{ position:'absolute', transform:'rotate(-90deg)' }}>
              <circle cx="55" cy="55" r="46" fill="none" stroke="var(--border)" strokeWidth="8" />
              <circle cx="55" cy="55" r="46" fill="none" stroke={flowColor} strokeWidth="8" strokeLinecap="round"
                strokeDasharray={`${2*Math.PI*46}`}
                strokeDashoffset={`${2*Math.PI*46*(1-progress/100)}`}
                style={{ transition:'stroke-dashoffset 0.6s ease' }}
              />
            </svg>
            <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center' }}>
              <span style={{ fontFamily:'var(--font-mono)', fontWeight:700, fontSize:'1.1rem', color:flowColor }}>{progress}%</span>
            </div>
          </div>
          <h2 style={{ marginBottom:8, fontSize:'1.3rem' }}>{t('uploadTitle')}</h2>
          <p style={{ marginBottom:28, fontSize:'0.9rem' }}>{stepMsg}</p>
          <div style={{ display:'flex', flexWrap:'wrap', justifyContent:'center', gap:6 }}>
            {['OpenBharatOCR','Bhashini API','Scheme DB'].map((s,i) => (
              <span key={i} className={`badge badge-${['saffron','blue','green'][i]}`}>{s}</span>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page" style={{ background:'var(--bg)', overflowY:'auto' }}>
      <Nav onBack={onBack} title={flowTitle} />
      <div className="container" style={{ paddingTop:28, paddingBottom:60 }}>
        <div className="anim-up" style={{ marginBottom:24 }}>
          <h2 style={{ marginBottom:6 }}>{flowTitle}</h2>
        </div>

        <div className="anim-up d1 card-flat" style={{ marginBottom:22, padding:'12px 16px', display:'flex', gap:10, alignItems:'flex-start' }}>
          <span style={{ fontSize:18 }}>💡</span>
          <p style={{ fontSize:'0.82rem', color:'var(--text2)' }}>{t('uploadTip')}</p>
        </div>

        <div className="anim-up d2">
          {!file ? (
            <div {...getRootProps()} className={`dropzone${isDragActive?' active':''}`}>
              <input {...getInputProps()} />
              <div className="dropzone-icon"><Upload size={30} color="var(--saffron)" /></div>
              <h3 style={{ marginBottom:8, fontSize:'1.05rem' }}>{isDragActive ? 'Drop here!' : t('uploadTitle')}</h3>
              <p style={{ fontSize:'0.85rem', marginBottom:22, color:'var(--text3)' }}>{t('uploadDesc')}</p>
              <div style={{ display:'flex', gap:8, justifyContent:'center', flexWrap:'wrap' }}>
                {[{Icon:FileImage,label:'Gallery'},{Icon:Camera,label:'Camera'},{Icon:FileText,label:'PDF'}].map(({Icon,label}) => (
                  <div key={label} className="btn btn-secondary" style={{ padding:'9px 16px', fontSize:'0.82rem', gap:6 }}>
                    <Icon size={14} /> {label}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="card" style={{ padding:0, overflow:'hidden' }}>
              {preview
                ? <div style={{ position:'relative', paddingTop:'52%' }}><img src={preview} alt="Preview" style={{ position:'absolute', inset:0, width:'100%', height:'100%', objectFit:'cover' }} /></div>
                : <div style={{ height:100, display:'flex', alignItems:'center', justifyContent:'center', background:'var(--surface2)' }}><FileText size={44} color="var(--text4)" /></div>
              }
              <div style={{ padding:'14px 16px', display:'flex', gap:12, alignItems:'center' }}>
                <div style={{ width:36, height:36, borderRadius:10, background:'var(--emerald-bg)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>✅</div>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ fontWeight:600, fontSize:'0.88rem', color:'var(--text)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{file.name}</div>
                  <div style={{ fontSize:'0.75rem', color:'var(--text3)' }}>{(file.size/1024/1024).toFixed(2)} MB · {file.type.split('/')[1].toUpperCase()}</div>
                </div>
                <button onClick={() => { setFile(null); setPreview(null); setError(''); }}
                  style={{ background:'none', border:'none', cursor:'pointer', color:'var(--text4)', padding:4, borderRadius:6, transition:'color 0.2s' }}
                  onMouseEnter={e => e.currentTarget.style.color='var(--red)'}
                  onMouseLeave={e => e.currentTarget.style.color='var(--text4)'}>
                  <X size={18} />
                </button>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="anim-up" style={{ marginTop:14, padding:'13px 16px', background:'var(--red-bg)', border:'1.5px solid var(--red-border)', borderRadius:14, display:'flex', gap:10, alignItems:'flex-start' }}>
            <AlertCircle size={17} color="var(--red)" style={{ flexShrink:0, marginTop:1 }} />
            <p style={{ fontSize:'0.85rem', color:'var(--red)' }}>{error}</p>
          </div>
        )}

        <div className="anim-up d3" style={{ marginTop:26 }}>
          <button className="btn btn-primary" style={{ width:'100%', padding:'15px' }} disabled={!file} onClick={handleSubmit}>
            {t('analyzeBtn')}
          </button>
          <p style={{ textAlign:'center', fontSize:'0.73rem', color:'var(--text4)', marginTop:12 }}>
            {t('poweredBy')}
          </p>
        </div>
      </div>
    </div>
  );
}
