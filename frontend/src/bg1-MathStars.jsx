/**
 * BG 1 — MathStars
 * Floating math symbols drifting slowly like stars across the chat area.
 *
 * USAGE in App.jsx (inside the chat <main> or chat scroll container):
 *   import MathStarsBg from './bg1-MathStars';
 *   // Place as first child inside the chat area div:
 *   <div style={{ position:'relative' }}>
 *     <MathStarsBg />
 *     ...your chat messages...
 *   </div>
 */

import { useEffect, useRef } from 'react';

const SYMBOLS = ['∑', 'π', '∞', '÷', '√', '∫', 'θ', 'Δ', '±', '≈', '×', 'α', 'β', 'λ', 'φ', '∂', '∇', '∈', '≤', '≥', '%', '!', '²', '³'];

function randomBetween(a, b) { return a + Math.random() * (b - a); }

export default function MathStarsBg() {
  const canvasRef = useRef(null);
  const animRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let W, H, particles;

    const COLORS = [
      'rgba(91,63,200,',   // violet
      'rgba(201,168,76,',  // gold
      'rgba(74,159,212,',  // sky
      'rgba(224,107,139,', // rose
      'rgba(75,175,138,',  // sage
    ];

    function init() {
      W = canvas.width = canvas.offsetWidth;
      H = canvas.height = canvas.offsetHeight;

      particles = Array.from({ length: 55 }, () => ({
        sym: SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)],
        x: randomBetween(0, W),
        y: randomBetween(0, H),
        size: randomBetween(11, 30),
        speed: randomBetween(0.12, 0.45),
        drift: randomBetween(-0.18, 0.18),
        alpha: randomBetween(0.06, 0.22),
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        rot: randomBetween(-0.4, 0.4),
        rotV: randomBetween(-0.002, 0.002),
        pulse: randomBetween(0, Math.PI * 2),
        pulseS: randomBetween(0.003, 0.008),
      }));
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);

      particles.forEach(p => {
        p.y -= p.speed;
        p.x += p.drift;
        p.rot += p.rotV;
        p.pulse += p.pulseS;

        const alpha = p.alpha + Math.sin(p.pulse) * 0.05;

        // Wrap
        if (p.y < -40) p.y = H + 20;
        if (p.x < -30) p.x = W + 20;
        if (p.x > W + 30) p.x = -20;

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.globalAlpha = Math.max(0, alpha);
        ctx.font = `${p.size}px 'Georgia', serif`;
        ctx.fillStyle = p.color + alpha + ')';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // Soft glow
        ctx.shadowColor = p.color + '0.6)';
        ctx.shadowBlur = 12;
        ctx.fillText(p.sym, 0, 0);
        ctx.restore();
      });

      animRef.current = requestAnimationFrame(draw);
    }

    init();
    draw();

    const ro = new ResizeObserver(init);
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(animRef.current);
      ro.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
        borderRadius: 'inherit',
      }}
    />
  );
}