/* Sopwer Inbox — main app (v2) */
const { useState, useMemo, useEffect } = React;

const BRAND_MAP = {
  sopwer: { p: '#2E78D9', h: '#1F5FB8', d: '#154693', soft: '#EAF3FC', s100: '#C9DFF5' },
  brief:  { p: '#1E5BB0', h: '#184C94', d: '#123A70', soft: '#E9F1FA', s100: '#C2D9F0' },
};

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "density": "comfortable",
  "brand": "sopwer",
  "accent": "blue",
  "erpCard": true,
  "banner": false
}/*EDITMODE-END*/;

function InboxApp() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const seed = window.INBOX.CONVERSATIONS;

  const [convs, setConvs] = useState(() => JSON.parse(JSON.stringify(seed)));
  const [canned, setCanned] = useState(() => JSON.parse(JSON.stringify(window.INBOX.CANNED)));
  const [statusFilter, setStatusFilter] = useState('open');
  const [scope, setScope] = useState('all');
  const [channelSel, setChannelSel] = useState([]);          // [] = all channels
  const [search, setSearch] = useState('');
  const [filterAgent, setFilterAgent] = useState(null);
  const [unreplied, setUnreplied] = useState(false);
  const [sortBy, setSortBy] = useState('newest');
  const [selId, setSelId] = useState('c1');
  const [cpCollapsed, setCpCollapsed] = useState(false);
  const [demo, setDemo] = useState('normal');
  const [bannerDismissed, setBannerDismissed] = useState(false);

  const [role, setRole] = useState('manager');               // 'agent' | 'manager'
  const [agentStatus, setAgentStatus] = useState('available');
  const [modal, setModal] = useState(null);                  // null | 'canned' | 'ai'
  const [toasts, setToasts] = useState([]);
  const [ai, setAi] = useState({ enabled: true, provider: 'ollama', endpoint: 'http://localhost:11434', model: 'llama3.1:8b', apiKey: '' });

  const counts = useMemo(() => {
    const c = { open: 0, pending: 0, resolved: 0, mine: 0, all: convs.length, byChannel: {} };
    convs.forEach(x => { c[x.status]++; if (x.assignee === 'me') c.mine++; c.byChannel[x.channelId] = (c.byChannel[x.channelId] || 0) + 1; });
    return c;
  }, [convs]);

  const lastInIsCustomer = (c) => { const v = c.messages.filter(m => m.type !== 'note'); const m = v[v.length-1]; return m && m.dir === 'in'; };

  const filtered = useMemo(() => {
    if (demo === 'emptyList') return [];
    let r = convs.filter(c => c.status === statusFilter);
    if (scope === 'me') r = r.filter(c => c.assignee === 'me');
    if (channelSel.length) r = r.filter(c => channelSel.includes(c.channelId));
    if (filterAgent) r = r.filter(c => c.assignee === filterAgent);
    if (unreplied) r = r.filter(lastInIsCustomer);
    if (search.trim()) {
      const q = search.toLowerCase();
      r = r.filter(c => c.contact.name.toLowerCase().includes(q) || c.contact.handle.toLowerCase().includes(q));
    }
    if (sortBy === 'oldest') r = [...r].reverse();
    return r;
  }, [convs, statusFilter, scope, channelSel, filterAgent, unreplied, search, sortBy, demo]);

  const searchEmpty = demo !== 'emptyList' && search.trim() !== '' && filtered.length === 0;
  const selConv = demo === 'noSelect' ? null : convs.find(c => c.id === selId) || null;
  const loading = demo === 'loading';
  const bannerOn = (demo === 'disconnected' || t.banner) && !bannerDismissed;

  const brand = BRAND_MAP[t.brand] || BRAND_MAP.sopwer;
  const rootStyle = { '--pri': brand.p, '--pri-hover': brand.h, '--pri-press': brand.d, '--sw-blue-50': brand.soft, '--sw-blue-100': brand.s100 };
  const appCls = ['app', t.density === 'compact' ? 'compact' : '', t.accent === 'green' ? 'acc-green' : '', cpCollapsed ? 'cp-collapsed' : ''].filter(Boolean).join(' ');

  function selectConv(id) {
    setDemo(d => (d === 'emptyList' || d === 'noSelect' || d === 'loading') ? 'normal' : d);
    setSelId(id);
    setConvs(cs => cs.map(c => c.id === id ? { ...c, unread: 0 } : c));
  }
  function updateConv(id, patch) { setConvs(cs => cs.map(c => c.id === id ? { ...c, ...patch } : c)); }
  function toggleChannel(id) { setChannelSel(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]); }

  function sendMsg(text, mode) {
    if (!selConv) return;
    const id = 'x' + Date.now();
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
    if (mode === 'note') {
      const note = { id, dir: 'out', type: 'note', text, time, agent: 'me' };
      setConvs(cs => cs.map(c => c.id === selConv.id ? { ...c, messages: [...c.messages, note] } : c));
      return;
    }
    const msg = { id, dir: 'out', type: 'text', text, time, status: 'pending', agent: 'me' };
    setConvs(cs => cs.map(c => c.id === selConv.id ? { ...c, messages: [...c.messages, msg], lastTime: 'baru' } : c));
    const setStatus = (s) => setConvs(cs => cs.map(c => c.id === selConv.id ? { ...c, messages: c.messages.map(m => m.id === id ? { ...m, status: s } : m) } : c));
    setTimeout(() => setStatus('sent'), 600);
    setTimeout(() => setStatus('delivered'), 1500);
    setTimeout(() => setStatus('read'), 3200);
  }
  function retryMsg(mid) {
    if (!selConv) return;
    const setStatus = (s) => setConvs(cs => cs.map(c => c.id === selConv.id ? { ...c, messages: c.messages.map(m => m.id === mid ? { ...m, status: s } : m) } : c));
    setStatus('pending');
    setTimeout(() => setStatus('sent'), 700);
    setTimeout(() => setStatus('delivered'), 1600);
  }

  // AI agent-assist: returns a promise (rejects if cloud provider without key — realistic fail path)
  function suggestReply() {
    return new Promise((resolve, reject) => {
      const cloud = ai.provider !== 'ollama';
      setTimeout(() => {
        if (cloud && !ai.apiKey.trim()) { reject(new Error('no-key')); return; }
        const D = window.INBOX.AI_DRAFTS;
        resolve(D[Math.floor(Math.random() * D.length)]);
      }, 1100);
    });
  }

  // contact panel edits
  function rename(name) { if (selConv) updateConv(selConv.id, { contact: { ...selConv.contact, name } }); }
  function addTag(tag) { if (selConv && !(selConv.tags||[]).includes(tag)) updateConv(selConv.id, { tags: [...(selConv.tags||[]), tag] }); }
  function removeTag(tag) { if (selConv) updateConv(selConv.id, { tags: (selConv.tags||[]).filter(x => x !== tag) }); }
  function setNote(note) { if (selConv) updateConv(selConv.id, { note }); }

  // simulate incoming chat → toast + bump
  function simulateIncoming() {
    const candidates = convs.filter(c => c.id !== selId);
    const target = candidates[Math.floor(Math.random() * candidates.length)];
    if (!target) return;
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
    const incoming = { id: 'in' + Date.now(), dir: 'in', type: 'text', text: 'Halo min, mohon info terbaru untuk pesanan saya ya 🙏', time };
    setConvs(cs => {
      const updated = cs.map(c => c.id === target.id ? { ...c, status: 'open', unread: (c.unread||0)+1, lastTime: 'baru', messages: [...c.messages, incoming] } : c);
      const moved = updated.find(c => c.id === target.id);
      return [moved, ...updated.filter(c => c.id !== target.id)];
    });
    setToasts(ts => ts.find(x => x.id === target.id) ? ts : [...ts, { ...target, status: 'open', messages: [...target.messages, incoming] }]);
    setTimeout(() => setToasts(ts => ts.filter(x => x.id !== target.id)), 5200);
  }

  const DEMOS = [['normal','Normal'],['loading','Loading'],['emptyList','List kosong'],['noSelect','Belum dipilih'],['disconnected','Kanal terputus']];
  function gotoDemo(d) {
    setBannerDismissed(false);
    if (d === 'disconnected') { setSelId('c1'); setStatusFilter('open'); }
    if (d === 'normal') setSelId('c1');
    setDemo(d);
  }

  return (
    <div className={appCls} style={rootStyle}>
      <Sidebar counts={counts} filter={statusFilter} setFilter={(s)=>{setStatusFilter(s); setDemo(d=>d==='emptyList'?'normal':d);}}
        scope={scope} setScope={setScope} channelSel={channelSel} toggleChannel={toggleChannel} clearChannels={() => setChannelSel([])}
        role={role} onOpenCanned={() => setModal('canned')} onOpenAI={() => setModal('ai')}
        agentStatus={agentStatus} setAgentStatus={setAgentStatus}/>

      <ConversationList convs={filtered} selId={selConv ? selConv.id : null} onSelect={selectConv}
        search={search} setSearch={setSearch} statusFilter={statusFilter} scope={scope} setScope={setScope}
        loading={loading} searchEmpty={searchEmpty}
        filterAgent={filterAgent} setFilterAgent={setFilterAgent} unreplied={unreplied} setUnreplied={setUnreplied} sortBy={sortBy} setSortBy={setSortBy}/>

      <Thread conv={selConv} loading={loading} banner={bannerOn} onDismissBanner={() => setBannerDismissed(true)}
        onStatus={(s) => { updateConv(selConv.id, { status: s }); if (s !== statusFilter) setStatusFilter(s); }}
        onAssign={(a) => updateConv(selConv.id, { assignee: a })}
        onSend={sendMsg} onRetry={retryMsg}
        cpCollapsed={cpCollapsed} onToggleCp={() => setCpCollapsed(false)}
        role={role} canned={canned} onManageCanned={() => setModal('canned')} aiEnabled={ai.enabled} onSuggest={suggestReply}/>

      {!cpCollapsed && <ContactPanel conv={selConv} allConvs={convs} showErp={t.erpCard} onClose={() => setCpCollapsed(true)}
        onRename={rename} onAddTag={addTag} onRemoveTag={removeTag} onNote={setNote}/>}

      <ToastStack toasts={toasts} onOpen={(id) => { selectConv(id); setToasts(ts => ts.filter(x => x.id !== id)); }} onDismiss={(id) => setToasts(ts => ts.filter(x => x.id !== id))}/>

      {modal === 'canned' && <CannedManager canned={canned} onSave={setCanned} onClose={() => setModal(null)}/>}
      {modal === 'ai' && <AISettings ai={ai} onChange={(patch) => setAi(a => ({ ...a, ...patch }))} onClose={() => setModal(null)}/>}

      {/* prototype chrome */}
      <div className="role-switch">
        <span className="dl">Peran</span>
        <button className={role === 'agent' ? 'on' : ''} onClick={() => setRole('agent')}>Agen</button>
        <button className={role === 'manager' ? 'on' : ''} onClick={() => setRole('manager')}>Manager</button>
      </div>

      <div className="demo-switch">
        <span className="dl">State</span>
        <select className="demo-select" value={demo} onChange={(e) => gotoDemo(e.target.value)}>
          {DEMOS.map(([id, label]) => (<option key={id} value={id}>{label}</option>))}
        </select>
        <button className="chat-sim" onClick={simulateIncoming} title="Simulasikan chat baru masuk"><Ic.Bell size={13} style={{ verticalAlign: -2, marginRight: 4 }}/>Chat masuk</button>
      </div>

      <TweaksPanel>
        <TweakSection label="Tampilan daftar"/>
        <TweakRadio label="Kepadatan" value={t.density} options={['comfortable','compact']} onChange={(v) => setTweak('density', v)}/>
        <TweakSection label="Brand & warna"/>
        <TweakRadio label="Biru utama" value={t.brand} options={['sopwer','brief']} onChange={(v) => setTweak('brand', v)}/>
        <TweakRadio label="Bubble keluar" value={t.accent} options={['blue','green']} onChange={(v) => setTweak('accent', v)}/>
        <TweakSection label="Panel kontak"/>
        <TweakToggle label="Tampilkan kartu ERPNext" value={t.erpCard} onChange={(v) => setTweak('erpCard', v)}/>
        <TweakSection label="Status kanal"/>
        <TweakToggle label="Banner kanal terputus" value={t.banner} onChange={(v) => setTweak('banner', v)}/>
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<InboxApp/>);
