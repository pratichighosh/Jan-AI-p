import { useTheme } from '../context/ThemeContext';

const indiaMapImg = '/indiamap.jpeg';

export default function IndiaMap({ style = {}, mini = false }) {
  const { isDark } = useTheme();

  const filterStyle = isDark
    ? 'brightness(0.7) sepia(0.6) saturate(2.5) hue-rotate(335deg) contrast(1.15)'
    : 'sepia(0.4) saturate(2) hue-rotate(350deg) brightness(0.95)';

  if (mini) {
    return (
      <div style={{ width: '100%', height: '100%', overflow: 'hidden', borderRadius: '50%' }}>
        <img src={indiaMapImg} alt="India"
          style={{ width: '100%', height: '100%', objectFit: 'cover', filter: filterStyle }} />
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', ...style }}>
      <img src={indiaMapImg} alt="Map of India"
        style={{ width: '100%', height: '100%', objectFit: 'contain', filter: filterStyle, display: 'block' }} />
    </div>
  );
}