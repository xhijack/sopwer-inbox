/* Sopwer Inbox — Manager modals (Canned manager, AI settings) + toasts */
const { useState: useM, useRef: useMR } = React;

/* ───────────── KELOLA BALASAN CEPAT ───────────── */
function CannedManager({ canned, onSave, onClose }) {
  const [list, setList] = useM(canned);
  const [form, setForm] = useM(null); // {id|null, title, slug, body}
  function startAdd() { setForm({ id: null, title: '', slug: '', body: '' }); }
  function startEdit(c) { setForm({ id: c.id, title: c.title, slug: c.slug, body: c.body }); }
  function remove(id) { setList(l => l.filter(c => c.id !== id)); }
  function commit() {
    if (!form.title.trim() || !form.slug.trim() || !form.body.trim()) return;
    const slug = form.slug.trim().replace(/^\//, '').replace(/\s+/g, '-').toLowerCase();
    if (form.id) setList(l => l.map(c => c.id === form.id ? { ...c, title: form.title.trim(), slug, body: form.body.trim() } : c));
    else setList(l => [...l, { id: 'cn' + Date.now(), title: form.title.trim(), slug, body: form.body.trim() }]);
    setForm(null);
  }
  return (
    <div className="overlay" onClick={onClose}>
      <div className="sheet" style={{ maxWidth: 600 }} onClick={e => e.stopPropagation()}>
        <div className="sheet-head">
          <div className="ic"><Ic.MessageSquare size={20}/></div>
          <div>
            <h2>Kelola Balasan Cepat</h2>
            <p>Balasan yang muncul saat agen mengetik <code style={{fontFamily:'var(--font-mono)'}}>/</code> di composer.</p>
            <span className="mgr-badge"><Ic.Lock size={10}/>AKSES MANAGER</span>
          </div>
          <button className="x" onClick={onClose}><Ic.X size={18}/></button>
        </div>
        <div className="sheet-body">
          {form && (
            <div className="cm-form">
              <div className="row">
                <div className="fld"><label>Judul</label><input value={form.title} placeholder="mis. Salam pembuka" onChange={e => setForm({ ...form, title: e.target.value })}/></div>
                <div className="fld slug-fld" style={{ maxWidth: 180 }}><label>Shortcut</label><input value={form.slug} placeholder="halo" onChange={e => setForm({ ...form, slug: e.target.value })}/></div>
              </div>
              <div className="fld"><label>Isi balasan</label><textarea rows={3} value={form.body} placeholder="Tulis isi balasan…" onChange={e => setForm({ ...form, body: e.target.value })}/></div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 4 }}>
                <button className="btn btn-ghost" onClick={() => setForm(null)}>Batal</button>
                <button className="btn btn-primary" onClick={commit}>{form.id ? 'Simpan perubahan' : 'Tambah balasan'}</button>
              </div>
            </div>
          )}
          {!form && (
            <button className="btn btn-outline" style={{ marginBottom: 14, width: '100%', justifyContent: 'center' }} onClick={startAdd}><Ic.Plus size={15}/>Tambah balasan cepat</button>
          )}
          {list.map(c => (
            <div className="cm-item" key={c.id}>
              <span className="slug">/{c.slug}</span>
              <div className="body"><div className="ttl">{c.title}</div><div className="txt">{c.body}</div></div>
              <div className="acts">
                <button onClick={() => startEdit(c)} title="Edit"><Ic.Edit size={14}/></button>
                <button className="del" onClick={() => remove(c.id)} title="Hapus"><Ic.Trash size={14}/></button>
              </div>
            </div>
          ))}
          {list.length === 0 && <div style={{ textAlign: 'center', color: 'var(--fg-3)', fontSize: 13, padding: '20px 0' }}>Belum ada balasan cepat. Tambahkan yang pertama.</div>}
        </div>
        <div className="sheet-foot">
          <button className="btn btn-ghost" onClick={onClose}>Tutup</button>
          <button className="btn btn-primary" onClick={() => { onSave(list); onClose(); }}>Simpan ({list.length})</button>
        </div>
      </div>
    </div>
  );
}

/* ───────────── SETTINGAN AI ───────────── */
function AISettings({ ai, onChange, onClose }) {
  const [test, setTest] = useM('idle'); // idle | testing | ok
  const isCloud = ai.provider !== 'ollama';
  function runTest() { setTest('testing'); setTimeout(() => setTest('ok'), 1300); }
  const PROVIDERS = [
    { id: 'ollama', nm: 'Ollama', tag: 'Lokal', icon: <Ic.Server size={17}/> },
    { id: 'claude', nm: 'Claude', tag: 'Cloud', icon: <Ic.Cloud size={17}/> },
    { id: 'openai', nm: 'OpenAI', tag: 'Cloud', icon: <Ic.Cloud size={17}/> },
  ];
  return (
    <div className="overlay" onClick={onClose}>
      <div className="sheet" onClick={e => e.stopPropagation()}>
        <div className="sheet-head">
          <div className="ic"><Ic.Sparkles size={20}/></div>
          <div>
            <h2>Settingan AI</h2>
            <p>Agent-assist (“Sarankan balasan”). Provider-agnostic — agen selalu di loop, tidak ada auto-send.</p>
            <span className="mgr-badge"><Ic.Lock size={10}/>AKSES MANAGER</span>
          </div>
          <button className="x" onClick={onClose}><Ic.X size={18}/></button>
        </div>
        <div className="sheet-body">
          <div className="ai-section">
            <div className="ai-row">
              <div><div className="lbl">Aktifkan AI assist</div><div className="sub">Tombol “Sarankan balasan” muncul di composer untuk semua agen.</div></div>
              <button className={'switch' + (ai.enabled ? ' on' : '')} onClick={() => onChange({ enabled: !ai.enabled })}/>
            </div>
          </div>

          <div className="ai-section" style={{ opacity: ai.enabled ? 1 : .5, pointerEvents: ai.enabled ? 'auto' : 'none' }}>
            <div className="fld" style={{ marginBottom: 4 }}><label>Provider</label></div>
            <div className="provider-grid">
              {PROVIDERS.map(p => (
                <button key={p.id} className={'prov' + (ai.provider === p.id ? ' on' : '')} onClick={() => { onChange({ provider: p.id, model: '' }); setTest('idle'); }}>
                  <div className="pic">{p.icon}{ai.provider === p.id && <Ic.CheckCircle size={16}/>}</div>
                  <div className="nm">{p.nm}</div><div className="tag">{p.tag}</div>
                </button>
              ))}
            </div>

            <div style={{ marginTop: 14 }}>
              {!isCloud ? (
                <div className="cm-form" style={{ marginBottom: 0 }}>
                  <div className="row">
                    <div className="fld"><label>Endpoint</label><input value={ai.endpoint} onChange={e => onChange({ endpoint: e.target.value })} placeholder="http://localhost:11434"/></div>
                    <div className="fld" style={{ maxWidth: 200 }}><label>Model</label><input value={ai.model} onChange={e => onChange({ model: e.target.value })} placeholder="llama3.1:8b"/></div>
                  </div>
                </div>
              ) : (
                <div className="cm-form" style={{ marginBottom: 0 }}>
                  <div className="row">
                    <div className="fld"><label>API key</label><input type="password" value={ai.apiKey} onChange={e => onChange({ apiKey: e.target.value })} placeholder="sk-…"/></div>
                    <div className="fld" style={{ maxWidth: 200 }}><label>Model</label><input value={ai.model} onChange={e => onChange({ model: e.target.value })} placeholder={ai.provider === 'claude' ? 'claude-sonnet-4' : 'gpt-4o'}/></div>
                  </div>
                </div>
              )}

              {!isCloud ? (
                <div className="residency local"><Ic.Server size={16}/><div><b>Data tinggal di server Anda.</b> Isi chat tidak keluar dari infrastruktur sendiri — pilihan paling aman untuk data pelanggan.</div></div>
              ) : (
                <div className="residency cloud"><Ic.AlertTriangle size={16}/><div><b>Isi chat dikirim ke server {ai.provider === 'claude' ? 'Anthropic' : 'OpenAI'} di luar negeri.</b> Pastikan sesuai kebijakan privasi & persetujuan pelanggan Anda.</div></div>
              )}

              <div className="test-row">
                <button className="btn btn-outline" onClick={runTest} disabled={test === 'testing'}>
                  {test === 'testing' ? <><span className="spin" style={{display:'inline-flex'}}><Ic.Loader size={14}/></span>Menguji…</> : <><Ic.Wifi size={15}/>Tes koneksi</>}
                </button>
                {test === 'ok' && <span className="test-status ok"><span className="d"/>Koneksi berhasil · {isCloud ? ai.provider : 'Ollama'} siap</span>}
                {test === 'testing' && <span className="test-status testing"><span className="d"/>Menghubungi provider…</span>}
              </div>
            </div>
          </div>
        </div>
        <div className="sheet-foot">
          <button className="btn btn-primary" onClick={onClose}>Selesai</button>
        </div>
      </div>
    </div>
  );
}

/* ───────────── TOASTS ───────────── */
function ToastStack({ toasts, onOpen, onDismiss }) {
  const { CHANNELS } = window.INBOX;
  if (!toasts.length) return null;
  return (
    <div className="toast-stack">
      {toasts.map(c => {
        const ch = CHANNELS[c.channelId];
        const prev = window.lastPreview(c);
        return (
          <div className="toast-card" key={c.id} onClick={() => onOpen(c.id)}>
            <div className="av" style={{ background: c.contact.color }}>{c.contact.initials}
              <span className={'ch ' + ch.type}><ChannelGlyph ch={ch.type} size={8}/></span>
            </div>
            <div className="b">
              <div className="t">{c.contact.name}<span className="when">baru saja</span></div>
              <div className="m">{prev.text}</div>
            </div>
            <button className="x" onClick={e => { e.stopPropagation(); onDismiss(c.id); }}><Ic.X size={15}/></button>
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, { CannedManager, AISettings, ToastStack });
