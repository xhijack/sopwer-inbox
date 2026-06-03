import { useState, useRef, useEffect } from "react";
import { Ic, ChannelGlyph } from "./icons";
import logoUrl from "@/assets/sopwer-logo-full.png";
import type { ChannelVM, UIStatus } from "@/types";
import type { Role } from "@/hooks/useSession";

export interface SidebarCounts {
  open: number;
  pending: number;
  resolved: number;
  mine: number;
  all: number;
  byChannel: Record<string, number>;
}

interface SidebarProps {
  counts: SidebarCounts;
  filter: UIStatus;
  setFilter: (s: UIStatus) => void;
  scope: "me" | "all";
  setScope: (s: "me" | "all") => void;
  channels: ChannelVM[];
  channelSel: string[];
  toggleChannel: (id: string) => void;
  clearChannels: () => void;
  role: Role;
  onOpenCanned: () => void;
  onOpenAI: () => void;
  agentStatus: "available" | "away";
  setAgentStatus: (s: "available" | "away") => void;
  fullName: string;
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({
  counts,
  filter,
  setFilter,
  scope,
  setScope,
  channels,
  channelSel,
  toggleChannel,
  clearChannels,
  role,
  onOpenCanned,
  onOpenAI,
  agentStatus,
  setAgentStatus,
  fullName,
  collapsed,
  onToggle,
}: SidebarProps) {
  const [statusOpen, setStatusOpen] = useState(false);
  const sref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (sref.current && !sref.current.contains(e.target as Node)) setStatusOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const StatusItem = ({ id, label }: { id: UIStatus; label: string }) => (
    <button
      className={"sb-item" + (filter === id ? " active" : "")}
      onClick={() => setFilter(id)}
    >
      <span className="chdot" style={{ background: `var(--st-${id})` }} />
      <span className="lbl">{label}</span>
      <span className="cnt">{counts[id] ?? 0}</span>
    </button>
  );

  const allCh = channelSel.length === 0;
  const fnInitials = fullName
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  return (
    <aside className="sidebar">
      <div className="sb-logo">
        <img src={logoUrl} alt="Sopwer" />
        <span className="tag">INBOX</span>
        <button
          className="sb-collapse-btn"
          title={collapsed ? "Lebarkan panel" : "Ciutkan panel"}
          onClick={onToggle}
        >
          {collapsed ? <Ic.PanelLeft size={17} /> : <Ic.PanelLeftClose size={16} />}
        </button>
      </div>
      <div className="sb-scroll">
        <div className="sb-sec">Status</div>
        <StatusItem id="open" label="Open" />
        <StatusItem id="pending" label="Pending" />
        <StatusItem id="resolved" label="Resolved" />

        <div className="sb-sec">Tampilan</div>
        <button
          className={"sb-item" + (scope === "me" ? " active" : "")}
          onClick={() => setScope("me")}
        >
          <span className="ic">
            <Ic.UserCheck size={17} />
          </span>
          <span className="lbl">Ditugaskan ke saya</span>
          <span className="cnt">{counts.mine}</span>
        </button>
        <button
          className={"sb-item" + (scope === "all" ? " active" : "")}
          onClick={() => setScope("all")}
        >
          <span className="ic">
            <Ic.Users size={17} />
          </span>
          <span className="lbl">Semua percakapan</span>
          <span className="cnt">{counts.all}</span>
        </button>

        <div className="sb-sec">Kanal</div>
        <button
          className={"sb-item" + (allCh ? " active" : "")}
          onClick={clearChannels}
        >
          <span className="ic">
            <Ic.Inbox size={17} />
          </span>
          <span className="lbl">Semua kanal</span>
        </button>
        {channels.map((ch) => {
          const on = channelSel.includes(ch.id);
          return (
            <button
              key={ch.id}
              className={"sb-item" + (on ? " on" : "")}
              onClick={() => toggleChannel(ch.id)}
              title={ch.addr}
            >
              <span className="check">{on && <Ic.Check size={11} />}</span>
              <span className={"chtype " + ch.type}>
                <ChannelGlyph ch={ch.type} size={10} />
              </span>
              <span className="lbl">{ch.name}</span>
              <span className="cnt">{counts.byChannel[ch.id] || 0}</span>
            </button>
          );
        })}

        {role === "manager" && (
          <>
            <div className="sb-sec">
              Manager <span className="pin">● khusus</span>
            </div>
            <button className="sb-item mgr" onClick={onOpenCanned}>
              <span className="ic">
                <Ic.MessageSquare size={17} />
              </span>
              <span className="lbl">Kelola Balasan Cepat</span>
            </button>
            <button className="sb-item mgr" onClick={onOpenAI}>
              <span className="ic">
                <Ic.Sparkles size={17} />
              </span>
              <span className="lbl">Settingan AI</span>
            </button>
          </>
        )}
      </div>

      <div className="sb-foot" style={{ position: "relative" }} ref={sref}>
        <div className="status-toggle" onClick={() => setStatusOpen((o) => !o)}>
          <div className="ava">{fnInitials || "?"}</div>
          <span className={"pres" + (agentStatus === "away" ? " away" : "")} />
        </div>
        <div
          className="info"
          style={{ cursor: "pointer" }}
          onClick={() => setStatusOpen((o) => !o)}
        >
          <div className="nm">{fullName}</div>
          <div className="role">
            {role === "manager" ? "Inbox Manager" : "Agen CS"} ·{" "}
            {agentStatus === "away" ? "Away" : "Available"}
          </div>
        </div>
        <span style={{ color: "var(--sw-ink-400)", cursor: "pointer", display: "flex" }}>
          <Ic.ChevronUp size={15} onClick={() => setStatusOpen((o) => !o)} />
        </span>
        {statusOpen && (
          <div className="status-pop">
            <button
              onClick={() => {
                setAgentStatus("available");
                setStatusOpen(false);
              }}
            >
              <span className="d" style={{ background: "var(--sw-green-400)" }} />
              Available
              <span style={{ marginLeft: "auto", color: "var(--fg-4)", fontSize: 11 }}>
                {agentStatus === "available" ? "✓" : ""}
              </span>
            </button>
            <button
              onClick={() => {
                setAgentStatus("away");
                setStatusOpen(false);
              }}
            >
              <span className="d" style={{ background: "var(--sw-yellow-400)" }} />
              Away
              <span style={{ marginLeft: "auto", color: "var(--fg-4)", fontSize: 11 }}>
                {agentStatus === "away" ? "✓" : ""}
              </span>
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
