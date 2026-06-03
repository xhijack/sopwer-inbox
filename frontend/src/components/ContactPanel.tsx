import { useState, useEffect } from "react";
import { Ic, ChannelGlyph } from "./icons";
import { tagClass, rupiah } from "@/lib/format";
import type { ChannelVM, ContactContext, ConversationVM } from "@/types";

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

  const erpDocs = erp ? [...erp.sales_orders, ...erp.invoices] : [];

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

        {erp && erpDocs.length > 0 && (
          <div className="cp-sec">
            <div className="lbl">
              <span>Dari ERPNext</span>
              <span style={{ color: "var(--sw-green-600)", textTransform: "none", letterSpacing: 0 }}>
                ● Terhubung
              </span>
            </div>
            {erpDocs.map((o) => {
              const isInvoice = o.name.toLowerCase().includes("inv") || erp.invoices.includes(o);
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
