import React, { useState, useRef, useEffect } from 'react'

const API = '/api'
const SUGGESTIONS = [
  '¿Qué significa el error E-101 en la perfiladora?',
  '¿Cómo ajusto la presión hidráulica?',
  'El perfil se desvía hacia la izquierda',
  '¿Cada cuánto hay que lubricar los rodillos?',
]

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [machines, setMachines] = useState([])
  const [selectedMachine, setSelectedMachine] = useState(null)
  const [apiStatus, setApiStatus] = useState('checking')
  const chatRef = useRef(null)

  useEffect(() => {
    fetch(API + '/health')
      .then(r => r.json())
      .then(d => {
        setApiStatus(d.llm_ready ? 'ready' : 'no-llm')
        return fetch(API + '/machines')
      })
      .then(r => r.json())
      .then(d => setMachines(d.machines || []))
      .catch(() => setApiStatus('error'))
  }, [])

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
  }, [messages])

  async function sendMessage(text) {
    if (!text.trim() || loading) return
    const question = text.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const res = await fetch(API + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          machine_filter: selectedMachine || undefined,
        }),
      })
      const data = await res.json()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ Error de conexión. Verifica que el servidor esté corriendo.',
      }])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  function formatContent(text) {
    if (!text) return ''
    // Bold numbers + causes/solutions headers
    let formatted = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br/>')
      .replace(/^(\d+\.)/gm, '<br/>$1')
    return formatted
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="header-logo">K</div>
          <div className="header-title">
            <h1>KAVANA Assistant</h1>
            <span>Asistente Técnico Industrial</span>
          </div>
        </div>
        <div className="header-status">
          <span className="status-dot" />
          {apiStatus === 'ready' ? 'Conectado' : apiStatus === 'no-llm' ? 'Sin LLM' : 'Verificando...'}
        </div>
      </header>

      {/* Machine Selector */}
      {machines.length > 0 && (
        <div className="machine-bar">
          <button
            className={`machine-chip ${!selectedMachine ? 'active' : ''}`}
            onClick={() => setSelectedMachine(null)}
          >
            Todas las máquinas
          </button>
          {machines.map(m => (
            <button
              key={m.machine}
              className={`machine-chip ${selectedMachine === m.machine ? 'active' : ''}`}
              onClick={() => setSelectedMachine(selectedMachine === m.machine ? null : m.machine)}
            >
              {m.machine.split('Modelo')[0].trim()}
            </button>
          ))}
        </div>
      )}

      {/* Chat */}
      <div className="chat-container" ref={chatRef}>
        {messages.length === 0 ? (
          <div className="welcome">
            <div className="welcome-icon">⚙️</div>
            <h2>Bienvenido al asistente técnico</h2>
            <p>
              Pregunta sobre cualquier máquina: errores, mantenimiento,
              ajustes o trucos de fabricación.
            </p>
            <div className="welcome-suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  className="suggestion-btn"
                  onClick={() => sendMessage(s)}
                >
                  💬 {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-bubble">
                <div dangerouslySetInnerHTML={{ __html: formatContent(msg.content) }} />
                {msg.sources && msg.sources.length > 0 && (
                  <div className="message-sources">
                    {msg.sources.map((s, j) => (
                      <span key={j} className="source-badge">
                        {s.machine.split(' ')[0]} · {s.code}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="message assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-bubble">
              <div className="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="input-area">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Pregunta sobre la máquina..."
          disabled={loading}
        />
        <button
          className="send-btn"
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
        >
          ➤
        </button>
      </div>

      <div className="footer">
        KAVANA Systems © 2026 · {' '}
        <a href="https://github.com/kavanasystemsinfo-ui/Kavana-assistant" target="_blank">
          v1.0.0
        </a>
      </div>
    </div>
  )
}
