/**
 * BG 2 — Constellation
 * Glowing dots that drift and connect with luminous lines when nearby.
 *
 * USAGE in App.jsx:
 *   import ConstellationBg from './bg2-Constellation';
 *   <div style={{ position:'relative' }}>
 *     <ConstellationBg />
 *     ...your chat messages...
 *   </div>
 */

import { useEffect, useRef } from 'react';

function rand(a, b) { return a + Math.random() * (b - a); }

const NODE_COUNT  = 60;
const CONNECT_DIST = 110;

export default function ConstellationBg() {
  const canvasRef = useRef(null);
  const animRef   = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx    = canvas.getContext('2d');
    let W, H, nodes;

    // Palette — warm gold + soft violet
    const DOT_COLORS = [
      [201, 168, 76],   // gold
      [91,  63, 200],   // violet
      [74, 159, 212],   // sky
      [224, 107, 139],  // rose
    ];

    function init() {
      W = canvas.width  = canvas.offsetWidth;
      H = canvas.height = canvas.offsetHeight;

      nodes = Array.from({ length: NODE_COUNT }, () => {
        const col = DOT_COLORS[Math.floor(Math.random() * DOT_COLORS.length)];
        return {
          x:  rand(0, W), y:  rand(0, H),
          vx: rand(-0.25, 0.25), vy: rand(-0.25, 0.25),
          r:  rand(1.5, 3.5),
          col,
          pulse:  rand(0, Math.PI * 2),
          pulseS: rand(0.01, 0.025),
        };
      });
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);

      // Update positions
      nodes.forEach(n => {
        n.x += n.vx;
        n.y += n.vy;
        n.pulse += n.pulseS;

        if (n.x < 0 || n.x > W) n.vx *= -1;
        if (n.y < 0 || n.y > H) n.vy *= -1;
      });

      // Draw edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = a.x - b.x, dy = a.y - b.y;
          const dist = Math.sqrt(dx*dx + dy*dy);
          if (dist > CONNECT_DIST) continue;

          const alpha = (1 - dist / CONNECT_DIST) * 0.18;
          const r = Math.round((a.col[0] + b.col[0]) / 2);
          const g = Math.round((a.col[1] + b.col[1]) / 2);
          const bv = Math.round((a.col[2] + b.col[2]) / 2);

          const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
          grad.addColorStop(0, `rgba(${a.col.join(',')},${alpha})`);
          grad.addColorStop(1, `rgba(${b.col.join(',')},${alpha})`);

          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = grad;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }

      // Draw nodes
      nodes.forEach(n => {
        const pulse = 0.55 + 0.45 * Math.sin(n.pulse);
        const alpha = 0.35 + 0.35 * pulse;
        const [r, g, b] = n.col;

        // Outer glow
        const glow = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 5);
        glow.addColorStop(0,   `rgba(${r},${g},${b},${alpha * 0.5})`);
        glow.addColorStop(1,   `rgba(${r},${g},${b},0)`);
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r * 5, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        // Core dot
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r * pulse, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${r},${g},${b},${alpha})`;
        ctx.shadowColor = `rgba(${r},${g},${b},0.9)`;
        ctx.shadowBlur  = 10;
        ctx.fill();
        ctx.shadowBlur  = 0;
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
      }}
    />
  );
}
