import React, { useState, useRef, useEffect, useCallback } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './AIHelperChat.css';

// ─── Agentic Quick Suggestions ────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { label: '🔬 Analyze image', prompt: 'Analyze the current micrograph and describe what you see.' },
  { label: '📏 Measure defects', prompt: 'What is the estimated defect density from the extracted data?' },
  { label: '🧮 Burgers vector?', prompt: 'Explain the Burgers vector type in this sample.' },
  { label: '📊 Plot metrics', prompt: 'Plot the key crystallographic metrics as a bar chart.' },
  { label: '✏️ Pen tool', prompt: 'Activate the neon pen tool.' },
  { label: '📐 Measure tool', prompt: 'Activate the measurement tool.' },
];

// ─── Capability Chips ─────────────────────────────────────────────────────────
const CAPS = [
  { label: '🛠 UI Control', type: 'tool' },
  { label: '📊 Live Data', type: 'data' },
  { label: '👁 Image Context', type: 'view' },
  { label: '📈 Graph Gen', type: 'graph' },
];

// ─── Markdown-like text renderer ─────────────────────────────────────────────
function RenderText({ text }) {
  if (!text) return null;

  // Split into segments: code blocks, inline code, bold
  const lines = text.split('\n');

  return lines.map((line, lineIdx) => {
    // Detect code block markers
    if (line.startsWith('```')) {
      return null; // handled by block parser below
    }

    // Inline bold + code
    const parts = [];
    let remaining = line;
    let keyIdx = 0;

    // Parse **bold** and `code`
    const regex = /(\*\*(.*?)\*\*|`([^`]+)`)/g;
    let match;
    let lastIndex = 0;

    while ((match = regex.exec(remaining)) !== null) {
      if (match.index > lastIndex) {
        parts.push(<span key={keyIdx++}>{remaining.slice(lastIndex, match.index)}</span>);
      }
      if (match[2] !== undefined) {
        parts.push(<strong key={keyIdx++}>{match[2]}</strong>);
      } else if (match[3] !== undefined) {
        parts.push(<code key={keyIdx++} className="inline-code">{match[3]}</code>);
      }
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < remaining.length) {
      parts.push(<span key={keyIdx++}>{remaining.slice(lastIndex)}</span>);
    }

    // Bullet points
    if (line.startsWith('- ') || line.startsWith('• ')) {
      return <div key={lineIdx} style={{ display: 'flex', gap: '6px', marginBottom: '3px' }}>
        <span style={{ color: '#6366f1', flexShrink: 0 }}>▸</span>
        <span>{parts}</span>
      </div>;
    }

    if (line === '') return <div key={lineIdx} style={{ height: '6px' }} />;
    return <div key={lineIdx}>{parts}</div>;
  });
}

// ─── Render full message content (with code blocks + graphs) ─────────────────
function RenderMessage({ text }) {
  if (!text) return null;

  const segments = [];
  const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }
    const lang = match[1];
    const code = match[2].trim();

    if (lang === 'json') {
      try {
        const parsed = JSON.parse(code);
        if (parsed.data && parsed.title) {
          segments.push({ type: 'graph', content: parsed });
        } else {
          segments.push({ type: 'code', lang, content: code });
        }
      } catch {
        segments.push({ type: 'code', lang, content: code });
      }
    } else {
      segments.push({ type: 'code', lang, content: code });
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) });
  }

  return segments.map((seg, i) => {
    if (seg.type === 'text') {
      return <div key={i}><RenderText text={seg.content} /></div>;
    }
    if (seg.type === 'code') {
      return <pre key={i} className="msg-code-block">{seg.content}</pre>;
    }
    if (seg.type === 'graph') {
      const { title, type, data } = seg.content;
      const COLORS = ['#6366f1','#8b5cf6','#10b981','#f59e0b','#ef4444','#06b6d4'];
      return (
        <div key={i} className="chat-graph-container">
          <div className="chat-graph-title">{title}</div>
          <ResponsiveContainer width="100%" height={140}>
            {type === 'line' ? (
              <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: '11px' }} />
                <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={{ fill: '#6366f1', r: 3 }} />
              </LineChart>
            ) : (
              <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: '11px' }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {data.map((_, idx) => <Cell key={idx} fill={COLORS[idx % COLORS.length]} />)}
                </Bar>
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      );
    }
    return null;
  });
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function AIHelperChat({ contextData, scientistName, onAgentCommand, material, gVector, zoneAxis, defects }) {
  const INITIAL_MSG = {
    role: 'ai',
    text: `**Neural Core Online** ⚡\n\nWelcome back, ${scientistName || 'Scientist'}. I am your agentic AI co-pilot.\n\n- I can **analyze** your micrographs\n- **Control** the canvas tools\n- **Plot** crystallographic data\n- Answer physics questions in real-time\n\nWhat would you like to explore?`
  };

  const [messages, setMessages] = useState([INITIAL_MSG]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);


  useEffect(() => { scrollToBottom(); }, [messages, isTyping, scrollToBottom]);

  // Auto-resize textarea
  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = '22px';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 100) + 'px';
    }
  };

  const handleSend = async (msg) => {
    const userMessage = msg || input;
    if (!userMessage.trim() || isTyping) return;

    const newMessages = [...messages, { role: 'user', text: userMessage }];
    setMessages(newMessages);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = '22px';
    setIsTyping(true);

    // Build context from real API response fields
    let contextString = 'No analysis run yet. Upload a micrograph and run analysis first.';
    let imageStatus = 'No';
    if (contextData) {
      imageStatus = 'Yes';
      const totalDefects  = contextData['Total Defects Detected'] ?? 'N/A';
      const avgDiameter   = contextData['Average Diameter']       ?? 'N/A';
      const domType       = contextData['Dominant Defect Type']   ?? 'N/A';
      const density       = contextData['Estimated Density']      ?? 'N/A';
      contextString = [
        `Material System: ${material || 'Not set'}`,
        `g-vector: ${gVector || 'Not set'}`,
        `Zone Axis: [${zoneAxis || 'Not set'}]`,
        `Total Defects: ${totalDefects}`,
        `Average Diameter: ${avgDiameter}`,
        `Dominant Type: ${domType}`,
        `Areal Density: ${density}`,
        `Individual Defects Available: ${Array.isArray(defects) ? defects.length : 0}`,
      ].join(' | ');
    } else {
      // Still show whatever config is set even without analysis
      contextString = `Material System: ${material || 'Not set'} | g-vector: ${gVector || 'Not set'} | Zone Axis: [${zoneAxis || 'Not set'}] | Analysis: Not yet run`;
    }

    const systemPrompt = `You are NEMOTRON CORE — the agentic AI assistant embedded in S/TEM Engine Studio OS, a premium material physics analysis platform.

You are currently in the RIGHT PANEL of a 3-column workspace:
- LEFT: Config panel (crystal system, diffraction vector g, zone axis, scale calibration)  
- CENTER: Canvas (pan, measure, Fourier filter, annotate micrographs)
- RIGHT: Data & AI (extracted metrics + you)

FORMATTING RULES (STRICT):
1. Use short bullet points with "▸" (just use "- " and the renderer will convert)
2. No long paragraphs — be concise and scientific
3. For graphs, output ONLY this JSON block and nothing else for the chart:
\`\`\`json
{"title": "Title", "type": "bar", "data": [{"name": "A", "value": 10}]}
\`\`\`
Use "bar" or "line" for type.

UI CONTROL COMMANDS (output these anywhere in your response):
- [ACTION: TOOL_PEN] → Activates Neon Marker
- [ACTION: TOOL_CIRCLE] → Activates Circle tool
- [ACTION: TOOL_MEASURE] → Activates Measurement Scale
- [ACTION: TOOL_ERASER] → Activates Eraser
- [ACTION: CLEAR_CANVAS] → Clears canvas
- [ACTION: TOGGLE_DARK_FIELD] → Inverts image to Dark Field

LIVE STATE:
Micrograph Uploaded: ${imageStatus}
Extracted Data: ${contextString}`;

    try {
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages, system_prompt: systemPrompt })
      });

      if (!response.ok) throw new Error('Backend offline');

      setMessages(prev => [...prev, { role: 'ai', text: '' }]);
      setIsTyping(false);

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(l => l.trim());

        for (const line of lines) {
          try {
            const parsed = JSON.parse(line);
            if (parsed.response !== undefined) {
              setMessages(prev => {
                const updated = [...prev];
                let currentText = updated[updated.length - 1].text + parsed.response;

                // Agentic action parser
                const actionMatch = currentText.match(/\[ACTION:\s*([A-Z_]+)\]/g);
                if (actionMatch) {
                  actionMatch.forEach(act => {
                    const name = act.match(/\[ACTION:\s*([A-Z_]+)\]/)[1];
                    if (onAgentCommand) onAgentCommand(name);
                  });
                  currentText = currentText.replace(/\[ACTION:\s*[A-Z_]+\]/g, '');
                }

                updated[updated.length - 1] = { ...updated[updated.length - 1], text: currentText };
                return updated;
              });
            }
          } catch (e) {
            // ignore parse errors
          }
        }
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'ai', text: `**Neural Engine Offline**\n\n- Ensure \`api_server.py\` is running on port 8000\n- Check your API key configuration\n- Run: \`python src/api_server.py\`` }
      ]);
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    const fresh = [{ role: 'ai', text: `**Neural Core Online** ⚡\n\nChat history cleared. How can I assist you?` }];
    setMessages(fresh);
  };

  return (
    <div className="studio-chat-container">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-icon">🧠</div>
          <div className="chat-header-info">
            <h3>Nemotron Core</h3>
            <p>AGENTIC AI · OPENROUTER</p>
          </div>
        </div>
        <div className="chat-header-right">
          <button
            className="clear-chat-btn"
            onClick={clearChat}
            title="Clear chat history"
          >
            🗑
          </button>
          <div className="status-indicator">
            <div className="status-dot" />
            Online
          </div>
        </div>
      </div>

      {/* Capability chips */}
      <div className="agent-caps">
        {CAPS.map(c => (
          <div key={c.label} className={`cap-chip ${c.type}`}>{c.label}</div>
        ))}
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`msg-row ${msg.role}`}>
            <div className={`msg-avatar ${msg.role === 'ai' ? 'ai-av' : 'user-av'}`}>
              {msg.role === 'ai' ? '⚡' : '👤'}
            </div>
            <div className={`message ${msg.role}`}>
              <RenderMessage text={msg.text} />
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="msg-row ai">
            <div className="msg-avatar ai-av">⚡</div>
            <div className="message ai">
              <div className="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick action buttons */}
      <div className="quick-actions">
        {QUICK_ACTIONS.map(qa => (
          <button
            key={qa.label}
            className="quick-btn"
            onClick={() => handleSend(qa.prompt)}
            disabled={isTyping}
          >
            {qa.label}
          </button>
        ))}
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            className="chat-input"
            placeholder="Ask the AI or give a command..."
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={isTyping}
            rows={1}
          />
          <button
            className="chat-send-btn"
            onClick={() => handleSend()}
            disabled={!input.trim() || isTyping}
            title="Send (Enter)"
          >
            <svg viewBox="0 0 24 24">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <div className="input-hint">
          Enter to send · Shift+Enter for new line<br/>
          <span style={{color: '#f87171'}}>Data Privacy Notice: Your queries and context may be sent to third-party AI providers (NVIDIA/OpenRouter).</span>
        </div>
      </div>
    </div>
  );
}
