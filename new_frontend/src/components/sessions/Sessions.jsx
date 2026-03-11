import React, { useState, useEffect } from 'react';
import apiClient from '../../services/api';

function SessionCard({ session, onClick, isActive }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all ${
        isActive
          ? 'bg-primary/5 border-primary/30'
          : 'bg-ivory border-primary/10 hover:border-primary/20 hover:bg-primary/5'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <p className="text-sm font-semibold text-ink line-clamp-1">
          {session.session_name || session.matter || `Session ${session.session_number || ''}`}
        </p>
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
          session.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
        }`}>
          {session.is_active ? 'Active' : 'Closed'}
        </span>
      </div>
      <p className="text-xs text-slate-500 flex items-center gap-1.5">
        <span className="material-symbols-outlined text-xs">forum</span>
        {session.message_count || 0} messages
      </p>
      <p className="text-[10px] text-slate-400 mt-1">
        {session.updated_at ? new Date(session.updated_at).toLocaleDateString('en-IN') : '—'}
      </p>
    </button>
  );
}

export default function Sessions() {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    apiClient.get('talkdoc/sessions/')
      .then((r) => setSessions(r.data?.results ?? r.data ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function loadMessages(sessionId) {
    try {
      const r = await apiClient.get(`talkdoc/session_messages/?session_id=${sessionId}`);
      setMessages(r.data?.results ?? r.data?.messages ?? []);
    } catch {
      setMessages([]);
    }
  }

  function handleSelectSession(session) {
    setSelected(session);
    loadMessages(session.id);
  }

  async function handleSend() {
    if (!input.trim() || !selected || chatLoading) return;
    const text = input.trim();
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: text }]);
    setChatLoading(true);
    try {
      const r = await apiClient.post('talkdoc/query/', {
        session_id: selected.id,
        query: text,
      });
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: r.data?.answer || r.data?.response || 'No response',
          citations: r.data?.citations ?? [],
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: err.response?.data?.error || 'Sorry, could not process that.' },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  const filtered = sessions.filter((s) => {
    if (filter === 'active') return s.is_active;
    if (filter === 'closed') return !s.is_active;
    return true;
  });

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: session list */}
      <aside className="w-80 border-r border-primary/10 bg-slate-50 flex flex-col">
        <div className="p-4 border-b border-primary/10">
          <h2 className="font-bold text-ink mb-3">Sessions</h2>
          <div className="flex gap-1">
            {['all', 'active', 'closed'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`flex-1 py-1.5 text-xs font-semibold rounded transition-all capitalize ${
                  filter === f
                    ? 'bg-primary text-ivory'
                    : 'bg-white border border-slate-200 text-slate-600 hover:border-primary/50'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
          {loading ? (
            [1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-ivory rounded-xl animate-pulse" />
            ))
          ) : filtered.length === 0 ? (
            <div className="text-center py-10">
              <span className="material-symbols-outlined text-slate-300 text-4xl block mb-2">forum</span>
              <p className="text-xs text-slate-400">No sessions found</p>
            </div>
          ) : (
            filtered.map((s) => (
              <SessionCard
                key={s.id}
                session={s}
                onClick={() => handleSelectSession(s)}
                isActive={selected?.id === s.id}
              />
            ))
          )}
        </div>
      </aside>

      {/* Right: chat view */}
      <div className="flex-1 flex flex-col bg-background-light overflow-hidden">
        {selected ? (
          <>
            {/* Session header */}
            <div className="h-14 border-b border-primary/10 bg-ivory flex items-center px-6 gap-3 flex-shrink-0">
              <span className="material-symbols-outlined text-primary">forum</span>
              <div>
                <p className="text-sm font-bold text-ink">
                  {selected.session_name || selected.matter || 'Session'}
                </p>
                <p className="text-xs text-slate-400">
                  {selected.message_count || messages.length} messages
                </p>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-4">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-primary text-ivory rounded-br-sm'
                        : 'bg-white border border-primary/10 text-ink rounded-bl-sm shadow-sm'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-primary/20 space-y-0.5">
                        {msg.citations.map((c, ci) => (
                          <p key={ci} className="text-xs text-ivory/70">
                            [{ci + 1}] {c.filename || c.doc_name} — p.{c.page}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-primary/10 rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex gap-1">
                      {[0, 150, 300].map((d) => (
                        <span
                          key={d}
                          className="w-2 h-2 bg-primary rounded-full animate-bounce"
                          style={{ animationDelay: `${d}ms` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input (only for active sessions) */}
            {selected.is_active && (
              <div className="p-4 border-t border-primary/10 bg-ivory flex gap-3 flex-shrink-0">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Continue the conversation…"
                  className="flex-1 bg-primary/5 border border-primary/20 rounded-lg px-4 py-2.5 text-sm text-ink
                             placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
                <button
                  onClick={handleSend}
                  disabled={chatLoading || !input.trim()}
                  className="size-10 bg-primary text-ivory rounded-lg flex items-center justify-center
                             hover:bg-primary/90 transition-all disabled:opacity-40"
                >
                  <span className="material-symbols-outlined">send</span>
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center">
            <span className="material-symbols-outlined text-slate-300 text-6xl">forum</span>
            <div>
              <h3 className="text-lg font-bold text-ink mb-1">Select a Session</h3>
              <p className="text-sm text-slate-400 max-w-xs">
                Choose a document chat session from the left panel to view the conversation.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
