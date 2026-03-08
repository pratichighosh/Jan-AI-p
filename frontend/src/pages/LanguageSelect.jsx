import { useState } from 'react';
import { Check } from 'lucide-react';
import Nav from '../components/Nav';
import { useLanguage } from '../context/LanguageContext';

const FEATURED = ['hi','en','bn','ta','te','mr','gu','kn','ml','pa'];

export default function LanguageSelect({ onComplete }) {
  const { languages, setLanguage, langCode, t } = useLanguage();
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(langCode || '');
  const [showAll, setShowAll] = useState(false);

  const list = search.trim()
    ? languages.filter(l => l.name.toLowerCase().includes(search.toLowerCase()) || l.english.toLowerCase().includes(search.toLowerCase()))
    : showAll ? languages : languages.filter(l => FEATURED.includes(l.code));

  const handleSelect = (code) => {
    setSelected(code);
    setTimeout(() => { setLanguage(code); onComplete(); }, 260);
  };

  const total = languages.length;

  return (
    <div className="page" style={{ background:'var(--bg)', overflowY:'auto' }}>
      <Nav showBrand />
      <div className="container" style={{ paddingTop:32, paddingBottom:60 }}>
        <div className="anim-up" style={{ marginBottom:28 }}>
          <div style={{ width:56, height:56, borderRadius:16, background:'var(--saffron-bg)', border:'1.5px solid var(--saffron-border)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:28, marginBottom:16 }}>🌐</div>
          <h2 style={{ marginBottom:6 }}>{t('chooseLanguage')}</h2>
          <p style={{ color:'var(--text3)', fontSize:'0.9rem' }}>अपनी भाषा चुनें · தேர்ந்தெடுங்கள் · আপনার ভাষা</p>
        </div>

        {/* Search */}
        <div className="anim-up d1 input-icon-wrap" style={{ marginBottom:22 }}>
          <span className="icon" style={{ position:'absolute', left:14, top:'50%', transform:'translateY(-50%)', color:'var(--text4)' }}>🔍</span>
          <input
            className="input"
            style={{ paddingLeft:40 }}
            placeholder={t('searchLang')}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {!search && (
          <p style={{ fontSize:'0.72rem', color:'var(--text4)', letterSpacing:'0.06em', textTransform:'uppercase', marginBottom:14 }}>
            {showAll ? t('allLangs').replace('{n}', total) : t('popularLangs')}
          </p>
        )}

        <div className="anim-up d2" style={{ display:'grid', gridTemplateColumns:'repeat(2,1fr)', gap:10 }}>
          {list.map(lang => (
            <button
              key={lang.code}
              className={`lang-card${selected === lang.code ? ' selected' : ''}`}
              onClick={() => handleSelect(lang.code)}
              style={{ position:'relative' }}
            >
              {selected === lang.code && (
                <div style={{ position:'absolute', top:9, right:9, width:20, height:20, borderRadius:'50%', background:'var(--saffron)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                  <Check size={11} color="#fff" strokeWidth={3} />
                </div>
              )}
              <div style={{ fontSize:'1.15rem', fontWeight:700, color:selected===lang.code?'var(--saffron)':'var(--text)', marginBottom:3, lineHeight:1.3 }}>
                {lang.name}
              </div>
              <div style={{ fontSize:'0.72rem', color:'var(--text3)' }}>{lang.english}</div>
            </button>
          ))}
        </div>

        {!search && !showAll && (
          <button className="btn btn-ghost" style={{ width:'100%', marginTop:14, color:'var(--saffron)' }} onClick={() => setShowAll(true)}>
            {t('showAll').replace('{n}', total)}
          </button>
        )}
      </div>

      <div style={{ textAlign:'center', padding:'0 20px 32px' }}>
        <p style={{ fontSize:'0.7rem', color:'var(--text4)' }}>{t('poweredBy')}</p>
      </div>
    </div>
  );
}
