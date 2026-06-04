import { useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";
import { Ic } from "./icons";
import type { SendableDocument } from "@/types";

export function DocumentPicker({
  conversation,
  doctypes,
  onClose,
  onSend,
}: {
  conversation: string;
  doctypes: string[];
  onClose: () => void;
  onSend: (doctype: string, name: string) => void;
}) {
  const [doctype, setDoctype] = useState(doctypes[0] || "");
  const [q, setQ] = useState("");
  const { data } = useFrappeGetCall<{ message: SendableDocument[] }>(
    "sopwer_inbox.api.document.list_sendable_documents",
    { conversation, doctype, q },
    doctype ? undefined : null, // don't fetch until a doctype is chosen
  );
  const rows = data?.message || [];
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal doc-picker" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Kirim Dokumen</h3>
          <button className="icon-btn" onClick={onClose}>
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
          <input
            placeholder="Cari nomor dokumen…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="doc-list">
          {rows.length === 0 && <div className="doc-empty">Tidak ada dokumen.</div>}
          {rows.map((r) => (
            <button key={r.name} className="doc-row" onClick={() => onSend(doctype, r.name)}>
              <span className="no">{r.name}</span>
              <span className="meta">
                {r.date} · {r.status}
              </span>
              <span className="total">{r.grand_total}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
