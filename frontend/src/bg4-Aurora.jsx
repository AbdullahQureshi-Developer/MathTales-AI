/**
 * BG 4 — Aurora Waves
 * Slow, silky aurora-borealis gradient waves that drift and breathe.
 * Stays subtle enough to read chat text over it.
 *
 * USAGE in App.jsx:
 *   import AuroraBg from './bg4-Aurora';
 *   <div style={{ position:'relative' }}>
 *     <AuroraBg />
 *     ...your chat messages...
 *   </div>
 */

import { useEffect, useRef } from 'react';

export default function AuroraBg() {
  const canvasRef = useRef(null);
  const animRef   = useRef(null);
  const tRef      = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx    = canvas.getContext('2d');
    let W, H;

    function init() {
      W = canvas.width  = canvas.offsetWidth;
      H = canvas.height = canvas.offsetHeight;
    }

    /* ── aurora color stops (r,g,b) ── */
    const AURORA_BANDS = [
      { r: 201, g: 168, b: 76  },  // warm gold
      { r: 224, g: 149, b: 181 },  // blush rose
      { r: 91,  g: 63,  b: 200 },  // deep violet
      { r: 74,  g: 159, b: 212 },  // sky blue
      { r: 75,  g: 175, b: 138 },  // sage green
      { r: 230, g: 130, b: 100 },  // peach
    ];

    function lerp(a, b, t) { return a + (b - a) * t; }

    function draw() {
      tRef.current += 0.0018;
      const t = tRef.current;
      ctx.clearRect(0, 0, W, H);

      /* Draw 4 overlapping aurora layers */
      for (let layer = 0; layer < 4; layer++) {
        const phaseOffset = (layer / 4) * Math.PI * 2;
        const speed       = 0.6 + layer * 0.3;
        const yBase       = H * (0.15 + layer * 0.22);
        const height      = H * (0.28 + layer * 0.06);
        const opacity     = 0.08 + layer * 0.015;

        /* Color blending between two bands */
        const ci1 = (layer + Math.floor(t * 0.4)) % AURORA_BANDS.length;
        const ci2 = (ci1 + 1) % AURORA_BANDS.length;
        const blend = (Math.sin(t * 0.5 + phaseOffset) + 1) / 2;
        const c = {
          r: Math.round(lerp(AURORA_BANDS[ci1].r, AURORA_BANDS[ci2].r, blend)),
          g: Math.round(lerp(AURORA_BANDS[ci1].g, AURORA_BANDS[ci2].g, blend)),
          b: Math.round(lerp(AURORA_BANDS[ci1].b, AURORA_BANDS[ci2].b, blend)),
        };

        /* Build a wavy path across the canvas */
        ctx.beginPath();
        ctx.moveTo(0, yBase);

        const steps = 80;
        for (let i = 0; i <= steps; i++) {
          const x  = (i / steps) * W;
          const wx = (i / steps) * Math.PI * 2 * 2.5;
          const wy =
            Math.sin(wx * 1.0 + t * speed + phaseOffset) * height * 0.35 +
            Math.sin(wx * 1.7 + t * speed * 0.8 + phaseOffset * 1.3) * height * 0.2 +
            Math.sin(wx * 0.5 + t * speed * 0.5 + phaseOffset * 0.7) * height * 0.15;

          const y = yBase + wy;
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }

        /* Close path to bottom of canvas */
        ctx.lineTo(W, H);
        ctx.lineTo(0, H);
        ctx.closePath();

        /* Gradient fill for each wave */
        const grad = ctx.createLinearGradient(0, yBase - height, 0, yBase + height * 1.5);
        grad.addColorStop(0,   `rgba(${c.r},${c.g},${c.b},0)`);
        grad.addColorStop(0.3, `rgba(${c.r},${c.g},${c.b},${opacity})`);
        grad.addColorStop(0.6, `rgba(${c.r},${c.g},${c.b},${opacity * 0.5})`);
        grad.addColorStop(1,   `rgba(${c.r},${c.g},${c.b},0)`);

        ctx.fillStyle = grad;
        ctx.fill();
      }

      /* ── shimmer sparkles scattered over the waves ── */
      const sparkleCount = 18;
      for (let i = 0; i < sparkleCount; i++) {
        const sx = W * ((i / sparkleCount + t * 0.04 * (i % 3 === 0 ? 1 : -0.5)) % 1);
        const sy = H * (0.1 + 0.8 * ((Math.sin(t * 0.7 + i * 1.3) + 1) / 2));
        const alpha = (Math.sin(t * 2.5 + i * 0.8) + 1) / 2 * 0.25;
        const radius = 1 + Math.sin(t * 3 + i) * 0.7;

        const sg = ctx.createRadialGradient(sx, sy, 0, sx, sy, radius * 6);
        sg.addColorStop(0, `rgba(255,240,180,${alpha})`);
        sg.addColorStop(1, `rgba(255,240,180,0)`);
        ctx.beginPath();
        ctx.arc(sx, sy, radius * 6, 0, Math.PI * 2);
        ctx.fillStyle = sg;
        ctx.fill();
      }

      /* ── top edge glow ── */
      const topGrad = ctx.createLinearGradient(0, 0, W, 0);
      const topHue = Math.round(((Math.sin(t * 0.3) + 1) / 2) * 60 + 240); // cycles violet→blue
      topGrad.addColorStop(0,   `hsla(${topHue},70%,70%,0.07)`);
      topGrad.addColorStop(0.5, `hsla(${topHue + 40},70%,75%,0.12)`);
      topGrad.addColorStop(1,   `hsla(${topHue + 80},70%,70%,0.07)`);
      ctx.fillStyle = topGrad;
      ctx.fillRect(0, 0, W, H * 0.08);

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
    <>
      {/* Static mesh base so there's always something under the waves */}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none',
        background: `
          radial-gradient(ellipse at 15% 25%, rgba(201,168,76,0.10) 0%, transparent 50%),
          radial-gradient(ellipse at 80% 15%, rgba(91,63,200,0.08) 0%, transparent 45%),
          radial-gradient(ellipse at 60% 80%, rgba(74,159,212,0.09) 0%, transparent 50%),
          radial-gradient(ellipse at 20% 75%, rgba(75,175,138,0.07) 0%, transparent 45%)
        `,
      }}/>
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute', inset: 0,
          width: '100%', height: '100%',
          pointerEvents: 'none', zIndex: 1,
        }}
      />
    </>
  );
}
