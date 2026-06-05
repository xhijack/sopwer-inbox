import { useState } from "react";
import { createPortal } from "react-dom";
import { useFrappeGetCall } from "frappe-react-sdk";
import { Ic } from "./icons";
import { rupiah } from "@/lib/format";
import type { SendableDocument } from "@/types";

export function DocumentPicker({
  conversation,
  doctypes,
  onClose,
  onSend,
  sending,
  error,
}: {
  conversation: string;
  doctypes: string[];
  onClose: () => void;
  onSend: (doctype: string, name: string) => void;
  sending?: boolean;
  error?: string | null;
}) {
  const [doctype, setDoctype] = useState(doctypes[0] || "");
  const [q, setQ] = useState("");
  const { data, isLoading } = useFrappeGetCall<{ message: SendableDocument[] }>(
    "sopwer_inbox.api.document.list_sendable_documents",
    { conversation, doctype, q },
    doctype ? undefined : null,
  );
  const rows = data?.message || [];

  // Portal to <body> so the overlay centers on the viewport, never trapped
  // inside a transformed / overflow-clipped ancestor (the thread column).
  return createPortal(
    <div className="overlay" onClick={onClose}>
      <div className="sheet doc-picker" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <div className="ic">
            <Ic.File size={18} />
          </div>
          <div>
            <h2>Kirim Dokumen</h2>
            <p>Pilih dokumen pelanggan untuk dikirim.</p>
          </div>
          <button className="x" onClick={onClose} title="Tutup">
            <Ic.X size={16} />
          </button>
        </div>

        <div className="doc-controls">
          <select value={doctype} onChange={(e) => setDoctype(e.target.value)}>
            {doctypes.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <div className="doc-search">
            <Ic.Search size={14} />
            <input
              placeholder="Cari nomor dokumen…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
        </div>

        {error && (
          <div className="doc-error">
            <Ic.AlertTriangle size={14} />
            <span>{error}</span>
          </div>
        )}
        {sending && (
          <div className="doc-sending">
            <span className="spin" style={{ display: "inline-flex" }}><Ic.Loader size={14} /></span>
            <span>Mengirim dokumen…</span>
          </div>
        )}

        <div className="doc-list">
          {isLoading && <div className="doc-empty">Memuat…</div>}
          {!isLoading && rows.length === 0 && (
            <div className="doc-empty">
              <Ic.Inbox size={22} />
              <span>Tidak ada dokumen untuk pelanggan ini.</span>
            </div>
          )}
          {!isLoading &&
            rows.map((r) => (
              <button
                key={r.name}
                className="doc-row"
                disabled={sending}
                onClick={() => onSend(doctype, r.name)}
              >
                <div className="doc-row-main">
                  <span className="no">{r.name}</span>
                  <span className="meta">{[r.date, r.status].filter(Boolean).join(" · ")}</span>
                </div>
                <span className="total">{rupiah(r.grand_total, r.currency || "Rp")}</span>
                <Ic.Send size={14} className="doc-row-go" />
              </button>
            ))}
        </div>
      </div>
    </div>,
    document.body,
  );
}
