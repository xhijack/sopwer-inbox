import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { useFrappeEventListener } from "frappe-react-sdk";
import { Sidebar, type SidebarCounts } from "./components/Sidebar";
import { ConversationList } from "./components/ConversationList";
import { Thread } from "./components/Thread";
import { ContactPanel } from "./components/ContactPanel";
import {
  CannedManager,
  AISettings,
  ToastStack,
  type AIConfig,
  type ToastItem,
} from "./components/Modals";
import type { ComposerMode } from "./components/Composer";
import { useSession } from "./hooks/useSession";
import {
  useChannels,
  useConversations,
  useMessages,
  useCanned,
  useAgents,
} from "./hooks/useInboxData";
import { useContactContext } from "./hooks/useContactContext";
import { useInboxApi } from "./hooks/useInboxApi";
import { messageToVM } from "./lib/mappers";
import { hhmm } from "./lib/format";
import type {
  ConvStatus,
  ConversationVM,
  MessageVM,
  NewMessageEvent,
  ConversationUpdatedEvent,
  UIStatus,
} from "./types";

export function InboxApp() {
  const session = useSession();
  const { channels } = useChannels();
  const { agents } = useAgents();
  const { conversations, isLoading: convsLoading, mutate: mutateConvs } = useConversations();
  const { canned, mutate: mutateCanned } = useCanned();
  const api = useInboxApi();

  const [statusFilter, setStatusFilter] = useState<UIStatus>("open");
  const [scope, setScope] = useState<"me" | "all">("all");
  const [channelSel, setChannelSel] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [filterAgent, setFilterAgent] = useState<string | null>(null);
  const [unreplied, setUnreplied] = useState(false);
  const [sortBy, setSortBy] = useState<"newest" | "oldest">("newest");
  const [selId, setSelId] = useState<string | null>(null);
  const [cpCollapsed, setCpCollapsed] = useState(false);
  const [sbCollapsed, setSbCollapsed] = useState(false);
  const [listCollapsed, setListCollapsed] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [bannerForced, setBannerForced] = useState(false);

  const [agentStatus, setAgentStatus] = useState<"available" | "away">("available");
  const [modal, setModal] = useState<null | "canned" | "ai">(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [ai, setAi] = useState<AIConfig>({
    enabled: true,
    provider: "ollama",
    endpoint: "http://localhost:11434",
    model: "llama3.1:8b",
    apiKey: "",
  });

  // Local optimistic message overlay, keyed by conversation id.
  const [optimistic, setOptimistic] = useState<Record<string, MessageVM[]>>({});

  const selConv = useMemo(
    () => conversations.find((c) => c.id === selId) || null,
    [conversations, selId],
  );

  // Auto-select the first conversation once loaded.
  useEffect(() => {
    if (!selId && conversations.length) setSelId(conversations[0].id);
  }, [conversations, selId]);

  const { messages: rawMessages, isLoading: msgsLoading, mutate: mutateMessages } =
    useMessages(selId);
  const { context, isLoading: ctxLoading, mutate: mutateContext } = useContactContext(selId);

  const messages = useMemo<MessageVM[]>(() => {
    const base = rawMessages.map(messageToVM);
    const extra = (selId && optimistic[selId]) || [];
    // Drop optimistic entries that the server has since echoed (best-effort by text+pending).
    return [...base, ...extra];
  }, [rawMessages, optimistic, selId]);

  // Mark read on open.
  const markedRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!selId || !selConv || selConv.unread === 0) return;
    if (markedRef.current.has(selId)) return;
    markedRef.current.add(selId);
    api.markRead(selId).then(() => mutateConvs());
  }, [selId, selConv, api, mutateConvs]);

  const counts = useMemo<SidebarCounts>(() => {
    const c: SidebarCounts = {
      open: 0,
      pending: 0,
      resolved: 0,
      mine: 0,
      all: conversations.length,
      byChannel: {},
    };
    conversations.forEach((x) => {
      c[x.status]++;
      if (x.assignee === session.userId) c.mine++;
      c.byChannel[x.channelId] = (c.byChannel[x.channelId] || 0) + 1;
    });
    return c;
  }, [conversations, session.userId]);

  const filtered = useMemo<ConversationVM[]>(() => {
    let r = conversations.filter((c) => c.status === statusFilter);
    if (scope === "me") r = r.filter((c) => c.assignee === session.userId);
    if (channelSel.length) r = r.filter((c) => channelSel.includes(c.channelId));
    if (filterAgent) r = r.filter((c) => c.assignee === filterAgent);
    if (search.trim()) {
      const q = search.toLowerCase();
      r = r.filter(
        (c) =>
          c.contact.name.toLowerCase().includes(q) ||
          c.contact.handle.toLowerCase().includes(q),
      );
    }
    // unreplied = last message inbound; preview prefix heuristic not available,
    // so we rely on unread>0 OR no outbound marker. Keep simple: unread.
    if (unreplied) r = r.filter((c) => c.unread > 0);
    if (sortBy === "oldest") r = [...r].reverse();
    return r;
  }, [conversations, statusFilter, scope, channelSel, filterAgent, search, unreplied, sortBy, session.userId]);

  const searchEmpty = search.trim() !== "" && filtered.length === 0;

  // failed conversation set for the list "Gagal terkirim" marker.
  const failedIds = useMemo(() => {
    const s = new Set<string>();
    if (selId) {
      const hasFailed = messages.some((m) => m.dir === "out" && m.status === "failed");
      if (hasFailed) s.add(selId);
    }
    return s;
  }, [messages, selId]);

  const banner = (bannerForced || false) && !bannerDismissed;

  const selectConv = useCallback(
    (id: string) => {
      setSelId(id);
      markedRef.current.delete(id);
    },
    [],
  );

  function toggleChannel(id: string) {
    setChannelSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  /* ── optimistic send ── */
  async function sendMsg(text: string, mode: ComposerMode) {
    if (!selId) return;
    const tmpId = "tmp" + Date.now();
    const time = hhmm(new Date().toISOString());

    if (mode === "note") {
      const note: MessageVM = { id: tmpId, dir: "out", type: "note", text, time, agent: session.userId, optimistic: true };
      setOptimistic((o) => ({ ...o, [selId]: [...(o[selId] || []), note] }));
      try {
        await api.addInternalNote(selId, text);
        await mutateMessages();
      } finally {
        setOptimistic((o) => ({ ...o, [selId]: (o[selId] || []).filter((m) => m.id !== tmpId) }));
      }
      return;
    }

    const bubble: MessageVM = {
      id: tmpId,
      dir: "out",
      type: "text",
      text,
      time,
      status: "pending",
      agent: session.userId,
      optimistic: true,
    };
    setOptimistic((o) => ({ ...o, [selId]: [...(o[selId] || []), bubble] }));

    try {
      await api.sendMessage({ conversation: selId, text });
      await mutateMessages();
      await mutateConvs();
      setOptimistic((o) => ({ ...o, [selId]: (o[selId] || []).filter((m) => m.id !== tmpId) }));
    } catch {
      // mark the optimistic bubble failed (stays until retry)
      setOptimistic((o) => ({
        ...o,
        [selId]: (o[selId] || []).map((m) => (m.id === tmpId ? { ...m, status: "failed" } : m)),
      }));
    }
  }

  async function retryMsg(mid: string) {
    if (!selId) return;
    // Optimistic bubble (client-only failure) → re-send.
    const optMsg = (optimistic[selId] || []).find((m) => m.id === mid);
    if (optMsg && optMsg.text) {
      setOptimistic((o) => ({
        ...o,
        [selId]: (o[selId] || []).map((m) => (m.id === mid ? { ...m, status: "pending" } : m)),
      }));
      try {
        await api.sendMessage({ conversation: selId, text: optMsg.text });
        await mutateMessages();
        setOptimistic((o) => ({ ...o, [selId]: (o[selId] || []).filter((m) => m.id !== mid) }));
      } catch {
        setOptimistic((o) => ({
          ...o,
          [selId]: (o[selId] || []).map((m) => (m.id === mid ? { ...m, status: "failed" } : m)),
        }));
      }
      return;
    }
    // Persisted failed message → server retry.
    try {
      await api.retryMessage(mid);
      await mutateMessages();
    } catch {
      /* keep failed state */
    }
  }

  // AI agent-assist — Phase 9 deferred: there is NO AI backend. Surface the
  // "fitur AI belum aktif" state by rejecting.
  function suggestReply(): Promise<string> {
    return new Promise((_resolve, reject) => {
      setTimeout(() => reject(new Error("ai-not-active")), 700);
    });
  }

  async function onStatus(s: ConvStatus) {
    if (!selId) return;
    await api.setStatus(selId, s);
    await mutateConvs();
    const ui = s.toLowerCase() as UIStatus;
    if (ui !== statusFilter) setStatusFilter(ui);
  }

  async function onAssign(a: string | null) {
    if (!selId) return;
    await api.assign(selId, a);
    await mutateConvs();
  }

  /* ── contact panel edits (persist via frappe.client.set_value) ── */
  async function persistDocValue(doctype: string, name: string, field: string, value: string) {
    await fetch("/api/method/frappe.client.set_value", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Frappe-CSRF-Token": window.csrf_token || "",
      },
      body: JSON.stringify({ doctype, name, fieldname: field, value }),
    });
  }

  async function rename(name: string) {
    if (!selConv || !context?.contact?.name) return;
    await persistDocValue("Contact", context.contact.name, "first_name", name);
    await mutateContext();
  }
  async function setNote(note: string) {
    if (!context?.contact?.name) return;
    await persistDocValue("Contact", context.contact.name, "inbox_notes", note);
    await mutateContext();
  }
  async function addTag(tag: string) {
    if (!selConv || selConv.tags.includes(tag)) return;
    await persistDocValue("Inbox Conversation", selConv.id, "tags", [...selConv.tags, tag].join(", "));
    await mutateConvs();
  }
  async function removeTag(tag: string) {
    if (!selConv) return;
    await persistDocValue(
      "Inbox Conversation",
      selConv.id,
      "tags",
      selConv.tags.filter((t) => t !== tag).join(", "),
    );
    await mutateConvs();
  }

  /* ── realtime ── */
  useFrappeEventListener("inbox:new_message", (ev: NewMessageEvent) => {
    mutateConvs();
    if (ev.conversation === selId) {
      mutateMessages();
      return;
    }
    // Toast for inbound messages on other conversations.
    if (ev.direction === "Incoming" && !ev.is_internal) {
      const conv = conversations.find((c) => c.id === ev.conversation);
      if (conv) {
        const toast: ToastItem = {
          id: ev.message,
          conv,
          channel: channels[conv.channelId],
          preview: conv.preview || "Pesan baru",
        };
        setToasts((ts) => (ts.find((x) => x.conv.id === conv.id) ? ts : [...ts, toast]));
        setTimeout(() => setToasts((ts) => ts.filter((x) => x.id !== toast.id)), 5200);
      }
    }
  });

  useFrappeEventListener("inbox:conversation_updated", (_ev: ConversationUpdatedEvent) => {
    mutateConvs();
  });

  return (
    <div
      className={
        "app" +
        (cpCollapsed ? " cp-collapsed" : "") +
        (sbCollapsed ? " sb-collapsed" : "") +
        (listCollapsed ? " list-collapsed" : "")
      }
    >
      <Sidebar
        counts={counts}
        filter={statusFilter}
        setFilter={setStatusFilter}
        scope={scope}
        setScope={setScope}
        channels={Object.values(channels)}
        channelSel={channelSel}
        toggleChannel={toggleChannel}
        clearChannels={() => setChannelSel([])}
        role={session.role}
        onOpenCanned={() => setModal("canned")}
        onOpenAI={() => setModal("ai")}
        agentStatus={agentStatus}
        setAgentStatus={setAgentStatus}
        fullName={session.fullName}
        collapsed={sbCollapsed}
        onToggle={() => setSbCollapsed((v) => !v)}
      />

      <ConversationList
        convs={filtered}
        channels={channels}
        agents={agents}
        failedIds={failedIds}
        selId={selId}
        onSelect={selectConv}
        search={search}
        setSearch={setSearch}
        statusFilter={statusFilter}
        scope={scope}
        setScope={setScope}
        loading={convsLoading}
        searchEmpty={searchEmpty}
        filterAgent={filterAgent}
        setFilterAgent={setFilterAgent}
        unreplied={unreplied}
        setUnreplied={setUnreplied}
        sortBy={sortBy}
        setSortBy={setSortBy}
        myUserId={session.userId}
        collapsed={listCollapsed}
        onToggleCollapse={() => setListCollapsed((v) => !v)}
      />

      <Thread
        conv={selConv}
        messages={messages}
        agents={agents}
        channels={channels}
        myUserId={session.userId}
        loading={msgsLoading && messages.length === 0}
        banner={banner}
        onDismissBanner={() => setBannerDismissed(true)}
        onReconnect={() => {
          setBannerForced(false);
          setBannerDismissed(true);
        }}
        onStatus={onStatus}
        onAssign={onAssign}
        onSend={sendMsg}
        onRetry={retryMsg}
        cpCollapsed={cpCollapsed}
        onToggleCp={() => setCpCollapsed(false)}
        role={session.role}
        canned={canned}
        onManageCanned={() => setModal("canned")}
        aiEnabled={ai.enabled}
        onSuggest={suggestReply}
      />

      {!cpCollapsed && (
        <ContactPanel
          conv={selConv}
          channel={selConv ? channels[selConv.channelId] : undefined}
          context={context}
          contextLoading={ctxLoading}
          onClose={() => setCpCollapsed(true)}
          onRename={rename}
          onAddTag={addTag}
          onRemoveTag={removeTag}
          onNote={setNote}
        />
      )}

      <ToastStack
        toasts={toasts}
        onOpen={(id) => {
          selectConv(id);
          setToasts((ts) => ts.filter((x) => x.conv.id !== id));
        }}
        onDismiss={(id) => setToasts((ts) => ts.filter((x) => x.id !== id))}
      />

      {modal === "canned" && session.isManager && (
        <CannedManager
          canned={canned}
          onChanged={() => mutateCanned()}
          onClose={() => setModal(null)}
        />
      )}
      {modal === "ai" && session.isManager && (
        <AISettings
          ai={ai}
          onChange={(patch) => setAi((a) => ({ ...a, ...patch }))}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}
