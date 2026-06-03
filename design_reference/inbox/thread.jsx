/* Sopwer Inbox — thread, bubbles, composer (v2) */
const { useState: useS2, useRef: useR2, useEffect: useE2 } = React;

/* delivery ticks */
function DeliveryTick({ status }) {
  if (status === 'pending') return <span className="tick pending" title="Mengirim…"><Ic.Clock size={13}/></span>;
  if (status === 'sent') return <span className="tick sent" title="Terkirim"><Ic.Check size={15}/></span>;
  if (status === 'delivered') return <span className="tick delivered" title="Tersampaikan"><Ic.CheckCheck size={15}/></span>;
  if (status === 'read') return <span className="tick read" title="Dibaca"><Ic.CheckCheck size={15}/></span>;
  return null;
}

function MediaImage({ media }) {
  const tone = media.tone === 'green' ? 'var(--sw-green-400)' : 'var(--sw-blue-400)';
  const tone2 = media.tone === 'green' ? 'var(--sw-green-600)' : 'var(--sw-blue-600)';
  return (
    <div className="media-img" style={{ width: media.w, maxWidth: '100%' }}>
      <div className="ph" style={{ height: media.h, background: `linear-gradient(135deg, ${tone}, ${tone2})` }}>
        <Ic.Image size={30} style={{ opacity: .7 }}/>
      </div>
    </div>
  );
}
function MediaVideo({ media }) {
  const tone = media.tone === 'green' ? 'var(--sw-green-500)' : 'var(--sw-blue-500)';
  return (
    <div className="media-video" style={{ width: media.w, maxWidth: '100%' }}>
      <div className="pv" style={{ height: media.h, background: `linear-gradient(135deg, ${tone}, var(--sw-ink-700))` }}><Ic.Video size={30} style={{ opacity: .6 }}/></div>
      <div className="pl"><span><Ic.Play size={16}/></span></div>
      <span className="dur">{media.dur}</span>
    </div>
  );
}
function MediaLocation({ media }) {
  return (
    <div className="media-loc">
      <div className="map"><span className="pin"><Ic.MapPin size={26}/></span></div>
      <div className="lc"><Ic.MapPin size={16} style={{ color: 'var(--sw-error)', flexShrink: 0 }}/>
        <div style={{ minWidth: 0 }}><div className="nm">{media.label}</div><div className="sub">Lokasi dibagikan</div></div>
      </div>
    </div>
  );
}

function NoteCard({ m }) {
  const av = m.agent ? window.INBOX.AGENTS[m.agent] : null;
  return (
    <div className="note-row">
      <div className="note-card">
        <div className="nh"><Ic.Lock size={12}/> Catatan internal <span className="who">{av ? av.name : ''}</span></div>
        <div className="nb">{m.text}</div>
        <div className="nt">{m.time} · tidak terkirim ke pelanggan</div>
      </div>
    </div>
  );
}

function Bubble({ m, onRetry }) {
  const isOut = m.dir === 'out';
  const av = isOut && m.agent ? window.INBOX.AGENTS[m.agent] : null;
  return (
    <div className={'row ' + (isOut ? 'out' : 'in') + (m.status === 'failed' ? ' failed' : '')}>
      {isOut && av && <div className="ava" style={{ background: av.color }} title={av.name}>{av.initials}</div>}
      <div className="bubble">
        {m.type === 'image' && <MediaImage media={m.media}/>}
        {m.type === 'video' && <MediaVideo media={m.media}/>}
        {m.type === 'location' && <MediaLocation media={m.media}/>}
        {m.type === 'file' && (
          <div className="media-file">
            <div className="fic"><Ic.File size={18}/></div>
            <div style={{ minWidth: 0 }}><div className="fn">{m.media.name}</div><div className="fs">PDF · {m.media.size}</div></div>
            <span className="dl" title="Unduh"><Ic.Download size={17}/></span>
          </div>
        )}
        {m.type === 'audio' && (
          <div className="media-audio">
            <button className="play"><Ic.Play size={14}/></button>
            <div className="wave">{[10,16,8,20,13,18,7,15,22,11,17,9,14,19,12,8,16,10].map((h,i)=>(<i key={i} style={{height:h}}/>))}</div>
            <span className="dur">{m.media.dur}</span>
          </div>
        )}
        {(m.text || m.caption) && <div className="caption-txt" style={{ marginTop: (m.type==='text'?0:5) }}>{m.text || m.caption}</div>}
        {m.status !== 'failed' && (
          <div className="meta"><span className="tm">{m.time}</span>{isOut && <DeliveryTick status={m.status}/>}</div>
        )}
        {m.status === 'failed' && (
          <div className="fail-line">
            <span className="ft"><Ic.AlertCircle size={12}/> Gagal terkirim</span>
            <button className="retry" onClick={() => onRetry(m.id)}><Ic.RefreshCw size={11} style={{verticalAlign:-1}}/> Coba lagi</button>
          </div>
        )}
      </div>
    </div>
  );
}

function ThreadSkeleton() {
  const rows = [['in','58%'],['in','40%'],['out','52%'],['out','34%'],['in','62%'],['out','46%']];
  return (
    <div className="msgs">
      {rows.map(([side,w],i)=>(
        <div className={'sk-bubble-row '+side} key={i}>
          <div className="sk" style={{ height: 42, width: w, borderRadius: 16, borderBottomLeftRadius: side==='in'?5:16, borderBottomRightRadius: side==='out'?5:16 }}/>
        </div>
      ))}
    </div>
  );
}

function StatusSeg({ status, onChange }) {
  const opts = [['open','Open'],['pending','Pending'],['resolved','Resolved']];
  return (
    <div className="seg">
      {opts.map(([id,label]) => (
        <button key={id} className={(status===id?'on '+id:'')} onClick={() => onChange(id)}>
          {status===id && (id==='resolved' ? <Ic.CheckCircle size={13}/> : <span className="st-dot" style={{background:'currentColor'}}/>)}
          {label}
        </button>
      ))}
    </div>
  );
}

function AssignMenu({ assignee, onAssign }) {
  const [open, setOpen] = useS2(false);
  const ref = useR2(null);
  useE2(() => {
    const h = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h);
  }, []);
  const A = window.INBOX.AGENTS;
  const cur = assignee ? A[assignee] : null;
  const list = [['me',A.me],['rina',A.rina],['budi',A.budi],['dewi',A.dewi]];
  return (
    <div className="menu-wrap" ref={ref}>
      <button className="assign-btn" onClick={() => setOpen(o => !o)}>
        {cur ? <span className="ava" style={{ background: cur.color }}>{cur.initials}</span> : <span className="ava na"><Ic.User size={12}/></span>}
        <span>{cur ? (assignee === 'me' ? 'Saya' : cur.name.split(' ')[0]) : 'Tugaskan'}</span>
        <Ic.ChevronDown size={14} style={{ color: 'var(--fg-3)' }}/>
      </button>
      {open && (
        <div className="menu">
          <div className="mh">Tugaskan ke</div>
          {list.map(([id, a]) => (
            <button key={id} className={assignee===id?'sel':''} onClick={() => { onAssign(id); setOpen(false); }}>
              <span className="ava" style={{ background: a.color }}>{a.initials}</span>{a.name}{id==='me' && ' (saya)'}
              <span className="chk"><Ic.Check size={15}/></span>
            </button>
          ))}
          <button className={!assignee?'sel':''} onClick={() => { onAssign(null); setOpen(false); }}>
            <span className="ava na"><Ic.X size={12}/></span>Belum ditugaskan<span className="chk"><Ic.Check size={15}/></span>
          </button>
        </div>
      )}
    </div>
  );
}

/* ───────────── COMPOSER (two-mode + AI) ───────────── */
function Composer({ onSend, channelName, role, canned, onManageCanned, aiEnabled, onSuggest }) {
  const [val, setVal] = useS2('');
  const [mode, setMode] = useS2('reply');        // 'reply' | 'note'
  const [focus, setFocus] = useS2(false);
  const [showCanned, setShowCanned] = useS2(false);
  const [hl, setHl] = useS2(0);
  const [aiBusy, setAiBusy] = useS2(false);
  const [aiErr, setAiErr] = useS2(false);
  const [aiDraft, setAiDraft] = useS2(false);
  const ta = useR2(null);

  const filtered = (() => {
    if (!showCanned) return [];
    const q = val.startsWith('/') ? val.slice(1).toLowerCase() : '';
    return canned.filter(c => c.slug.includes(q) || c.title.toLowerCase().includes(q));
  })();

  function auto() { const el = ta.current; if (!el) return; el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 160) + 'px'; }
  useE2(auto, [val]);

  function onChange(e) { const v = e.target.value; setVal(v); setShowCanned(mode === 'reply' && v.startsWith('/')); setHl(0); setAiDraft(false); }
  function pick(c) { setVal(c.body); setShowCanned(false); requestAnimationFrame(() => { ta.current && ta.current.focus(); auto(); }); }
  function send() {
    const text = val.trim();
    if (!text || (mode === 'reply' && text.startsWith('/'))) return;
    onSend(text, mode);
    setVal(''); setShowCanned(false); setAiDraft(false);
    requestAnimationFrame(() => { if (ta.current) ta.current.style.height = 'auto'; });
  }
  function onKey(e) {
    if (showCanned && filtered.length) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setHl(h => (h+1)%filtered.length); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); setHl(h => (h-1+filtered.length)%filtered.length); return; }
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); pick(filtered[hl]); return; }
      if (e.key === 'Escape') { setShowCanned(false); return; }
    }
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  }
  function suggest() {
    setAiErr(false); setAiBusy(true);
    onSuggest().then(draft => {
      setAiBusy(false); setAiDraft(true); setVal(draft);
      requestAnimationFrame(() => { ta.current && ta.current.focus(); auto(); });
    }).catch(() => { setAiBusy(false); setAiErr(true); });
  }
  function switchMode(m) { setMode(m); setShowCanned(false); }

  const isNote = mode === 'note';
  return (
    <div className={'composer' + (isNote ? ' note-mode' : '')}>
      {showCanned && filtered.length > 0 && (
        <div className="canned">
          <div className="ch"><span>Balasan cepat</span><span>↑↓ pilih · Enter sisip · Esc tutup</span></div>
          <div className="canned-scroll">
            {filtered.map((c, i) => (
              <button key={c.slug} className={i===hl?'hl':''} onMouseEnter={() => setHl(i)} onClick={() => pick(c)}>
                <div><span className="slug">/{c.slug}</span><span className="ttl">{c.title}</span></div>
                <div className="bd">{c.body}</div>
              </button>
            ))}
          </div>
          {role === 'manager' && <button className="manage" onClick={onManageCanned}><Ic.Edit size={14}/>Kelola balasan cepat</button>}
        </div>
      )}

      <div className="composer-modes">
        <button className={'cmode' + (mode === 'reply' ? ' on-reply' : '')} onClick={() => switchMode('reply')}><Ic.Reply size={14}/>Balas</button>
        <button className={'cmode' + (mode === 'note' ? ' on-note' : '')} onClick={() => switchMode('note')}><Ic.Lock size={14}/>Catatan internal</button>
      </div>

      {isNote && <div className="note-flag"><Ic.Eye size={14}/><span>Mode catatan internal — pesan ini <b>tidak akan terkirim ke pelanggan</b>, hanya terlihat oleh agen.</span></div>}
      {aiErr && <div className="ai-fail"><Ic.AlertCircle size={14}/><span>Koneksi AI gagal — cek Settingan AI. Anda tetap bisa menulis manual.</span><button className="rt" onClick={suggest}>Coba lagi</button></div>}

      <div className={'composer-inner' + (focus ? ' focus' : '')}>
        <textarea ref={ta} rows={1} value={val}
          placeholder={isNote ? 'Tulis catatan internal untuk tim…' : `Balas via ${channelName}…  ketik / untuk balasan cepat`}
          onChange={onChange} onKeyDown={onKey} onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}/>
        <div className="composer-bar">
          <button className="tool" title="Lampirkan gambar"><Ic.Image size={18}/></button>
          <button className="tool" title="Lampirkan file"><Ic.Paperclip size={18}/></button>
          <button className="tool" title="Emoji"><Ic.Smile size={18}/></button>
          {!isNote && aiEnabled && (
            <button className="ai-btn" onClick={suggest} disabled={aiBusy} title="Sarankan balasan dengan AI">
              {aiBusy ? <><span className="spin"><Ic.Loader size={14}/></span>Menyusun…</> : <><Ic.Sparkles size={14}/>Sarankan balasan</>}
            </button>
          )}
          {aiDraft && !aiBusy && <span className="ai-draft-flag"><Ic.Sparkles size={12}/>Draft AI — edit dulu sebelum kirim</span>}
          <span className="spacer"/>
          <button className={'send-btn' + (isNote ? ' note' : '')} disabled={!val.trim() || (mode === 'reply' && val.startsWith('/'))} onClick={send}>
            {isNote ? <>Simpan catatan <Ic.Lock size={15}/></> : <>Kirim <Ic.Send size={16}/></>}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ───────────── THREAD ───────────── */
function Thread({ conv, loading, banner, onDismissBanner, onStatus, onAssign, onSend, onRetry, cpCollapsed, onToggleCp,
                  role, canned, onManageCanned, aiEnabled, onSuggest }) {
  const scrollRef = useR2(null);
  useE2(() => { const el = scrollRef.current; if (el) el.scrollTop = el.scrollHeight; }, [conv && conv.id, conv && conv.messages.length, loading]);

  if (!conv) {
    return (
      <section className="thread">
        <div className="empty">
          <svg className="art" viewBox="0 0 96 96" fill="none">
            <rect x="14" y="22" width="68" height="48" rx="8" stroke="currentColor" strokeWidth="3"/>
            <path d="M14 34h68" stroke="currentColor" strokeWidth="3"/>
            <circle cx="22" cy="28" r="2" fill="currentColor"/><circle cx="30" cy="28" r="2" fill="currentColor"/>
            <rect x="24" y="44" width="34" height="6" rx="3" fill="currentColor" opacity=".5"/>
            <rect x="24" y="56" width="22" height="6" rx="3" fill="currentColor" opacity=".3"/>
          </svg>
          <h3>Pilih percakapan</h3>
          <p>Pilih percakapan dari daftar di sebelah kiri untuk mulai membalas pelanggan Anda.</p>
        </div>
      </section>
    );
  }

  const ch = window.INBOX.CHANNELS[conv.channelId];
  return (
    <section className="thread">
      <div className="th-head">
        <div className="th-ava-wrap"><div className="th-ava" style={{ background: conv.contact.color }}>{conv.contact.initials}</div></div>
        <div className="th-id">
          <div className="nm">{conv.contact.name}</div>
          <div className="meta">
            <span className={'th-ch-tag ' + ch.type}><ChannelGlyph ch={ch.type} size={10}/>{ch.name}</span>
            <span>{conv.contact.handle}</span>
          </div>
        </div>
        <div className="th-actions">
          <StatusSeg status={conv.status} onChange={onStatus}/>
          <AssignMenu assignee={conv.assignee} onAssign={onAssign}/>
          {cpCollapsed && <button className="icon-btn" title="Buka panel kontak" onClick={onToggleCp}><Ic.PanelRight size={16}/></button>}
        </div>
      </div>

      {banner && (
        <div className="banner">
          <span className="bi"><Ic.PhoneOff size={16}/></span>
          <span><b>{ch.name} terputus.</b> Koneksi gateway (Wuzapi) terputus 3 menit lalu — pesan keluar akan tertahan sampai tersambung kembali.</span>
          <span className="act">
            <button className="reconnect"><Ic.RefreshCw size={12} style={{verticalAlign:-2,marginRight:4}}/>Sambungkan ulang</button>
            <button className="x" onClick={onDismissBanner} title="Tutup"><Ic.X size={15}/></button>
          </span>
        </div>
      )}

      {loading ? <ThreadSkeleton/> : (
        <div className="msgs" ref={scrollRef}>
          <div className="day-sep">Hari ini</div>
          {conv.messages.map(m => m.type === 'note' ? <NoteCard key={m.id} m={m}/> : <Bubble key={m.id} m={m} onRetry={onRetry}/>)}
        </div>
      )}

      <Composer onSend={onSend} channelName={ch.name} role={role} canned={canned} onManageCanned={onManageCanned} aiEnabled={aiEnabled} onSuggest={onSuggest}/>
    </section>
  );
}

Object.assign(window, { Thread, Composer, Bubble, NoteCard, DeliveryTick, StatusSeg, AssignMenu, ThreadSkeleton });
