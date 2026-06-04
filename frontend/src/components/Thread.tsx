import { useState, useRef, useEffect, useLayoutEffect } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";
import { Ic, ChannelGlyph } from "./icons";
import { playOutgoing } from "@/lib/sound";
import { Bubble, NoteCard, ThreadSkeleton } from "./Bubbles";
import { Composer, type ComposerMode, type OutgoingMedia } from "./Composer";
import { DocumentPicker } from "./DocumentPicker";
import { toApiStatus } from "@/lib/format";
import type {
  AgentVM,
  ChannelVM,
  ConversationVM,
  InboxCannedResponse,
  MessageVM,
  UIStatus,
  ConvStatus,
} from "@/types";
import type { Role } from "@/hooks/useSession";
import type { useInboxApi } from "@/hooks/useInboxApi";

function StatusSeg({
  status,
  onChange,
}: {
  status: UIStatus;
  onChange: (s: ConvStatus) => void;
}) {
  const opts: [UIStatus, string][] = [
    ["open", "Open"],
    ["pending", "Pending"],
    ["resolved", "Resolved"],
  ];
  return (
    <div className="seg">
      {opts.map(([id, label]) => (
        <button
          key={id}
          className={status === id ? "on " + id : ""}
          onClick={() => onChange(toApiStatus(id))}
        >
          {status === id &&
            (id === "resolved" ? (
              <Ic.CheckCircle size={13} />
            ) : (
              <span className="st-dot" style={{ background: "currentColor" }} />
            ))}
          {label}
        </button>
      ))}
    </div>
  );
}

function AssignMenu({
  assignee,
  agents,
  myUserId,
  onAssign,
}: {
  assignee: string | null;
  agents: Record<string, AgentVM>;
  myUserId: string;
  onAssign: (id: string | null) => void;
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
  const cur = assignee ? agents[assignee] : null;
  const list = Object.values(agents);
  return (
    <div className="menu-wrap" ref={ref}>
      <button className="assign-btn" onClick={() => setOpen((o) => !o)}>
        {cur ? (
          <span className="ava" style={{ background: cur.color }}>
            {cur.initials}
          </span>
        ) : (
          <span className="ava na">
            <Ic.User size={12} />
          </span>
        )}
        <span>{cur ? (assignee === myUserId ? "Saya" : cur.name.split(" ")[0]) : "Tugaskan"}</span>
        <Ic.ChevronDown size={14} style={{ color: "var(--fg-3)" }} />
      </button>
      {open && (
        <div className="menu">
          <div className="mh">Tugaskan ke</div>
          {list.map((a) => (
            <button
              key={a.id}
              className={assignee === a.id ? "sel" : ""}
              onClick={() => {
                onAssign(a.id);
                setOpen(false);
              }}
            >
              <span className="ava" style={{ background: a.color }}>
                {a.initials}
              </span>
              {a.name}
              {a.id === myUserId && " (saya)"}
              <span className="chk">
                <Ic.Check size={15} />
              </span>
            </button>
          ))}
          <button
            className={!assignee ? "sel" : ""}
            onClick={() => {
              onAssign(null);
              setOpen(false);
            }}
          >
            <span className="ava na">
              <Ic.X size={12} />
            </span>
            Belum ditugaskan
            <span className="chk">
              <Ic.Check size={15} />
            </span>
          </button>
        </div>
      )}
    </div>
  );
}

interface ThreadProps {
  conv: ConversationVM | null;
  messages: MessageVM[];
  agents: Record<string, AgentVM>;
  channels: Record<string, ChannelVM>;
  myUserId: string;
  loading: boolean;
  banner: boolean;
  onDismissBanner: () => void;
  onReconnect: () => void;
  onStatus: (s: ConvStatus) => void;
  onAssign: (a: string | null) => void;
  onSend: (text: string, mode: ComposerMode, media?: OutgoingMedia) => void;
  onRetry: (id: string) => void;
  cpCollapsed: boolean;
  onToggleCp: () => void;
  role: Role;
  canned: InboxCannedResponse[];
  onManageCanned: () => void;
  aiEnabled: boolean;
  onSuggest: () => Promise<string>;
  api: ReturnType<typeof useInboxApi>;
  mutateMessages: () => void;
}

export function Thread(props: ThreadProps) {
  const {
    conv,
    messages,
    agents,
    channels,
    myUserId,
    loading,
    banner,
    onDismissBanner,
    onReconnect,
    onStatus,
    onAssign,
    onSend,
    onRetry,
    cpCollapsed,
    onToggleCp,
    role,
    canned,
    onManageCanned,
    aiEnabled,
    onSuggest,
    api,
    mutateMessages,
  } = props;

  const [pickerOpen, setPickerOpen] = useState(false);
  const [docSending, setDocSending] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);

  const { data: sendCfg } = useFrappeGetCall<{ message: { enabled: boolean; doctypes: string[] } }>(
    "sopwer_inbox.api.document.get_send_config",
  );
  const docEnabled = !!(sendCfg?.message?.enabled && sendCfg.message.doctypes.length);
  const docDoctypes = sendCfg?.message?.doctypes || [];

  async function handleDocSend(doctype: string, name: string) {
    if (!conv) return;
    setDocError(null);
    setDocSending(true);
    try {
      await api.sendDocument(conv.id, doctype, name);
      playOutgoing();
      await mutateMessages();
      setPickerOpen(false);
    } catch (e: unknown) {
      // Surface the real backend error instead of silently closing the picker.
      setDocError(e instanceof Error ? e.message : "Gagal mengirim dokumen.");
    } finally {
      setDocSending(false);
    }
  }

  const scrollRef = useRef<HTMLDivElement>(null);
  // Track whether the agent is pinned near the bottom; only auto-scroll then.
  const atBottomRef = useRef(true);
  const prevConvRef = useRef<string | null>(null);

  function onScroll() {
    const el = scrollRef.current;
    if (!el) return;
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const convChanged = prevConvRef.current !== (conv ? conv.id : null);
    // Always scroll to bottom on conversation switch; otherwise only if pinned.
    if (convChanged || atBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
    prevConvRef.current = conv ? conv.id : null;
  }, [conv?.id, messages.length, loading]);

  if (!conv) {
    return (
      <section className="thread">
        <div className="empty">
          <svg className="art" viewBox="0 0 96 96" fill="none">
            <rect x="14" y="22" width="68" height="48" rx="8" stroke="currentColor" strokeWidth="3" />
            <path d="M14 34h68" stroke="currentColor" strokeWidth="3" />
            <circle cx="22" cy="28" r="2" fill="currentColor" />
            <circle cx="30" cy="28" r="2" fill="currentColor" />
            <rect x="24" y="44" width="34" height="6" rx="3" fill="currentColor" opacity=".5" />
            <rect x="24" y="56" width="22" height="6" rx="3" fill="currentColor" opacity=".3" />
          </svg>
          <h3>Pilih percakapan</h3>
          <p>Pilih percakapan dari daftar di sebelah kiri untuk mulai membalas pelanggan Anda.</p>
        </div>
      </section>
    );
  }

  const ch = channels[conv.channelId];

  return (
    <section className="thread">
      <div className="th-head">
        <div className="th-ava-wrap">
          <div className="th-ava" style={{ background: conv.contact.color }}>
            {conv.contact.initials}
          </div>
        </div>
        <div className="th-id">
          <div className="nm">{conv.contact.name}</div>
          <div className="meta">
            {ch && (
              <span className={"th-ch-tag " + ch.type}>
                <ChannelGlyph ch={ch.type} size={10} />
                {ch.name}
              </span>
            )}
          </div>
        </div>
        <div className="th-actions">
          <StatusSeg status={conv.status} onChange={onStatus} />
          <AssignMenu
            assignee={conv.assignee}
            agents={agents}
            myUserId={myUserId}
            onAssign={onAssign}
          />
          {cpCollapsed && (
            <button className="icon-btn" title="Buka panel kontak" onClick={onToggleCp}>
              <Ic.PanelRight size={16} />
            </button>
          )}
        </div>
      </div>

      {banner && (
        <div className="banner">
          <span className="bi">
            <Ic.PhoneOff size={16} />
          </span>
          <span>
            <b>{ch ? ch.name : "Kanal"} terputus.</b> Koneksi gateway terputus — pesan keluar akan
            tertahan sampai tersambung kembali.
          </span>
          <span className="act">
            <button className="reconnect" onClick={onReconnect}>
              <Ic.RefreshCw size={12} style={{ verticalAlign: -2, marginRight: 4 }} />
              Sambungkan ulang
            </button>
            <button className="x" onClick={onDismissBanner} title="Tutup">
              <Ic.X size={15} />
            </button>
          </span>
        </div>
      )}

      {loading ? (
        <ThreadSkeleton />
      ) : (
        <div className="msgs" ref={scrollRef} onScroll={onScroll}>
          {messages.length === 0 ? (
            <div className="empty" style={{ flex: 1 }}>
              <h3>Belum ada pesan</h3>
              <p>Mulai percakapan dengan mengirim balasan di bawah.</p>
            </div>
          ) : (
            <>
              <div className="day-sep">Riwayat</div>
              {messages.map((m) =>
                m.type === "note" ? (
                  <NoteCard key={m.id} m={m} agent={m.agent ? agents[m.agent] : undefined} />
                ) : (
                  <Bubble
                    key={m.id}
                    m={m}
                    agent={m.dir === "out" && m.agent ? agents[m.agent] : undefined}
                    onRetry={onRetry}
                  />
                ),
              )}
            </>
          )}
        </div>
      )}

      <Composer
        onSend={onSend}
        channelName={ch ? ch.name : "kanal"}
        role={role}
        canned={canned}
        onManageCanned={onManageCanned}
        aiEnabled={aiEnabled}
        onSuggest={onSuggest}
        docEnabled={docEnabled}
        onOpenDocPicker={() => setPickerOpen(true)}
      />

      {pickerOpen && conv && (
        <DocumentPicker
          conversation={conv.id}
          doctypes={docDoctypes}
          onClose={() => { setPickerOpen(false); setDocError(null); }}
          onSend={handleDocSend}
          sending={docSending}
          error={docError}
        />
      )}
    </section>
  );
}
