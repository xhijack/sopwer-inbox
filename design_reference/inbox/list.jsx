/* Sopwer Inbox — conversation list pane + advanced filter/sort header */
const { useState: useLS, useRef: useLR, useEffect: useLE } = React;

function FilterMenu({ label, icon, on, children, width }) {
  const [open, setOpen] = useLS(false);
  const ref = useLR(null);
  useLE(() => {
    const h = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h);
  }, []);
  return (
    <div style={{ position: 'relative' }} ref={ref}>
      <button className={'lf-chip' + (on ? ' on' : '')} onClick={() => setOpen(o => !o)}>
        {icon}{label}<Ic.ChevronDown size={13}/>
      </button>
      {open && <div className="lf-menu" style={{ minWidth: width || 180 }} onClick={() => setOpen(false)}>{children}</div>}
    </div>
  );
}

function ConversationList({ convs, selId, onSelect, search, setSearch, statusFilter, scope, setScope,
                            loading, searchEmpty, filterAgent, setFilterAgent, unreplied, setUnreplied, sortBy, setSortBy }) {
  const A = window.INBOX.AGENTS;
  const title = statusFilter === 'open' ? 'Open' : statusFilter === 'pending' ? 'Pending' : 'Resolved';
  return (
    <section className="list">
      <div className="list-head">
        <div className="row1">
          <h2>{title}</h2>
          <span className="sub">{loading ? '—' : convs.length} percakapan</span>
        </div>
        <div className="list-search">
          <span className="si"><Ic.Search size={15}/></span>
          <input placeholder="Cari nama atau nomor kontak…" value={search} onChange={e => setSearch(e.target.value)}/>
        </div>
      </div>
      <div className="list-tabs">
        <button className={scope === 'me' ? 'active' : ''} onClick={() => setScope('me')}>Ditugaskan ke saya</button>
        <button className={scope === 'all' ? 'active' : ''} onClick={() => setScope('all')}>Semua</button>
      </div>

      <div className="list-filters">
        <FilterMenu label={filterAgent ? (filterAgent === 'me' ? 'Saya' : A[filterAgent].name.split(' ')[0]) : 'Agen'}
          icon={<Ic.User size={13}/>} on={!!filterAgent} width={200}>
          <div className="mh">Ditugaskan ke</div>
          <button className={!filterAgent ? 'sel' : ''} onClick={() => setFilterAgent(null)}>Semua agen</button>
          {Object.values(A).map(a => (
            <button key={a.id} className={filterAgent === a.id ? 'sel' : ''} onClick={() => setFilterAgent(a.id)}>
              <span className="ava" style={{ background: a.color }}>{a.initials}</span>{a.name}{a.id === 'me' ? ' (saya)' : ''}
            </button>
          ))}
        </FilterMenu>

        <button className={'lf-chip' + (unreplied ? ' on' : '')} onClick={() => setUnreplied(u => !u)}>
          <Ic.Reply size={13}/>Belum dibalas
        </button>

        <span className="lf-spacer"/>

        <FilterMenu label={sortBy === 'newest' ? 'Terbaru' : 'Terlama'} icon={<Ic.SlidersH size={13}/>} width={150}>
          <div className="mh">Urutkan</div>
          <button className={sortBy === 'newest' ? 'sel' : ''} onClick={() => setSortBy('newest')}>Terbaru di atas</button>
          <button className={sortBy === 'oldest' ? 'sel' : ''} onClick={() => setSortBy('oldest')}>Terlama di atas</button>
        </FilterMenu>
      </div>

      <div className="list-scroll">
        {loading ? <ListSkeleton/> :
          searchEmpty ? (
            <div className="empty-list">
              <div className="ic search-ic"><Ic.Search size={38}/></div>
              <h4>Tidak ada percakapan cocok</h4>
              <p>Tidak ada hasil untuk "<strong>{search}</strong>". Coba kata kunci lain atau ubah filter.</p>
            </div>
          ) : convs.length === 0 ? (
            <div className="empty-list">
              <div className="ic"><Ic.Inbox size={40}/></div>
              <h4>Belum ada percakapan</h4>
              <p>Tidak ada percakapan {statusFilter} di sini. Percakapan baru akan muncul otomatis saat pelanggan mengirim pesan.</p>
            </div>
          ) : convs.map(c => (
            <ConvItem key={c.id} c={c} selected={c.id === selId} onClick={() => onSelect(c.id)}/>
          ))
        }
      </div>
    </section>
  );
}

window.ConversationList = ConversationList;
