import { useState, useRef, useEffect, type ReactNode } from "react";
import { Ic, ChannelGlyph } from "./icons";
import { tagClass } from "@/lib/format";
import type { AgentVM, ChannelVM, ConversationVM, UIStatus } from "@/types";

interface ConvItemProps {
  c: ConversationVM;
  channel: ChannelVM | undefined;
  assignee: AgentVM | undefined;
  selected: boolean;
  onClick: () => void;
  failed: boolean;
}

export function ConvItem({
  c,
  channel,
  assignee,
  selected,
  onClick,
  failed,
}: ConvItemProps) {
  return (
    <div
      className={"conv" + (selected ? " sel" : "") + (c.unread ? " unread" : "")}
      onClick={onClick}
    >
      <div className="conv-ava-wrap">
        <div className="conv-ava" style={{ background: c.contact.color }}>
          {c.contact.initials}
        </div>
        {channel && (
          <div className={"conv-ch " + channel.type}>
            <ChannelGlyph ch={channel.type} size={10} />
          </div>
        )}
      </div>
      <div className="conv-body">
        <div className="conv-r1">
          <span className="conv-name">{c.contact.name}</span>
          <span className="conv-time">{c.lastTime}</span>
        </div>
        <div className="conv-r2">
          <span className="conv-prev">
            {failed ? (
              <span className="conv-failed">
                <Ic.AlertCircle size={12} /> Gagal terkirim
              </span>
            ) : (
              c.preview
            )}
          </span>
          {c.unread > 0 && <span className="conv-badge">{c.unread}</span>}
        </div>
        <div className="conv-meta">
          {channel && (
            <span className={"conv-chlabel " + channel.type}>{channel.name}</span>
          )}
          {c.tags.map((tg) => (
            <span key={tg} className={"tag-chip " + tagClass(tg)}>
              {tg}
            </span>
          ))}
          {assignee && (
            <span
              className="conv-assignee"
              title={"Ditugaskan ke " + assignee.name}
              style={{ background: assignee.color }}
            >
              {assignee.initials}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export function ListSkeleton() {
  return (
    <div>
      {Array.from({ length: 7 }).map((_, i) => (
        <div className="sk-conv" key={i}>
          <div
            className="sk"
            style={{ width: 42, height: 42, borderRadius: 9999, flexShrink: 0 }}
          />
          <div className="c">
            <div className="sk" style={{ height: 12, width: `${55 + ((i * 7) % 30)}%` }} />
            <div className="sk" style={{ height: 10, width: "40%" }} />
            <div className="sk" style={{ height: 11, width: `${70 - ((i * 5) % 30)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function FilterMenu({
  label,
  icon,
  on,
  children,
  width,
}: {
  label: string;
  icon: ReactNode;
  on?: boolean;
  children: ReactNode;
  width?: number;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  return (
    <div style={{ position: "relative" }} ref={ref}>
      <button className={"lf-chip" + (on ? " on" : "")} onClick={() => setOpen((o) => !o)}>
        {icon}
        {label}
        <Ic.ChevronDown size={13} />
      </button>
      {open && (
        <div
          className="lf-menu"
          style={{ minWidth: width || 180 }}
          onClick={() => setOpen(false)}
        >
          {children}
        </div>
      )}
    </div>
  );
}

interface ConversationListProps {
  convs: ConversationVM[];
  channels: Record<string, ChannelVM>;
  agents: Record<string, AgentVM>;
  failedIds: Set<string>;
  selId: string | null;
  onSelect: (id: string) => void;
  search: string;
  setSearch: (s: string) => void;
  statusFilter: UIStatus;
  scope: "me" | "all";
  setScope: (s: "me" | "all") => void;
  loading: boolean;
  searchEmpty: boolean;
  filterAgent: string | null;
  setFilterAgent: (a: string | null) => void;
  unreplied: boolean;
  setUnreplied: (fn: (u: boolean) => boolean) => void;
  sortBy: "newest" | "oldest";
  setSortBy: (s: "newest" | "oldest") => void;
  myUserId: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export function ConversationList(props: ConversationListProps) {
  const {
    convs,
    channels,
    agents,
    failedIds,
    selId,
    onSelect,
    search,
    setSearch,
    statusFilter,
    scope,
    setScope,
    loading,
    searchEmpty,
    filterAgent,
    setFilterAgent,
    unreplied,
    setUnreplied,
    sortBy,
    setSortBy,
    myUserId,
    collapsed,
    onToggleCollapse,
  } = props;

  const title =
    statusFilter === "open" ? "Open" : statusFilter === "pending" ? "Pending" : "Resolved";

  const agentLabel = filterAgent
    ? filterAgent === myUserId
      ? "Saya"
      : (agents[filterAgent]?.name || filterAgent).split(" ")[0]
    : "Agen";

  return (
    <section className="list">
      <div className="list-head">
        <div className="row1">
          <h2>{title}</h2>
          <span className="sub">{loading ? "—" : convs.length} percakapan</span>
          <button
            className="list-ghost-btn"
            title={collapsed ? "Lebarkan daftar" : "Ciutkan daftar"}
            onClick={onToggleCollapse}
          >
            {collapsed ? <Ic.ChevronRight size={17} /> : <Ic.ChevronLeft size={17} />}
          </button>
        </div>
        <div className="list-search">
          <span className="si">
            <Ic.Search size={15} />
          </span>
          <input
            placeholder="Cari nama atau nomor kontak…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      <div className="list-tabs">
        <button className={scope === "me" ? "active" : ""} onClick={() => setScope("me")}>
          Ditugaskan ke saya
        </button>
        <button className={scope === "all" ? "active" : ""} onClick={() => setScope("all")}>
          Semua
        </button>
      </div>

      <div className="list-filters">
        <FilterMenu
          label={agentLabel}
          icon={<Ic.User size={13} />}
          on={!!filterAgent}
          width={220}
        >
          <div className="mh">Ditugaskan ke</div>
          <button className={!filterAgent ? "sel" : ""} onClick={() => setFilterAgent(null)}>
            Semua agen
          </button>
          {Object.values(agents).map((a) => (
            <button
              key={a.id}
              className={filterAgent === a.id ? "sel" : ""}
              onClick={() => setFilterAgent(a.id)}
            >
              <span className="ava" style={{ background: a.color }}>
                {a.initials}
              </span>
              {a.name}
              {a.id === myUserId ? " (saya)" : ""}
            </button>
          ))}
        </FilterMenu>

        <button
          className={"lf-chip" + (unreplied ? " on" : "")}
          onClick={() => setUnreplied((u) => !u)}
        >
          <Ic.Reply size={13} />
          Belum dibalas
        </button>

        <span className="lf-spacer" />

        <FilterMenu
          label={sortBy === "newest" ? "Terbaru" : "Terlama"}
          icon={<Ic.SlidersH size={13} />}
          width={150}
        >
          <div className="mh">Urutkan</div>
          <button className={sortBy === "newest" ? "sel" : ""} onClick={() => setSortBy("newest")}>
            Terbaru di atas
          </button>
          <button className={sortBy === "oldest" ? "sel" : ""} onClick={() => setSortBy("oldest")}>
            Terlama di atas
          </button>
        </FilterMenu>
      </div>

      <div className="list-scroll">
        {loading ? (
          <ListSkeleton />
        ) : searchEmpty ? (
          <div className="empty-list">
            <div className="ic search-ic">
              <Ic.Search size={38} />
            </div>
            <h4>Tidak ada percakapan cocok</h4>
            <p>
              Tidak ada hasil untuk "<strong>{search}</strong>". Coba kata kunci lain atau ubah
              filter.
            </p>
          </div>
        ) : convs.length === 0 ? (
          <div className="empty-list">
            <div className="ic">
              <Ic.Inbox size={40} />
            </div>
            <h4>Belum ada percakapan</h4>
            <p>
              Tidak ada percakapan {statusFilter} di sini. Percakapan baru akan muncul otomatis
              saat pelanggan mengirim pesan.
            </p>
          </div>
        ) : (
          convs.map((c) => (
            <ConvItem
              key={c.id}
              c={c}
              channel={channels[c.channelId]}
              assignee={c.assignee ? agents[c.assignee] : undefined}
              selected={c.id === selId}
              onClick={() => onSelect(c.id)}
              failed={failedIds.has(c.id)}
            />
          ))
        )}
      </div>
    </section>
  );
}
