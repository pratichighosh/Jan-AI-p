import { useTheme } from '../context/ThemeContext';

const indiaMapImg = '/indiamap.jpeg';

// Each character: file in /public/, position as % of map container (left, top), size in px
const CHARACTERS = [
  { src: '/punjab.jpeg',      left: '24%', top: '18%', size: 62, label: 'Punjab'      },
  { src: '/rajasthan.jpeg',   left: '14%', top: '34%', size: 62, label: 'Rajasthan'   },
  { src: '/gujarat.jpeg',     left: '10%', top: '50%', size: 62, label: 'Gujarat'     },
  { src: '/maharashtra.jpeg', left: '20%', top: '62%', size: 62, label: 'Maharashtra' },
  { src: '/karnataka.jpeg',   left: '26%', top: '72%', size: 62, label: 'Karnataka'   },
  { src: '/tamilnadu.jpeg',   left: '34%', top: '81%', size: 62, label: 'Tamil Nadu'  },
  { src: '/up.jpeg',          left: '40%', top: '28%', size: 62, label: 'UP'          },
  { src: '/bengal.jpeg',      left: '66%', top: '42%', size: 62, label: 'West Bengal' },
  { src: '/assam.jpeg',       left: '74%', top: '24%', size: 62, label: 'Assam'       },
  { src: '/manipur.jpeg',     left: '80%', top: '36%', size: 62, label: 'Manipur'     },
  { src: '/telangana.jpeg',   left: '38%', top: '62%', size: 62, label: 'Telangana'   },
];

export default function IndiaMap({ style = {}, mini = false }) {
  const { isDark } = useTheme();

  const mapFilter = isDark
    ? 'brightness(0.6) sepia(0.5) saturate(2) hue-rotate(335deg) contrast(1.1)'
    : 'sepia(0.25) saturate(1.5) hue-rotate(350deg) brightness(0.97)';

  if (mini) {
    return (
      <div style={{ width: '100%', height: '100%', overflow: 'hidden', borderRadius: '50%' }}>
        <img src={indiaMapImg} alt="India"
          style={{ width: '100%', height: '100%', objectFit: 'cover', filter: mapFilter }} />
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', ...style }}>

      {/* Base map */}
      <img
        src={indiaMapImg}
        alt="Map of India"
        style={{
          width: '100%', height: '100%',
          objectFit: 'contain',
          filter: mapFilter,
          display: 'block',
          transition: 'filter 0.3s',
        }}
      />

      {/* Floating cultural characters */}
      {CHARACTERS.map(({ src, left, top, size, label }) => (
        <div
          key={label}
          title={label}
          style={{
            position: 'absolute',
            left, top,
            width: size,
            height: size,
            transform: 'translate(-50%, -50%)',
            borderRadius: '50%',
            overflow: 'hidden',
            border: `2px solid ${isDark ? 'rgba(255,140,60,0.6)' : 'rgba(220,80,0,0.35)'}`,
            boxShadow: isDark
              ? '0 2px 12px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,140,60,0.15)'
              : '0 3px 14px rgba(0,0,0,0.18), 0 0 0 1px rgba(220,80,0,0.1)',
            background: '#fff',
            cursor: 'default',
            transition: 'transform 0.25s ease, box-shadow 0.25s ease',
            animation: `float-${Math.floor(Math.random() * 3) + 1} ${3 + Math.random() * 2}s ease-in-out infinite`,
            zIndex: 2,
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translate(-50%, -50%) scale(1.25)';
            e.currentTarget.style.zIndex = '10';
            e.currentTarget.style.boxShadow = isDark
              ? '0 6px 24px rgba(0,0,0,0.6), 0 0 0 2px rgba(255,140,60,0.5)'
              : '0 6px 24px rgba(0,0,0,0.25), 0 0 0 2px rgba(220,80,0,0.4)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'translate(-50%, -50%) scale(1)';
            e.currentTarget.style.zIndex = '2';
            e.currentTarget.style.boxShadow = isDark
              ? '0 2px 12px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,140,60,0.15)'
              : '0 3px 14px rgba(0,0,0,0.18), 0 0 0 1px rgba(220,80,0,0.1)';
          }}
        >
          <img
            src={src}
            alt={label}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: 'center top',
              
            }}
          />
        </div>
      ))}

      {/* Floating animation keyframes injected once */}
      <style>{`
        @keyframes float-1 { 0%,100%{transform:translate(-50%,-50%) translateY(0)} 50%{transform:translate(-50%,-50%) translateY(-5px)} }
        @keyframes float-2 { 0%,100%{transform:translate(-50%,-50%) translateY(0)} 50%{transform:translate(-50%,-50%) translateY(-7px)} }
        @keyframes float-3 { 0%,100%{transform:translate(-50%,-50%) translateY(0)} 50%{transform:translate(-50%,-50%) translateY(-4px)} }
      `}</style>
    </div>
  );
}