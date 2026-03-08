import { useState } from 'react';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { ThemeProvider } from './context/ThemeContext';
import SplashScreen from './pages/SplashScreen';
import LanguageSelect from './pages/LanguageSelect';
import Home from './pages/Home';
import UploadPage from './pages/UploadPage';
import Results from './pages/Results';
import './index.css';

// ── Each entry: { screen, props }
// goBack() pops one level from stack, never jumps multiple

function Router() {
  const { langCode } = useLanguage();

  // Page stack – current page is last item
  const [stack, setStack] = useState([{ screen: 'splash' }]);
  const current = stack[stack.length - 1];

  const push = (entry) => setStack(prev => [...prev, entry]);
  const pop = () => setStack(prev => prev.length > 1 ? prev.slice(0, -1) : prev);
  const replace = (entry) => setStack(prev => [...prev.slice(0, -1), entry]);
  const reset = (entry) => setStack([entry]);

  // Handlers
  const onSplashDone = () => {
    const saved = localStorage.getItem('cais_language');
    reset({ screen: saved ? 'home' : 'language' });
  };

  const onLanguageDone = () => replace({ screen: 'home' });

  const onUpload = (flowType) => push({ screen: 'upload', flowType });

  const onResult = (data) => push({ screen: 'results', data });

  const onChangeLanguage = () => push({ screen: 'language' });

  const onHome = () => reset({ screen: 'home' });

  return (
    <>
      {current.screen === 'splash' && (
        <SplashScreen onComplete={onSplashDone} />
      )}

      {current.screen === 'language' && (
        <LanguageSelect onComplete={onLanguageDone} />
      )}

      {current.screen === 'home' && (
        <Home onUpload={onUpload} onLanguageClick={onChangeLanguage} />
      )}

      {current.screen === 'upload' && (
        <UploadPage
          flowType={current.flowType || 'form'}
          onBack={pop}             // ← one page back
          onResult={onResult}
        />
      )}

      {current.screen === 'results' && (
        <Results
          data={current.data}
          onBack={pop}             // ← one page back (to upload)
          onHome={onHome}
        />
      )}
    </>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <Router />
      </LanguageProvider>
    </ThemeProvider>
  );
}
