/* Sopwer Inbox — sidebar, conversation list, contact panel (v2) */
const { useState, useRef, useEffect, useMemo } = React;
const Ic = window.Ic;
const { AGENTS, CHANNELS } = window.INBOX;

const ChannelGlyph = ({ ch, size }) => ch === 'wa' ? <Ic.WaGlyph size={size}/> : <Ic.TgGlyph size={size}/>;
const tagClass = (t) => { const s = t.toLowerCase(); if (s === 'vip') return 'vip'; if (s === 'komplain') return 'komplain'; return ''; };

function lastPreview(c) {
  const visible = c.messages.filter(m => m.type !== 'note');
  const m = visible[visible.length - 1];
  if (!m) return { text: '' };
  const prefix = m.dir === 'out' ? 'Anda: ' : '';
  if (m.type === 'image') return { prefix, icon: 'image', text: m.caption || 'Foto' };
  if (m.type === 'video') return { prefix, icon: 'video', text: m.caption || 'Video' };
  if (m.type === 'file') return { prefix, icon: 'file', text: m.media.name };
  if (m.type === 'audio') return { prefix, icon: 'audio', text: 'Pesan suara' };
  if (m.type === 'location') return { prefix, icon: 'loc', text: 'Lokasi' };
  return { prefix, text: m.text };
}

/* ───────────── SIDEBAR ───────────── */
function Sidebar({ counts, filter, setFilter, scope, setScope, channelSel, toggleChannel, clearChannels,
                   role, onOpenCanned, onOpenAI, agentStatus, setAgentStatus }) {
  const [statusOpen, setStatusOpen] = useState(false);
  const sref = useRef(null);
  useEffect(() => {
    const h = e => { if (sref.current && !sref.current.contains(e.target)) setStatusOpen(false); };
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h);
  }, []);
  const StatusItem = ({ id, label }) => (
    <button className={'sb-item' + (filter === id ? ' active' : '')} onClick={() => setFilter(id)}>
      <span className="chdot" style={{ background: `var(--st-${id})` }}/>
      <span className="lbl">{label}</span>
      <span className="cnt">{counts[id] ?? 0}</span>
    </button>
  );
  const allCh = channelSel.length === 0;
  return (
    <aside className="sidebar">
      <div className="sb-logo">
        <img src={(window.__resources && window.__resources.logo) || "inbox/assets/sopwer-logo-full.png"} alt="Sopwer"/>
        <span className="tag">INBOX</span>
      </div>
      <div className="sb-scroll">
        <div className="sb-sec">Status</div>
        <StatusItem id="open" label="Open"/>
        <StatusItem id="pending" label="Pending"/>
        <StatusItem id="resolved" label="Resolved"/>

        <div className="sb-sec">Tampilan</div>
        <button className={'sb-item' + (scope === 'me' ? ' active' : '')} onClick={() => setScope('me')}>
          <span className="ic"><Ic.UserCheck size={17}/></span><span className="lbl">Ditugaskan ke saya</span>
          <span className="cnt">{counts.mine}</span>
        </button>
        <button className={'sb-item' + (scope === 'all' ? ' active' : '')} onClick={() => setScope('all')}>
          <span className="ic"><Ic.Users size={17}/></span><span className="lbl">Semua percakapan</span>
          <span className="cnt">{counts.all}</span>
        </button>

        <div className="sb-sec">Kanal</div>
        <button className={'sb-item' + (allCh ? ' active' : '')} onClick={clearChannels}>
          <span className="ic"><Ic.Inbox size={17}/></span><span className="lbl">Semua kanal</span>
        </button>
        {Object.values(CHANNELS).map(ch => {
          const on = channelSel.includes(ch.id);
          return (
            <button key={ch.id} className={'sb-item' + (on ? ' on' : '')} onClick={() => toggleChannel(ch.id)} title={ch.addr}>
              <span className="check">{on && <Ic.Check size={11}/>}</span>
              <span className={'chtype ' + ch.type}><ChannelGlyph ch={ch.type} size={10}/></span>
              <span className="lbl">{ch.name}</span>
              <span className="cnt">{counts.byChannel[ch.id] || 0}</span>
            </button>
          );
        })}

        {role === 'manager' && (
          <>
            <div className="sb-sec">Manager <span className="pin">● khusus</span></div>
            <button className="sb-item mgr" onClick={onOpenCanned}>
              <span className="ic"><Ic.MessageSquare size={17}/></span><span className="lbl">Kelola Balasan Cepat</span>
            </button>
            <button className="sb-item mgr" onClick={onOpenAI}>
              <span className="ic"><Ic.Sparkles size={17}/></span><span className="lbl">Settingan AI</span>
            </button>
          </>
        )}
      </div>

      <div className="sb-foot" style={{ position: 'relative' }} ref={sref}>
        <div className="status-toggle" onClick={() => setStatusOpen(o => !o)}>
          <div className="ava">AN</div>
          <span className={'pres' + (agentStatus === 'away' ? ' away' : '')}/>
        </div>
        <div className="info" style={{ cursor: 'pointer' }} onClick={() => setStatusOpen(o => !o)}>
          <div className="nm">Andi Nugroho</div>
          <div className="role">{role === 'manager' ? 'Inbox Manager' : 'Agen CS'} · {agentStatus === 'away' ? 'Away' : 'Available'}</div>
        </div>
        <Ic.ChevronUp size={15} style={{ color: 'var(--sw-ink-400)', cursor: 'pointer' }} onClick={() => setStatusOpen(o => !o)}/>
        {statusOpen && (
          <div className="status-pop">
            <button onClick={() => { setAgentStatus('available'); setStatusOpen(false); }}>
              <span className="d" style={{ background: 'var(--sw-green-400)' }}/>Available <span style={{ marginLeft: 'auto', color: 'var(--fg-4)', fontSize: 11 }}>{agentStatus === 'available' ? '✓' : ''}</span>
            </button>
            <button onClick={() => { setAgentStatus('away'); setStatusOpen(false); }}>
              <span className="d" style={{ background: 'var(--sw-yellow-400)' }}/>Away <span style={{ marginLeft: 'auto', color: 'var(--fg-4)', fontSize: 11 }}>{agentStatus === 'away' ? '✓' : ''}</span>
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

/* ───────────── CONVERSATION LIST ITEM ───────────── */
function ConvItem({ c, selected, onClick }) {
  const prev = lastPreview(c);
  const assignee = c.assignee ? AGENTS[c.assignee] : null;
  const ch = CHANNELS[c.channelId];
  const lastOut = [...c.messages].reverse().find(m => m.dir === 'out' && m.type !== 'note');
  const showFailed = lastOut && lastOut.status === 'failed';
  return (
    <div className={'conv' + (selected ? ' sel' : '') + (c.unread ? ' unread' : '')} onClick={onClick}>
      <div className="conv-ava-wrap">
        <div className="conv-ava" style={{ background: c.contact.color }}>{c.contact.initials}</div>
        <div className={'conv-ch ' + ch.type}><ChannelGlyph ch={ch.type} size={10}/></div>
      </div>
      <div className="conv-body">
        <div className="conv-r1">
          <span className="conv-name">{c.contact.name}</span>
          <span className="conv-time">{c.lastTime}</span>
        </div>
        <div className="conv-r1b">
          <span className={'conv-chlabel ' + ch.type}><span className="g"><ChannelGlyph ch={ch.type} size={9}/></span>{ch.name}</span>
          <span className="conv-handle" style={{ margin: 0 }}>{c.contact.handle}</span>
        </div>
        <div className="conv-r2">
          <span className="conv-prev">
            {showFailed ? <span className="conv-failed"><Ic.AlertCircle size={12}/> Gagal terkirim</span> : <>
              {prev.prefix && <span className="me">{prev.prefix}</span>}
              {prev.icon === 'image' && <span className="att"><Ic.Image size={12}/></span>}
              {prev.icon === 'video' && <span className="att"><Ic.Video size={12}/></span>}
              {prev.icon === 'file' && <span className="att"><Ic.File size={12}/></span>}
              {prev.icon === 'audio' && <span className="att"><Ic.Mic size={12}/></span>}
              {prev.icon === 'loc' && <span className="att"><Ic.MapPin size={12}/></span>}
              {' '}{prev.text}
            </>}
          </span>
          {c.unread > 0 && <span className="conv-badge">{c.unread}</span>}
        </div>
        <div className="conv-meta">
          <span className={'st-dot ' + c.status}/>
          <span className="conv-st-lbl">{c.status}</span>
          {assignee && <span className="conv-assignee" title={'Ditugaskan ke ' + assignee.name} style={{ background: assignee.color }}>{assignee.initials}</span>}
        </div>
        {c.tags && c.tags.length > 0 && (
          <div className="conv-tags">
            {c.tags.map(tg => <span key={tg} className={'tag-chip ' + tagClass(tg)}>{tg}</span>)}
          </div>
        )}
      </div>
    </div>
  );
}

function ListSkeleton() {
  return (
    <div>
      {Array.from({ length: 7 }).map((_, i) => (
        <div className="sk-conv" key={i}>
          <div className="sk" style={{ width: 42, height: 42, borderRadius: 9999, flexShrink: 0 }}/>
          <div className="c">
            <div className="sk" style={{ height: 12, width: `${55 + (i*7)%30}%` }}/>
            <div className="sk" style={{ height: 10, width: '40%' }}/>
            <div className="sk" style={{ height: 11, width: `${70 - (i*5)%30}%` }}/>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ───────────── CONTACT PANEL ───────────── */
function ContactPanel({ conv, allConvs, showErp, onClose, onRename, onAddTag, onRemoveTag, onNote }) {
  const [editingName, setEditingName] = useState(false);
  const [nameVal, setNameVal] = useState('');
  const [addingTag, setAddingTag] = useState(false);
  const [tagVal, setTagVal] = useState('');
  if (!conv) return null;
  const ct = conv.contact;
  const ch = CHANNELS[conv.channelId];
  const history = allConvs.filter(c => c.contact.name === ct.name);

  function commitName() { if (nameVal.trim()) onRename(nameVal.trim()); setEditingName(false); }
  function commitTag() { const v = tagVal.trim(); if (v) onAddTag(v); setTagVal(''); setAddingTag(false); }

  return (
    <aside className="cpanel">
      <div className="cp-head">
        <h3>Detail Kontak</h3>
        <button className="icon-btn" onClick={onClose} title="Tutup panel" style={{ width: 28, height: 28 }}><Ic.PanelRight size={15}/></button>
      </div>
      <div className="cp-scroll">
        <div className="cp-id">
          <div className="ava-wrap">
            <div className="ava" style={{ background: ct.color }}>{ct.initials}</div>
            <div className={'ch ' + ch.type}><ChannelGlyph ch={ch.type} size={13}/></div>
          </div>
          {editingName ? (
            <input className="cp-name-edit" autoFocus value={nameVal} onChange={e => setNameVal(e.target.value)}
              onBlur={commitName} onKeyDown={e => { if (e.key === 'Enter') commitName(); if (e.key === 'Escape') setEditingName(false); }}
              style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 700 }}/>
          ) : (
            <div className="cp-name-edit">
              <span className="nm">{ct.name}</span>
              <span className="pen" title="Edit nama" onClick={() => { setNameVal(ct.name); setEditingName(true); }}><Ic.Edit size={13}/></span>
            </div>
          )}
          <div className="handle">{ct.handle}</div>
          <span className={'chrow ' + ch.type}><ChannelGlyph ch={ch.type} size={11}/>{ch.name}</span>
        </div>

        <div className="cp-sec">
          <div className="lbl">Tag percakapan</div>
          <div className="cp-tags">
            {(conv.tags || []).map(tg => (
              <span key={tg} className={'cp-tag ' + tagClass(tg)}>{tg}
                <span className="x" title="Hapus tag" onClick={() => onRemoveTag(tg)}><Ic.X size={11}/></span>
              </span>
            ))}
            {addingTag ? (
              <input className="cp-tag-input" autoFocus value={tagVal} placeholder="nama tag…" onChange={e => setTagVal(e.target.value)}
                onBlur={commitTag} onKeyDown={e => { if (e.key === 'Enter') commitTag(); if (e.key === 'Escape') { setTagVal(''); setAddingTag(false); } }}/>
            ) : (
              <button className="cp-tag-add" onClick={() => setAddingTag(true)}><Ic.Plus size={12}/>Tag</button>
            )}
          </div>
        </div>

        <div className="cp-sec">
          <div className="lbl">Catatan tentang kontak</div>
          <textarea className="cp-note" rows={3} value={conv.note || ''} placeholder="Catatan lengket — muncul tiap kontak ini chat. Mis. preferensi, riwayat penting…"
            onChange={e => onNote(e.target.value)}/>
        </div>

        <div className="cp-sec">
          <div className="lbl">Informasi</div>
          <div className="cp-attr"><span className="k">Kanal</span><span className="v">{ch.name}</span></div>
          <div className="cp-attr"><span className="k">Status</span><span className="v" style={{ textTransform: 'capitalize' }}>{conv.status}</span></div>
          <div className="cp-attr"><span className="k">Pelanggan sejak</span><span className="v">Mei 2024</span></div>
          <div className="cp-attr"><span className="k">Total chat</span><span className="v">{history.length}</span></div>
        </div>

        {showErp && conv.orders && conv.orders.length > 0 && (
          <div className="cp-sec">
            <div className="lbl"><span>Dari ERPNext</span><span style={{ color: 'var(--sw-green-600)', textTransform: 'none', letterSpacing: 0 }}>● Terhubung</span></div>
            {conv.orders.map(o => (
              <div className="erp-card" key={o.no}>
                <div className="eh">
                  <span className="no">{o.no}</span>
                  <span className="lbl" style={{ marginLeft: 'auto', marginBottom: 0, letterSpacing: 0, textTransform: 'none' }}>{o.label}</span>
                </div>
                <div className="eb">
                  <div><div className="amt">{o.amount}</div><div className="dt">{o.date}</div></div>
                  <span className={'pill ' + o.status}><span className="dot"/>{o.status === 'paid' ? 'Lunas' : 'Menunggu'}</span>
                </div>
              </div>
            ))}
            <a className="erp-link" href="#" onClick={e => e.preventDefault()}>Lihat di ERPNext <Ic.ChevronRight size={13}/></a>
          </div>
        )}

        <div className="cp-sec">
          <div className="lbl">Percakapan sebelumnya</div>
          {history.length <= 1 && <div style={{ fontSize: 12, color: 'var(--fg-3)', lineHeight: 1.5 }}>Belum ada percakapan lain dengan kontak ini.</div>}
          {history.map(h => (
            <div className="cp-prev-item" key={h.id}>
              <span className="dot" style={{ background: `var(--st-${h.status})` }}/>
              <div className="t">
                <div className="s">{(lastPreview(h).text || '').slice(0, 38)}</div>
                <div className="d">{CHANNELS[h.channelId].name} · {h.lastTime}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

Object.assign(window, { Sidebar, ConversationList: null, ContactPanel, ChannelGlyph, lastPreview, ListSkeleton, tagClass });
