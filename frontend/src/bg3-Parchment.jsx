/**
 * BG 3 — Parchment Storybook
 * Soft aged-paper texture with faint, slowly-breathing SVG storybook
 * illustrations (stars, moon, castle, scroll, quill, compass rose, book).
 *
 * USAGE in App.jsx:
 *   import ParchmentBg from './bg3-Parchment';
 *   <div style={{ position:'relative' }}>
 *     <ParchmentBg />
 *     ...your chat messages...
 *   </div>
 */

import { useEffect, useRef } from 'react';

/* ── inline SVG illustrations ── */
const ILLUSTRATIONS = [
  /* Open book */
  `<svg viewBox="0 0 80 56" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M40 10 Q20 8 4 16 L4 50 Q20 42 40 44 Q60 42 76 50 L76 16 Q60 8 40 10Z" stroke="currentColor" stroke-width="2.2" fill="none" stroke-linecap="round"/>
    <line x1="40" y1="10" x2="40" y2="44" stroke="currentColor" stroke-width="1.6" stroke-dasharray="3 2"/>
    <line x1="15" y1="26" x2="37" y2="26" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="13" y1="32" x2="37" y2="32" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="15" y1="38" x2="37" y2="38" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="43" y1="26" x2="65" y2="26" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="43" y1="32" x2="67" y2="32" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="43" y1="38" x2="65" y2="38" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
  </svg>`,

  /* Star */
  `<svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
    <polygon points="30,4 36,22 56,22 40,34 46,52 30,40 14,52 20,34 4,22 24,22" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>
  </svg>`,

  /* Crescent moon */
  `<svg viewBox="0 0 50 60" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M32 6 A22 22 0 1 0 32 54 A14 14 0 1 1 32 6Z" stroke="currentColor" stroke-width="2.2" fill="none" stroke-linecap="round"/>
  </svg>`,

  /* Compass rose */
  `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="32" cy="32" r="26" stroke="currentColor" stroke-width="1.4"/>
    <circle cx="32" cy="32" r="4"  stroke="currentColor" stroke-width="1.4"/>
    <polygon points="32,6 28,32 32,28 36,32" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" fill="none"/>
    <polygon points="32,58 28,32 32,36 36,32" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" fill="none"/>
    <polygon points="6,32 32,28 28,32 32,36" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" fill="none"/>
    <polygon points="58,32 32,28 36,32 32,36" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" fill="none"/>
    <text x="32" y="18" text-anchor="middle" font-size="7" fill="currentColor" font-family="Georgia,serif">N</text>
  </svg>`,

  /* Quill pen */
  `<svg viewBox="0 0 52 72" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M42 4 C52 10 50 28 36 38 L20 58 L18 68 L14 56 C6 48 14 32 28 22 C36 16 40 8 42 4Z" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M28 22 L20 58" stroke="currentColor" stroke-width="1.2" stroke-dasharray="3 3"/>
    <path d="M18 68 Q19 62 24 58" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" fill="none"/>
  </svg>`,

  /* Scroll */
  `<svg viewBox="0 0 70 56" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="8" y="10" width="54" height="36" rx="6" stroke="currentColor" stroke-width="2" fill="none"/>
    <path d="M8 14 Q2 14 2 22 Q2 32 8 32" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
    <path d="M62 14 Q68 14 68 22 Q68 32 62 32" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
    <line x1="18" y1="22" x2="52" y2="22" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
    <line x1="18" y1="29" x2="52" y2="29" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
    <line x1="18" y1="36" x2="40" y2="36" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
  </svg>`,

  /* Hourglass */
  `<svg viewBox="0 0 48 72" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="6" y="4" width="36" height="8" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
    <rect x="6" y="60" width="36" height="8" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
    <path d="M10 12 L24 36 L38 12" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M10 60 L24 36 L38 60" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <line x1="24" y1="44" x2="24" y2="52" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
  </svg>`,

  /* Castle tower */
  `<svg viewBox="0 0 64 72" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="14" y="20" width="36" height="48" stroke="currentColor" stroke-width="2" fill="none"/>
    <rect x="10" y="10" width="8"  height="14" stroke="currentColor" stroke-width="1.8" fill="none"/>
    <rect x="28" y="10" width="8"  height="14" stroke="currentColor" stroke-width="1.8" fill="none"/>
    <rect x="46" y="10" width="8"  height="14" stroke="currentColor" stroke-width="1.8" fill="none"/>
    <rect x="24" y="44" width="16" height="24" stroke="currentColor" stroke-width="1.6" fill="none"/>
    <line x1="10" y1="24" x2="54" y2="24" stroke="currentColor" stroke-width="1.6"/>
  </svg>`,
];

/* scatter positions (% of container) — keep away from center reading zone */
const POSITIONS = [
  { x: 4,  y: 6,  size: 68, rot: -12 },
  { x: 82, y: 3,  size: 60, rot:  10 },
  { x: 1,  y: 52, size: 54, rot:  -8 },
  { x: 85, y: 55, size: 58, rot:   7 },
  { x: 42, y: 2,  size: 48, rot:   4 },
  { x: 6,  y: 86, size: 52, rot: -14 },
  { x: 80, y: 82, size: 56, rot:   9 },
  { x: 50, y: 88, size: 46, rot:  -5 },
];

/* keyframes injected once */
const STYLE = `
  @keyframes pb-breathe {
    0%,100% { opacity: var(--base-op); transform: scale(1)    rotate(var(--rot)); }
    50%      { opacity: calc(var(--base-op) * 1.6); transform: scale(1.06) rotate(var(--rot)); }
  }
  @keyframes pb-sway {
    0%,100% { transform: rotate(var(--rot)); }
    50%     { transform: rotate(calc(var(--rot) + 4deg)); }
  }
`;

export default function ParchmentBg() {
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!document.getElementById('pb-styles')) {
      const tag = document.createElement('style');
      tag.id = 'pb-styles';
      tag.textContent = STYLE;
      document.head.appendChild(tag);
    }
  }, []);

  return (
    <div
      ref={wrapRef}
      style={{
        position: 'absolute', inset: 0,
        pointerEvents: 'none', zIndex: 0,
        overflow: 'hidden',
        /* Parchment base */
        background: `
          radial-gradient(ellipse at 20% 20%, rgba(240,223,168,0.22) 0%, transparent 55%),
          radial-gradient(ellipse at 80% 75%, rgba(201,168,76,0.14) 0%, transparent 50%),
          radial-gradient(ellipse at 50% 50%, rgba(250,244,228,0.10) 0%, transparent 70%)
        `,
      }}
    >
      {/* Paper grain via SVG filter */}
      <svg width="0" height="0" style={{ position:'absolute' }}>
        <defs>
          <filter id="pb-grain">
            <feTurbulence type="fractalNoise" baseFrequency="0.72" numOctaves="4" stitchTiles="stitch"/>
            <feColorMatrix type="saturate" values="0"/>
            <feBlend in="SourceGraphic" mode="multiply"/>
          </filter>
        </defs>
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        filter: 'url(#pb-grain)',
        opacity: 0.07,
        background: '#C9A84C',
      }}/>

      {/* Faint grid lines — like old graph paper */}
      <svg style={{ position:'absolute', inset:0, width:'100%', height:'100%', opacity:0.06 }}>
        <defs>
          <pattern id="pb-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#C9A84C" strokeWidth="0.6"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#pb-grid)"/>
      </svg>

      {/* Scattered illustrations */}
      {POSITIONS.map((pos, i) => {
        const delay = i * 1.1;
        const dur   = 5 + (i % 3) * 1.8;
        const op    = 0.07 + (i % 4) * 0.018;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${pos.x}%`,
              top:  `${pos.y}%`,
              width:  pos.size,
              height: pos.size,
              color: '#8B6914',
              '--rot':     `${pos.rot}deg`,
              '--base-op': op,
              opacity: op,
              animation: `pb-breathe ${dur}s ease-in-out ${delay}s infinite`,
              transformOrigin: 'center',
            }}
            dangerouslySetInnerHTML={{ __html: ILLUSTRATIONS[i % ILLUSTRATIONS.length] }}
          />
        );
      })}

      {/* Corner flourishes */}
      {[
        { top:0,    left:0,    transform:'rotate(0deg)' },
        { top:0,    right:0,   transform:'rotate(90deg)' },
        { bottom:0, right:0,   transform:'rotate(180deg)' },
        { bottom:0, left:0,    transform:'rotate(270deg)' },
      ].map((style, i) => (
        <svg key={i} width="60" height="60" viewBox="0 0 60 60" fill="none"
          style={{ position:'absolute', opacity:0.09, ...style }}>
          <path d="M4 4 Q4 30 30 30" stroke="#8B6914" strokeWidth="1.5" fill="none"/>
          <path d="M4 4 L4 18 M4 4 L18 4" stroke="#8B6914" strokeWidth="1.5" strokeLinecap="round"/>
          <circle cx="30" cy="30" r="3" stroke="#8B6914" strokeWidth="1.2" fill="none"/>
        </svg>
      ))}
    </div>
  );
}
