import { ChevronLeft, Globe, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useLanguage } from '../context/LanguageContext';

export default function Nav({ onBack, title, onLanguageClick, showBrand = true }) {
  const { isDark, toggle } = useTheme();
  const { lang, t } = useLanguage();

  return (
    <nav className="nav" style={{ position:'sticky', top:0, zIndex:200 }}>
      <div style={{ display:'flex', alignItems:'center', gap:10, flex:1 }}>
        {onBack ? (
          <button className="back-btn" onClick={onBack}>
            <ChevronLeft size={16} />
            <span>{t('back')}</span>
          </button>
        ) : showBrand ? (
          <div className="nav-brand">
            <span style={{ fontSize:20 }}>🇮🇳</span>
            <span><span style={{ color:'var(--saffron)' }}>C</span>AIS</span>
          </div>
        ) : <div />}
      </div>

      {title && (
        <span style={{ position:'absolute', left:'50%', transform:'translateX(-50%)', fontSize:'0.9rem', fontWeight:700, color:'var(--text)', whiteSpace:'nowrap' }}>
          {title}
        </span>
      )}

      <div style={{ display:'flex', alignItems:'center', gap:8, justifyContent:'flex-end', flex:1 }}>
        {onLanguageClick && (
          <button className="btn-icon" onClick={onLanguageClick}
            style={{ display:'flex', alignItems:'center', gap:5, padding:'7px 11px', fontSize:'0.8rem', fontWeight:600 }}>
            <Globe size={14} />
            <span>{lang?.name || 'Language'}</span>
          </button>
        )}
        <button onClick={toggle} className="btn-icon" title={isDark?'Light mode':'Dark mode'}>
          {isDark ? <Sun size={16} color="var(--saffron)" /> : <Moon size={16} />}
        </button>
      </div>
    </nav>
  );
}
