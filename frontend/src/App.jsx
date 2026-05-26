import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, BookOpen, Loader2, Info, Repeat, Award } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import axios from 'axios';
import MathStarsBg from './bg1-MathStars';
import ConstellationBg from './bg2-Constellation';
import ParchmentBg from './bg3-Parchment';
import AuroraBg from './bg4-Aurora';
/* ─── Google Fonts injected once ─── */
const FontStyle = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .font-display { font-family: 'Playfair Display', serif; }

    :root {
      --cream:   #FAF7F2;
      --ivory:   #F3EDE3;
      --gold:    #C9A84C;
      --gold-lt: #F0DFA8;
      --ink:     #1C1917;
      --ink-mid: #3C3732;
      --violet:  #5B3FC8;
      --violet2: #7C5CDE;
      --rose:    #E06B8B;
      --sky:     #4A9FD4;
      --sage:    #4BAF8A;
    }

    body { background: var(--cream); }

    /* scrollbar */
    .custom-scrollbar::-webkit-scrollbar { width: 6px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: linear-gradient(180deg, #C9A84C55, #5B3FC855);
      border-radius: 99px;
    }

    /* prose overrides */
    .chat-prose p  { margin: 0.35em 0; line-height: 1.75; }
    .chat-prose ul { padding-left: 1.25rem; }
    .chat-prose li { margin: 0.2em 0; }
    .chat-prose strong { color: var(--ink); }
    .chat-prose pre {
      background: #1C191714;
      border: 1px solid #C9A84C40;
      border-radius: 12px;
      padding: 1rem;
      font-size: 0.82rem;
    }
    .chat-prose code {
      background: #5B3FC815;
      color: var(--violet);
      padding: 0.15em 0.4em;
      border-radius: 4px;
      font-size: 0.88em;
    }

    /* Grain texture overlay */
    .grain::after {
      content: '';
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.035'/%3E%3C/svg%3E");
      background-size: 180px;
      z-index: 999;
      opacity: 0.6;
    }

    /* Decorative dot grid */
    .dot-grid {
      background-image: radial-gradient(circle, #5B3FC818 1px, transparent 1px);
      background-size: 28px 28px;
    }

    /* Animated badge */
    @keyframes shimmer {
      0%   { background-position: -200% center; }
      100% { background-position:  200% center; }
    }
    .shimmer-text {
      background: linear-gradient(90deg, var(--gold), var(--violet2), var(--rose), var(--gold));
      background-size: 200% auto;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: shimmer 4s linear infinite;
    }

    @keyframes float {
      0%, 100% { transform: translateY(0px) rotate(0deg); }
      50%       { transform: translateY(-8px) rotate(3deg); }
    }
    .float-icon { animation: float 5s ease-in-out infinite; }

    /* Input glow */
    .input-glow:focus-within {
      box-shadow: 0 0 0 3px #5B3FC820, 0 20px 60px #5B3FC818;
    }

    /* Sidebar card hover */
    .stat-card {
      transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    .stat-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 32px #5B3FC818;
    }
  `}</style>
);

/* ─── Decorative blobs ─── */
const Blobs = () => (
  <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
    <div style={{
      position: 'absolute', top: '-12%', left: '-8%',
      width: '55%', height: '55%', borderRadius: '60% 40% 55% 45%',
      background: 'radial-gradient(ellipse, #F0DFA855 0%, #E8D5F000 70%)',
      filter: 'blur(60px)'
    }} />
    <div style={{
      position: 'absolute', bottom: '-15%', right: '-10%',
      width: '60%', height: '60%', borderRadius: '45% 55% 40% 60%',
      background: 'radial-gradient(ellipse, #C8D9F840 0%, #C8D9F800 70%)',
      filter: 'blur(70px)'
    }} />
    <div style={{
      position: 'absolute', top: '35%', left: '25%',
      width: '50%', height: '45%', borderRadius: '50%',
      background: 'radial-gradient(ellipse, #E8C4D030 0%, #E8C4D000 70%)',
      filter: 'blur(80px)'
    }} />
    {/* Subtle dot grid */}
    <div className="dot-grid absolute inset-0 opacity-60" />
  </div>
);

/* ─── Progress ring ─── */
const ProgressRing = ({ pct }) => {
  const r = 20, cx = 26, cy = 26;
  const circ = 2 * Math.PI * r;
  return (
    <svg width="52" height="52" style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#5B3FC815" strokeWidth="4" />
      <circle
        cx={cx} cy={cy} r={r} fill="none"
        stroke="url(#pg)" strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={circ * (1 - pct / 100)}
        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
      />
      <defs>
        <linearGradient id="pg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#C9A84C" />
          <stop offset="100%" stopColor="#5B3FC8" />
        </linearGradient>
      </defs>
    </svg>
  );
};

export default function App() {
  const [messages, setMessages] = useState([{
    role: 'assistant',
    content: "🌟 Welcome, young mathematician! I'm the Great Sage of MathTales. Together, we'll embark on a magical learning adventure that unfolds across many story turns. What math concept would you like to explore through storytelling today?"
  }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [turnNumber, setTurnNumber] = useState(0);
  const [storyElements, setStoryElements] = useState({ characters: '', setting: '' });
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/api/chat', {
        message: userMessage, history: messages
      });
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.data.response,
        context: response.data.context_used
      }]);
      setTurnNumber(response.data.turn_number != null ? response.data.turn_number : turnNumber + 1);
      if (response.data.story_elements != null) setStoryElements(response.data.story_elements);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "✨ My magical powers flickered! Let's try that again, young scholar.",
        isError: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const resetConversation = () => {
    setMessages([{ role: 'assistant', content: "🌟 Welcome back! Ready for a new mathematical adventure? What would you like to learn today?" }]);
    setTurnNumber(0);
    setStoryElements({ characters: '', setting: '' });
  };

  const pct = Math.min((turnNumber / 20) * 100, 100);
  const phaseLabel = turnNumber < 5 ? "Beginning of adventure"
    : turnNumber < 12 ? "Building understanding"
      : turnNumber < 20 ? "Deepening knowledge"
        : "Mastery achieved! 🎉";

  return (
    <>
      <FontStyle />
      <div className="grain flex h-screen overflow-hidden" style={{ background: 'var(--cream)', color: 'var(--ink-mid)' }}>
        <Blobs />

        {/* ══════════════ SIDEBAR ══════════════ */}
        <aside className="hidden md:flex flex-col z-10" style={{
          width: 300,
          borderRight: '1.5px solid #C9A84C28',
          background: 'linear-gradient(160deg, rgba(255,252,245,0.92) 0%, rgba(243,237,227,0.88) 100%)',
          backdropFilter: 'blur(24px)',
          boxShadow: '4px 0 40px #C9A84C0C',
          padding: '28px 20px'
        }}>

          {/* Logo */}
          <div className="flex items-center gap-3 mb-10">
            <div className="float-icon" style={{
              width: 44, height: 44, borderRadius: 14,
              background: 'linear-gradient(135deg, #1C1917 0%, #3C3732 50%, #5B3FC8 100%)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 8px 24px #1C191730'
            }}>
              <Sparkles size={20} color="#F0DFA8" />
            </div>
            <div>
              <h1 className="font-display shimmer-text" style={{ fontSize: 20, lineHeight: 1.2 }}>MathTales AI</h1>
              <p style={{ fontSize: 10, color: '#C9A84C', fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase' }}>Sage Edition</p>
            </div>
          </div>

          {/* Story Progress card */}
          <div className="stat-card mb-5" style={{
            padding: '18px 16px',
            borderRadius: 18,
            background: 'linear-gradient(135deg, #1C191708 0%, #5B3FC808 100%)',
            border: '1.5px solid #C9A84C30',
            boxShadow: '0 4px 20px #C9A84C0A'
          }}>
            <div className="flex items-center gap-2 mb-4">
              <Repeat size={14} style={{ color: 'var(--gold)' }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                Story Progress
              </span>
            </div>

            <div className="flex items-center gap-3">
              <ProgressRing pct={pct} />
              <div>
                <p style={{ fontSize: 28, fontWeight: 700, color: 'var(--violet)', lineHeight: 1 }}>{turnNumber}</p>
                <p style={{ fontSize: 11, color: '#78716C', fontWeight: 500 }}>of 20 turns</p>
              </div>
            </div>

            {/* Phase pill */}
            <div style={{
              marginTop: 14,
              padding: '6px 12px',
              borderRadius: 99,
              background: pct >= 100
                ? 'linear-gradient(90deg, #C9A84C20, #5B3FC820)'
                : '#5B3FC810',
              border: '1px solid #5B3FC825',
              display: 'inline-block'
            }}>
              <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--violet)' }}>{phaseLabel}</p>
            </div>
          </div>

          {/* Story World */}
          {(storyElements.characters || storyElements.setting) && (
            <div className="stat-card mb-5" style={{
              padding: '18px 16px',
              borderRadius: 18,
              background: 'linear-gradient(135deg, #4A9FD408 0%, #4BAF8A08 100%)',
              border: '1.5px solid #4A9FD430',
              boxShadow: '0 4px 20px #4A9FD40A'
            }}>
              <div className="flex items-center gap-2 mb-3">
                <BookOpen size={14} style={{ color: 'var(--sky)' }} />
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  Story World
                </span>
              </div>

              {storyElements.characters && (
                <div style={{ marginBottom: 10 }}>
                  <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--sky)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>Characters</p>
                  <p style={{ fontSize: 13, color: 'var(--ink-mid)', fontWeight: 500 }}>{storyElements.characters}</p>
                </div>
              )}
              {storyElements.setting && (
                <div>
                  <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--sage)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>Setting</p>
                  <p style={{ fontSize: 13, color: 'var(--ink-mid)', fontWeight: 500, textTransform: 'capitalize' }}>{storyElements.setting}</p>
                </div>
              )}
            </div>
          )}

          {/* New Story button */}
          <button
            onClick={resetConversation}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '12px 16px', borderRadius: 14,
              background: 'linear-gradient(135deg, #1C1917 0%, #3C3732 100%)',
              border: 'none', cursor: 'pointer', width: '100%',
              boxShadow: '0 6px 24px #1C191728',
              transition: 'all 0.25s ease'
            }}
            onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <BookOpen size={18} color="#F0DFA8" />
            <span style={{ fontSize: 14, fontWeight: 700, color: '#FAF7F2', letterSpacing: '0.02em' }}>New Story</span>
            <span style={{ marginLeft: 'auto', fontSize: 16 }}>✨</span>
          </button>

          {/* Footer badges */}
          <div style={{ marginTop: 'auto', paddingTop: 24, borderTop: '1px solid #C9A84C20' }}>
            {[
              { icon: <Info size={12} />, label: 'Enhanced Multi-Turn Mode', color: '#C9A84C' },
              { icon: <Award size={12} />, label: 'CPU LLM + RAG Pipeline', color: '#5B3FC8' }
            ].map((b, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 10px', borderRadius: 8,
                marginBottom: 6,
                background: '#1C191706',
                border: '1px solid #1C191710'
              }}>
                <span style={{ color: b.color }}>{b.icon}</span>
                <p style={{ fontSize: 11, fontWeight: 600, color: '#78716C' }}>{b.label}</p>
              </div>
            ))}
          </div>
        </aside>

        {/* ══════════════ MAIN ══════════════ */}
        <main className="flex-1 flex flex-col z-10 relative overflow-hidden">

          {/* Mobile header */}
          {/* <ParchmentBg/> */}
          <AuroraBg />
          {/* <ConstellationBg /> */}
          {/* <MathStarsBg /> */}
          <header className="md:hidden flex items-center justify-between" style={{
            padding: '14px 20px',
            borderBottom: '1px solid #C9A84C20',
            background: 'rgba(250,247,242,0.85)',
            backdropFilter: 'blur(16px)'
          }}>
            <div className="flex items-center gap-2">
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #1C1917, #5B3FC8)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <Sparkles size={16} color="#F0DFA8" />
              </div>
              <div>
                <p className="font-display shimmer-text" style={{ fontSize: 16 }}>MathTales AI</p>
                <p style={{ fontSize: 10, color: '#C9A84C', fontWeight: 600 }}>Turn {turnNumber}</p>
              </div>
            </div>
            <button onClick={resetConversation} style={{
              padding: '6px 12px', borderRadius: 8, border: '1px solid #C9A84C30',
              background: '#1C191708', fontSize: 12, fontWeight: 600, color: 'var(--ink-mid)', cursor: 'pointer'
            }}>New Story</button>
          </header>

          {/* Chat history */}
          <div className="flex-1 overflow-y-auto custom-scrollbar" style={{ padding: '32px 24px', position: "relative" }}>
            {/* <AuroraBg /> */}
            {/* <ConstellationBg/> */}
            {/* <MathStarsBg/> */}
            {/* <ParchmentBg/> */}
            <div style={{ maxWidth: 720, margin: '0 auto', position: 'relative', zIndex: 1 }}>
              <AnimatePresence initial={false}>
                {messages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 24 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
                    style={{
                      display: 'flex',
                      flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                      gap: 14,
                      marginBottom: 28,
                      alignItems: 'flex-start'
                    }}
                  >
                    {/* Avatar */}
                    <div style={{
                      flexShrink: 0,
                      width: 40, height: 40, borderRadius: 14,
                      background: msg.role === 'user'
                        ? 'linear-gradient(135deg, #4A9FD4 0%, #4BAF8A 100%)'
                        : 'linear-gradient(135deg, #1C1917 0%, #5B3FC8 100%)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      boxShadow: msg.role === 'user'
                        ? '0 6px 20px #4A9FD430'
                        : '0 6px 20px #5B3FC835',
                      border: msg.role === 'user' ? '2px solid #4A9FD430' : '2px solid #5B3FC830'
                    }}>
                      {msg.role === 'user'
                        ? <User size={18} color="white" />
                        : <Bot size={18} color="#F0DFA8" />}
                    </div>

                    {/* Bubble */}
                    <div style={{
                      maxWidth: '78%',
                      display: 'flex', flexDirection: 'column',
                      alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      gap: 6
                    }}>
                      {/* Role label */}
                      <p style={{
                        fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
                        textTransform: 'uppercase',
                        color: msg.role === 'user' ? 'var(--sky)' : 'var(--gold)',
                        paddingLeft: msg.role === 'user' ? 0 : 4,
                        paddingRight: msg.role === 'user' ? 4 : 0
                      }}>
                        {msg.role === 'user' ? 'You' : 'Great Sage'}
                      </p>

                      <div style={{
                        padding: '14px 20px',
                        borderRadius: msg.role === 'user' ? '20px 4px 20px 20px' : '4px 20px 20px 20px',
                        background: msg.isError
                          ? 'linear-gradient(135deg, #FFF0F3 0%, #FFE4EB 100%)'
                          : msg.role === 'user'
                            ? 'linear-gradient(135deg, #EEF6FD 0%, #E4F5EE 100%)'
                            : 'rgba(255,252,245,0.95)',
                        border: msg.isError
                          ? '1.5px solid #E06B8B30'
                          : msg.role === 'user'
                            ? '1.5px solid #4A9FD425'
                            : '1.5px solid #C9A84C22',
                        boxShadow: msg.role === 'user'
                          ? '0 4px 20px #4A9FD415'
                          : '0 6px 32px #1C191710, 0 1px 0 #C9A84C18',
                        backdropFilter: 'blur(8px)'
                      }}>
                        {msg.role === 'user' ? (
                          <p style={{ margin: 0, lineHeight: 1.7, fontWeight: 500, color: '#1C4966' }}>
                            {msg.content}
                          </p>
                        ) : (
                          <div className="chat-prose" style={{ color: 'var(--ink-mid)', fontSize: 14.5 }}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                          </div>
                        )}
                      </div>

                      {/* Context badge */}
                      {msg.context && msg.context.length > 0 && (
                        <div style={{
                          display: 'flex', alignItems: 'center', gap: 5,
                          fontSize: 10, fontWeight: 600,
                          color: 'var(--gold)',
                          paddingLeft: 4
                        }}>
                          <BookOpen size={10} />
                          <span>Used curated knowledge</span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Loading */}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{ display: 'flex', gap: 14, alignItems: 'flex-start', marginBottom: 28 }}
                >
                  <div style={{
                    width: 40, height: 40, borderRadius: 14, flexShrink: 0,
                    background: 'linear-gradient(135deg, #1C1917, #5B3FC8)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 6px 20px #5B3FC835'
                  }}>
                    <Bot size={18} color="#F0DFA8" />
                  </div>
                  <div style={{
                    padding: '14px 20px',
                    borderRadius: '4px 20px 20px 20px',
                    background: 'rgba(255,252,245,0.95)',
                    border: '1.5px solid #C9A84C22',
                    boxShadow: '0 6px 32px #1C191710',
                    display: 'flex', alignItems: 'center', gap: 10
                  }}>
                    <Loader2 size={18} style={{ color: 'var(--violet)', animation: 'spin 1s linear infinite' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--violet)', opacity: 0.8 }}>
                      The Sage is weaving the next chapter…
                    </span>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* ─── Input ─── */}
          <div style={{
            padding: '20px 24px 24px',
            background: 'linear-gradient(0deg, rgba(250,247,242,0.98) 60%, transparent)',
            backdropFilter: 'blur(12px)'
          }}>
            <div style={{ maxWidth: 720, margin: '0 auto' }}>
              <form onSubmit={handleSubmit}>
                <div className="input-glow" style={{
                  display: 'flex', alignItems: 'center',
                  background: 'rgba(255,252,248,0.98)',
                  border: '2px solid #C9A84C35',
                  borderRadius: 28,
                  padding: '6px 6px 6px 20px',
                  boxShadow: '0 8px 40px #1C191712, 0 2px 0 #C9A84C18',
                  transition: 'all 0.3s ease'
                }}>
                  {/* Sparkle accent */}
                  <Sparkles size={16} style={{ color: 'var(--gold)', marginRight: 10, flexShrink: 0 }} />

                  <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder={turnNumber > 0 ? "Continue the adventure…" : "Ask to learn a math concept…"}
                    disabled={isLoading}
                    style={{
                      flex: 1, background: 'transparent', border: 'none', outline: 'none',
                      fontSize: 14.5, fontWeight: 500,
                      color: 'var(--ink)', caretColor: 'var(--violet)',
                      fontFamily: 'Plus Jakarta Sans, sans-serif'
                    }}
                    autoFocus
                  />

                  <button
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    style={{
                      width: 44, height: 44, borderRadius: 20,
                      border: 'none', cursor: !input.trim() || isLoading ? 'not-allowed' : 'pointer',
                      background: !input.trim() || isLoading
                        ? 'linear-gradient(135deg, #D6D1CB, #C8C3BC)'
                        : 'linear-gradient(135deg, #1C1917 0%, #3C3732 50%, #5B3FC8 100%)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0,
                      boxShadow: !input.trim() || isLoading ? 'none' : '0 4px 16px #5B3FC840',
                      transition: 'all 0.25s ease',
                      transform: 'scale(1)'
                    }}
                    onMouseEnter={e => { if (input.trim() && !isLoading) e.currentTarget.style.transform = 'scale(1.05)'; }}
                    onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                  >
                    <Send size={18} color={!input.trim() || isLoading ? '#A09890' : '#FAF7F2'} />
                  </button>
                </div>
              </form>

              <p style={{
                textAlign: 'center', fontSize: 11, fontWeight: 500,
                color: '#A09890', marginTop: 12, letterSpacing: '0.02em'
              }}>
                MathTales AI · 10–20 turn learning adventures · Always verify math concepts
              </p>
            </div>
          </div>
        </main>
      </div>
    </>
  );
}