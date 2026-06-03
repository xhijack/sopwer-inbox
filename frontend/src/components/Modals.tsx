import { useState } from "react";
import {
  useFrappeCreateDoc,
  useFrappeUpdateDoc,
  useFrappeDeleteDoc,
} from "frappe-react-sdk";
import { Ic, ChannelGlyph } from "./icons";
import type {
  ChannelVM,
  ConversationVM,
  InboxCannedResponse,
} from "@/types";

/* ───────────── KELOLA BALASAN CEPAT ───────────── */
interface CannedManagerProps {
  canned: InboxCannedResponse[];
  onChanged: () => void;
  onClose: () => void;
}

type CannedForm = { name: string | null; title: string; slug: string; body: string };

export function CannedManager({ canned, onChanged, onClose }: CannedManagerProps) {
  const [form, setForm] = useState<CannedForm | null>(null);
  const [busy, setBusy] = useState(false);
  const { createDoc } = useFrappeCreateDoc();
  const { updateDoc } = useFrappeUpdateDoc();
  const { deleteDoc } = useFrappeDeleteDoc();

  function startAdd() {
    setForm({ name: null, title: "", slug: "", body: "" });
  }
  function startEdit(c: InboxCannedResponse) {
    setForm({ name: c.name, title: c.title, slug: c.shortcut, body: c.message });
  }
  async function remove(name: string) {
    setBusy(true);
    try {
      await deleteDoc("Inbox Canned Response", name);
      onChanged();
    } finally {
      setBusy(false);
    }
  }
  async function commit() {
    if (!form || !form.title.trim() || !form.slug.trim() || !form.body.trim()) return;
    const slug = form.slug.trim().replace(/^\//, "").replace(/\s+/g, "-").toLowerCase();
    setBusy(true);
    try {
      if (form.name) {
        await updateDoc("Inbox Canned Response", form.name, {
          title: form.title.trim(),
          shortcut: slug,
          message: form.body.trim(),
        });
      } else {
        await createDoc("Inbox Canned Response", {
          title: form.title.trim(),
          shortcut: slug,
          message: form.body.trim(),
        });
      }
      setForm(null);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="sheet" style={{ maxWidth: 600 }} onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <div className="ic">
            <Ic.MessageSquare size={20} />
          </div>
          <div>
            <h2>Kelola Balasan Cepat</h2>
            <p>
              Balasan yang muncul saat agen mengetik{" "}
              <code style={{ fontFamily: "var(--font-mono)" }}>/</code> di composer.
            </p>
            <span className="mgr-badge">
              <Ic.Lock size={10} />
              AKSES MANAGER
            </span>
          </div>
          <button className="x" onClick={onClose}>
            <Ic.X size={18} />
          </button>
        </div>
        <div className="sheet-body">
          {form && (
            <div className="cm-form">
              <div className="row">
                <div className="fld">
                  <label>Judul</label>
                  <input
                    value={form.title}
                    placeholder="mis. Salam pembuka"
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                  />
                </div>
                <div className="fld slug-fld" style={{ maxWidth: 180 }}>
                  <label>Shortcut</label>
                  <input
                    value={form.slug}
                    placeholder="halo"
                    onChange={(e) => setForm({ ...form, slug: e.target.value })}
                  />
                </div>
              </div>
              <div className="fld">
                <label>Isi balasan</label>
                <textarea
                  rows={3}
                  value={form.body}
                  placeholder="Tulis isi balasan…"
                  onChange={(e) => setForm({ ...form, body: e.target.value })}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 4 }}>
                <button className="btn btn-ghost" onClick={() => setForm(null)}>
                  Batal
                </button>
                <button className="btn btn-primary" onClick={commit} disabled={busy}>
                  {form.name ? "Simpan perubahan" : "Tambah balasan"}
                </button>
              </div>
            </div>
          )}
          {!form && (
            <button
              className="btn btn-outline"
              style={{ marginBottom: 14, width: "100%", justifyContent: "center" }}
              onClick={startAdd}
            >
              <Ic.Plus size={15} />
              Tambah balasan cepat
            </button>
          )}
          {canned.map((c) => (
            <div className="cm-item" key={c.name}>
              <span className="slug">/{c.shortcut}</span>
              <div className="body">
                <div className="ttl">{c.title}</div>
                <div className="txt">{c.message}</div>
              </div>
              <div className="acts">
                <button onClick={() => startEdit(c)} title="Edit">
                  <Ic.Edit size={14} />
                </button>
                <button className="del" onClick={() => remove(c.name)} title="Hapus" disabled={busy}>
                  <Ic.Trash size={14} />
                </button>
              </div>
            </div>
          ))}
          {canned.length === 0 && (
            <div style={{ textAlign: "center", color: "var(--fg-3)", fontSize: 13, padding: "20px 0" }}>
              Belum ada balasan cepat. Tambahkan yang pertama.
            </div>
          )}
        </div>
        <div className="sheet-foot">
          <button className="btn btn-ghost" onClick={onClose}>
            Tutup
          </button>
        </div>
      </div>
    </div>
  );
}

/* ───────────── SETTINGAN AI ───────────── */
export interface AIConfig {
  enabled: boolean;
  provider: "ollama" | "claude" | "openai";
  endpoint: string;
  model: string;
  apiKey: string;
}

interface AISettingsProps {
  ai: AIConfig;
  onChange: (patch: Partial<AIConfig>) => void;
  onClose: () => void;
}

export function AISettings({ ai, onChange, onClose }: AISettingsProps) {
  const [test, setTest] = useState<"idle" | "testing" | "ok">("idle");
  const isCloud = ai.provider !== "ollama";

  // AI backend is Phase 9 (deferred) — "Tes koneksi" simulates the UX only.
  function runTest() {
    setTest("testing");
    setTimeout(() => setTest("ok"), 1300);
  }

  const PROVIDERS = [
    { id: "ollama" as const, nm: "Ollama", tag: "Lokal", icon: <Ic.Server size={17} /> },
    { id: "claude" as const, nm: "Claude", tag: "Cloud", icon: <Ic.Cloud size={17} /> },
    { id: "openai" as const, nm: "OpenAI", tag: "Cloud", icon: <Ic.Cloud size={17} /> },
  ];

  return (
    <div className="overlay" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <div className="ic">
            <Ic.Sparkles size={20} />
          </div>
          <div>
            <h2>Settingan AI</h2>
            <p>
              Agent-assist ("Sarankan balasan"). Provider-agnostic — agen selalu di loop, tidak ada
              auto-send. Build AI ditunda (Phase 9).
            </p>
            <span className="mgr-badge">
              <Ic.Lock size={10} />
              AKSES MANAGER
            </span>
          </div>
          <button className="x" onClick={onClose}>
            <Ic.X size={18} />
          </button>
        </div>
        <div className="sheet-body">
          <div className="ai-section">
            <div className="ai-row">
              <div>
                <div className="lbl">Aktifkan AI assist</div>
                <div className="sub">
                  Tombol "Sarankan balasan" muncul di composer untuk semua agen.
                </div>
              </div>
              <button
                className={"switch" + (ai.enabled ? " on" : "")}
                onClick={() => onChange({ enabled: !ai.enabled })}
              />
            </div>
          </div>

          <div
            className="ai-section"
            style={{ opacity: ai.enabled ? 1 : 0.5, pointerEvents: ai.enabled ? "auto" : "none" }}
          >
            <div className="fld" style={{ marginBottom: 4 }}>
              <label>Provider</label>
            </div>
            <div className="provider-grid">
              {PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  className={"prov" + (ai.provider === p.id ? " on" : "")}
                  onClick={() => {
                    onChange({ provider: p.id, model: "" });
                    setTest("idle");
                  }}
                >
                  <div className="pic">
                    {p.icon}
                    {ai.provider === p.id && <Ic.CheckCircle size={16} />}
                  </div>
                  <div className="nm">{p.nm}</div>
                  <div className="tag">{p.tag}</div>
                </button>
              ))}
            </div>

            <div style={{ marginTop: 14 }}>
              {!isCloud ? (
                <div className="cm-form" style={{ marginBottom: 0 }}>
                  <div className="row">
                    <div className="fld">
                      <label>Endpoint</label>
                      <input
                        value={ai.endpoint}
                        onChange={(e) => onChange({ endpoint: e.target.value })}
                        placeholder="http://localhost:11434"
                      />
                    </div>
                    <div className="fld" style={{ maxWidth: 200 }}>
                      <label>Model</label>
                      <input
                        value={ai.model}
                        onChange={(e) => onChange({ model: e.target.value })}
                        placeholder="llama3.1:8b"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="cm-form" style={{ marginBottom: 0 }}>
                  <div className="row">
                    <div className="fld">
                      <label>API key</label>
                      <input
                        type="password"
                        value={ai.apiKey}
                        onChange={(e) => onChange({ apiKey: e.target.value })}
                        placeholder="sk-…"
                      />
                    </div>
                    <div className="fld" style={{ maxWidth: 200 }}>
                      <label>Model</label>
                      <input
                        value={ai.model}
                        onChange={(e) => onChange({ model: e.target.value })}
                        placeholder={ai.provider === "claude" ? "claude-sonnet-4" : "gpt-4o"}
                      />
                    </div>
                  </div>
                </div>
              )}

              {!isCloud ? (
                <div className="residency local">
                  <Ic.Server size={16} />
                  <div>
                    <b>Data tinggal di server Anda.</b> Isi chat tidak keluar dari infrastruktur
                    sendiri — pilihan paling aman untuk data pelanggan.
                  </div>
                </div>
              ) : (
                <div className="residency cloud">
                  <Ic.AlertTriangle size={16} />
                  <div>
                    <b>
                      Isi chat dikirim ke server {ai.provider === "claude" ? "Anthropic" : "OpenAI"}{" "}
                      di luar negeri.
                    </b>{" "}
                    Pastikan sesuai kebijakan privasi & persetujuan pelanggan Anda.
                  </div>
                </div>
              )}

              <div className="test-row">
                <button className="btn btn-outline" onClick={runTest} disabled={test === "testing"}>
                  {test === "testing" ? (
                    <>
                      <span className="spin" style={{ display: "inline-flex" }}>
                        <Ic.Loader size={14} />
                      </span>
                      Menguji…
                    </>
                  ) : (
                    <>
                      <Ic.Wifi size={15} />
                      Tes koneksi
                    </>
                  )}
                </button>
                {test === "ok" && (
                  <span className="test-status ok">
                    <span className="d" />
                    Koneksi berhasil · {isCloud ? ai.provider : "Ollama"} siap
                  </span>
                )}
                {test === "testing" && (
                  <span className="test-status testing">
                    <span className="d" />
                    Menghubungi provider…
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="sheet-foot">
          <button className="btn btn-primary" onClick={onClose}>
            Selesai
          </button>
        </div>
      </div>
    </div>
  );
}

/* ───────────── TOASTS ───────────── */
export interface ToastItem {
  id: string;
  conv: ConversationVM;
  channel: ChannelVM | undefined;
  preview: string;
}

interface ToastStackProps {
  toasts: ToastItem[];
  onOpen: (id: string) => void;
  onDismiss: (id: string) => void;
}

export function ToastStack({ toasts, onOpen, onDismiss }: ToastStackProps) {
  if (!toasts.length) return null;
  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div className="toast-card" key={t.id} onClick={() => onOpen(t.conv.id)}>
          <div className="av" style={{ background: t.conv.contact.color }}>
            {t.conv.contact.initials}
            {t.channel && (
              <span className={"ch " + t.channel.type}>
                <ChannelGlyph ch={t.channel.type} size={8} />
              </span>
            )}
          </div>
          <div className="b">
            <div className="t">
              {t.conv.contact.name}
              <span className="when">baru saja</span>
            </div>
            <div className="m">{t.preview}</div>
          </div>
          <button
            className="x"
            onClick={(e) => {
              e.stopPropagation();
              onDismiss(t.id);
            }}
          >
            <Ic.X size={15} />
          </button>
        </div>
      ))}
    </div>
  );
}
