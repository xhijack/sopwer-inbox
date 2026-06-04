import { useState, useEffect } from "react";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import { Ic, ChannelGlyph } from "./icons";
import { tagClass, rupiah } from "@/lib/format";
import type { ChannelVM, ContactContext, ConversationVM } from "@/types";

/* ── Suggestion / search result row ── */
interface CustomerOption {
  name: string;
  label: string;
  reason?: string;
}

interface LinkCustomerBlockProps {
  convId: string;
  contactName: string;
  onLinked: () => void;
}

function LinkCustomerBlock({ convId, contactName, onLinked }: LinkCustomerBlockProps) {
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<CustomerOption[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);

  const { data: optData, mutate: mutateOpts } = useFrappeGetCall<{
    message: { linked: string | null; suggestions: CustomerOption[] };
  }>(
    "sopwer_inbox.api.crm.customer_options",
    { conversation: convId },
    `crm-opts:${convId}`,
    { revalidateOnFocus: false },
  );

  const suggestions = optData?.message?.suggestions ?? [];
  const linked = optData?.message?.linked ?? null;

  const { call: callLink, loading: linking } = useFrappePostCall(
    "sopwer_inbox.api.crm.link_customer",
  );
  const { call: callSearch } = useFrappePostCall(
    "sopwer_inbox.api.crm.search_customers",
  );
  const { call: callCreate, loading: creating } = useFrappePostCall(
    "sopwer_inbox.api.crm.create_and_link_customer",
  );

  // If already linked, nothing to render
  if (linked) return null;

  async function doLink(customer: string) {
    setLinkError(null);
    try {
      await callLink({ conversation: convId, customer });
      mutateOpts();
      onLinked();
    } catch (e: unknown) {
      setLinkError(e instanceof Error ? e.message : "Gagal menghubungkan customer.");
    }
  }

  async function doSearch(q: string) {
    setSearchQ(q);
    if (!q.trim()) { setSearchResults([]); return; }
    setSearchError(null);
    setSearching(true);
    try {
      const res = await callSearch({ q }) as { message: CustomerOption[] } | undefined;
      setSearchResults(res?.message ?? []);
    } catch (e: unknown) {
      setSearchError(e instanceof Error ? e.message : "Gagal mencari customer.");
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }

  async function doCreate() {
    setCreateError(null);
    try {
      await callCreate({ conversation: convId, customer_name: contactName });
      mutateOpts();
      onLinked();
    } catch (e: unknown) {
      setCreateError(e instanceof Error ? e.message : "Gagal membuat customer.");
    }
  }

  return (
    <div className="cp-sec cp-link-customer">
      <div className="lbl">
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
          <Ic.UserCheck size={12} /> Hubungkan ke Customer
        </span>
      </div>
      <p className="clc-hint">
        Kaitkan kontak ini ke Customer ERPNext untuk melihat order/invoice & mengirim dokumen.
      </p>

      {suggestions.length > 0 && (
        <div className="clc-suggestions">
          {suggestions.map((s) => (
            <div key={s.name} className="clc-row">
              <div className="clc-info">
                <span className="clc-label">Sepertinya: {s.label}</span>
                {s.reason && <span className="clc-reason">{s.reason}</span>}
              </div>
              <button
                className="btn btn-sm btn-outline"
                disabled={linking}
                onClick={() => doLink(s.name)}
              >
                {linking ? "…" : "Hubungkan"}
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="clc-search-wrap">
        <input
          className="clc-search"
          placeholder="Cari customer…"
          value={searchQ}
          onChange={(e) => doSearch(e.target.value)}
        />
        {searching && <span className="clc-searching">Mencari…</span>}
        {searchError && <div className="clc-error">{searchError}</div>}
        {!searching && searchResults.length > 0 && (
          <div className="clc-results">
            {searchResults.map((r) => (
              <div key={r.name} className="clc-row">
                <span className="clc-label">{r.label}</span>
                <button
                  className="btn btn-sm btn-outline"
                  disabled={linking}
                  onClick={() => doLink(r.name)}
                >
                  {linking ? "…" : "Hubungkan"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <button
        className="btn btn-sm btn-outline clc-create-btn"
        disabled={creating}
        onClick={doCreate}
      >
        {creating ? (
          <span className="spin" style={{ display: "inline-flex" }}><Ic.Loader size={13} /></span>
        ) : (
          <Ic.Plus size={13} />
        )}
        Buat customer baru ({contactName || "kontak"})
      </button>

      {linkError && <div className="clc-error">{linkError}</div>}
      {createError && <div className="clc-error">{createError}</div>}
    </div>
  );
}

interface ContactPanelProps {
  conv: ConversationVM | null;
  channel: ChannelVM | undefined;
  context: ContactContext | null;
  contextLoading: boolean;
  onClose: () => void;
  onRename: (name: string) => void;
  onAddTag: (tag: string) => void;
  onRemoveTag: (tag: string) => void;
  onNote: (note: string) => void;
  onCustomerLinked?: () => void;
}

export function ContactPanel({
  conv,
  channel,
  context,
  contextLoading,
  onClose,
  onRename,
  onAddTag,
  onRemoveTag,
  onNote,
  onCustomerLinked,
}: ContactPanelProps) {
  const [editingName, setEditingName] = useState(false);
  const [nameVal, setNameVal] = useState("");
  const [addingTag, setAddingTag] = useState(false);
  const [tagVal, setTagVal] = useState("");
  const [noteVal, setNoteVal] = useState("");

  const inboxNotes = context?.contact?.inbox_notes ?? "";
  useEffect(() => {
    setNoteVal(inboxNotes || "");
  }, [inboxNotes, conv?.id]);

  if (!conv) {
    return (
      <aside className="cpanel">
        <div className="cp-head">
          <h3>Detail Kontak</h3>
          <button
            className="icon-btn"
            onClick={onClose}
            title="Tutup panel"
            style={{ width: 28, height: 28 }}
          >
            <Ic.PanelRight size={15} />
          </button>
        </div>
        <div className="cp-scroll">
          <div style={{ fontSize: 13, color: "var(--fg-3)", textAlign: "center", padding: 20 }}>
            Pilih percakapan untuk melihat detail kontak.
          </div>
        </div>
      </aside>
    );
  }

  const ct = conv.contact;
  const erp = context?.erp ?? null;
  const prev = context?.previous_conversations ?? [];

  function commitName() {
    if (nameVal.trim()) onRename(nameVal.trim());
    setEditingName(false);
  }
  function commitTag() {
    const v = tagVal.trim();
    if (v) onAddTag(v);
    setTagVal("");
    setAddingTag(false);
  }

  const erpDocs = erp ? [...(erp.sales_orders || []), ...(erp.invoices || [])] : [];

  return (
    <aside className="cpanel">
      <div className="cp-head">
        <h3>Detail Kontak</h3>
        <button
          className="icon-btn"
          onClick={onClose}
          title="Tutup panel"
          style={{ width: 28, height: 28 }}
        >
          <Ic.PanelRight size={15} />
        </button>
      </div>
      <div className="cp-scroll">
        <div className="cp-id">
          <div className="ava-wrap">
            <div className="ava" style={{ background: ct.color }}>
              {ct.initials}
            </div>
            {channel && (
              <div className={"ch " + channel.type}>
                <ChannelGlyph ch={channel.type} size={13} />
              </div>
            )}
          </div>
          {editingName ? (
            <input
              className="cp-name-edit"
              autoFocus
              value={nameVal}
              onChange={(e) => setNameVal(e.target.value)}
              onBlur={commitName}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitName();
                if (e.key === "Escape") setEditingName(false);
              }}
              style={{ fontFamily: "var(--font-display)", fontSize: 17, fontWeight: 700 }}
            />
          ) : (
            <div className="cp-name-edit">
              <span className="nm">{ct.name}</span>
              <span
                className="pen"
                title="Edit nama"
                onClick={() => {
                  setNameVal(ct.name);
                  setEditingName(true);
                }}
              >
                <Ic.Edit size={13} />
              </span>
            </div>
          )}
          <div className="handle">{ct.handle}</div>
          {channel && (
            <span className={"chrow " + channel.type}>
              <ChannelGlyph ch={channel.type} size={11} />
              {channel.name}
            </span>
          )}
        </div>

        <div className="cp-sec">
          <div className="lbl">Tag percakapan</div>
          <div className="cp-tags">
            {conv.tags.map((tg) => (
              <span key={tg} className={"cp-tag " + tagClass(tg)}>
                {tg}
                <span className="x" title="Hapus tag" onClick={() => onRemoveTag(tg)}>
                  <Ic.X size={11} />
                </span>
              </span>
            ))}
            {addingTag ? (
              <input
                className="cp-tag-input"
                autoFocus
                value={tagVal}
                placeholder="nama tag…"
                onChange={(e) => setTagVal(e.target.value)}
                onBlur={commitTag}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitTag();
                  if (e.key === "Escape") {
                    setTagVal("");
                    setAddingTag(false);
                  }
                }}
              />
            ) : (
              <button className="cp-tag-add" onClick={() => setAddingTag(true)}>
                <Ic.Plus size={12} />
                Tag
              </button>
            )}
          </div>
        </div>

        <div className="cp-sec">
          <div className="lbl">Catatan tentang kontak</div>
          <textarea
            className="cp-note"
            rows={3}
            value={noteVal}
            placeholder="Catatan lengket — muncul tiap kontak ini chat. Mis. preferensi, riwayat penting…"
            onChange={(e) => setNoteVal(e.target.value)}
            onBlur={() => {
              if (noteVal !== (inboxNotes || "")) onNote(noteVal);
            }}
          />
        </div>

        <div className="cp-sec">
          <div className="lbl">Informasi</div>
          {channel && (
            <div className="cp-attr">
              <span className="k">Kanal</span>
              <span className="v">{channel.name}</span>
            </div>
          )}
          <div className="cp-attr">
            <span className="k">Status</span>
            <span className="v" style={{ textTransform: "capitalize" }}>
              {conv.status}
            </span>
          </div>
          <div className="cp-attr">
            <span className="k">Total chat</span>
            <span className="v">{prev.length}</span>
          </div>
        </div>

        {!erp && conv && (
          <LinkCustomerBlock
            convId={conv.id}
            contactName={ct.name}
            onLinked={onCustomerLinked ?? (() => {})}
          />
        )}

        {erp && erpDocs.length > 0 && (
          <div className="cp-sec">
            <div className="lbl">
              <span>Dari ERPNext</span>
              <span style={{ color: "var(--sw-green-600)", textTransform: "none", letterSpacing: 0 }}>
                ● Terhubung
              </span>
            </div>
            {erpDocs.map((o) => {
              const isInvoice = o.name.toLowerCase().includes("inv") || (erp.invoices || []).includes(o);
              const paid = (o.status || "").toLowerCase().includes("paid");
              return (
                <div className="erp-card" key={o.name}>
                  <div className="eh">
                    <span className="no">{o.name}</span>
                    <span
                      className="lbl"
                      style={{ marginLeft: "auto", marginBottom: 0, letterSpacing: 0, textTransform: "none" }}
                    >
                      {isInvoice ? "Invoice" : "Sales Order"}
                    </span>
                  </div>
                  <div className="eb">
                    <div>
                      <div className="amt">{rupiah(o.grand_total, o.currency || "Rp")}</div>
                      <div className="dt">{o.transaction_date || o.posting_date || ""}</div>
                    </div>
                    <span className={"pill " + (paid ? "paid" : "pending")}>
                      <span className="dot" />
                      {paid ? "Lunas" : o.status || "Menunggu"}
                    </span>
                  </div>
                </div>
              );
            })}
            <a className="erp-link" href="#" onClick={(e) => e.preventDefault()}>
              Lihat di ERPNext <Ic.ChevronRight size={13} />
            </a>
          </div>
        )}

        <div className="cp-sec">
          <div className="lbl">Percakapan sebelumnya</div>
          {contextLoading && (
            <div style={{ fontSize: 12, color: "var(--fg-3)" }}>Memuat…</div>
          )}
          {!contextLoading && prev.length <= 1 && (
            <div style={{ fontSize: 12, color: "var(--fg-3)", lineHeight: 1.5 }}>
              Belum ada percakapan lain dengan kontak ini.
            </div>
          )}
          {prev.map((h) => (
            <div className="cp-prev-item" key={h.name}>
              <span
                className="dot"
                style={{ background: `var(--st-${(h.status || "Open").toLowerCase()})` }}
              />
              <div className="t">
                <div className="s">{(h.last_message_preview || "Belum ada pesan").slice(0, 38)}</div>
                <div className="d">{[h.channel, h.status].filter(Boolean).join(" · ")}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
