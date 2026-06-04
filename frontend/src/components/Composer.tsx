import { useState, useRef, useEffect, useCallback } from "react";
import { useFrappeFileUpload } from "frappe-react-sdk";
import { Ic } from "./icons";
import type { InboxCannedResponse, MessageType } from "@/types";
import type { Role } from "@/hooks/useSession";

export type ComposerMode = "reply" | "note";
export interface OutgoingMedia {
  url: string;
  type: MessageType;
  name?: string;
}

interface ComposerProps {
  onSend: (text: string, mode: ComposerMode, media?: OutgoingMedia) => void;
  channelName: string;
  role: Role;
  canned: InboxCannedResponse[];
  onManageCanned: () => void;
  aiEnabled: boolean;
  /** Returns a draft, or rejects to surface the AI-failed state. */
  onSuggest: () => Promise<string>;
  disabled?: boolean;
  docEnabled?: boolean;
  onOpenDocPicker?: () => void;
}

export function Composer({
  onSend,
  channelName,
  role,
  canned,
  onManageCanned,
  aiEnabled,
  onSuggest,
  disabled,
  docEnabled,
  onOpenDocPicker,
}: ComposerProps) {
  const [val, setVal] = useState("");
  const [mode, setMode] = useState<ComposerMode>("reply");
  const [focus, setFocus] = useState(false);
  const [showCanned, setShowCanned] = useState(false);
  const [hl, setHl] = useState(0);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiErr, setAiErr] = useState(false);
  const [aiDraft, setAiDraft] = useState(false);
  const [uploadErr, setUploadErr] = useState(false);
  const ta = useRef<HTMLTextAreaElement>(null);
  const imageInput = useRef<HTMLInputElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const { upload, loading: uploading } = useFrappeFileUpload();

  async function onPickFile(e: React.ChangeEvent<HTMLInputElement>, kind: MessageType) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploadErr(false);
    try {
      const res = await upload(file, { isPrivate: true });
      const url = (res as { file_url?: string })?.file_url;
      if (!url) throw new Error("upload returned no file_url");
      // Media always goes to the customer (reply); typed text becomes the caption.
      onSend(val.trim(), "reply", { url, type: kind, name: file.name });
      setVal("");
      setShowCanned(false);
    } catch {
      setUploadErr(true);
    }
  }

  const q = val.startsWith("/") ? val.slice(1).toLowerCase() : "";
  const filtered = showCanned
    ? canned.filter(
        (c) =>
          (c.shortcut || "").toLowerCase().includes(q) ||
          (c.title || "").toLowerCase().includes(q),
      )
    : [];

  const auto = useCallback(() => {
    const el = ta.current;
    if (!el) return;
    el.style.height = "auto";
    // Min 64px (roomy default), grow up to 220px.
    el.style.height = Math.max(64, Math.min(el.scrollHeight, 220)) + "px";
  }, []);

  useEffect(() => {
    auto();
  }, [val, auto]);

  function onChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const v = e.target.value;
    setVal(v);
    setShowCanned(mode === "reply" && v.startsWith("/"));
    setHl(0);
    setAiDraft(false);
  }

  function pick(c: InboxCannedResponse) {
    setVal(c.message);
    setShowCanned(false);
    requestAnimationFrame(() => {
      ta.current?.focus();
      auto();
    });
  }

  function send() {
    const text = val.trim();
    if (!text || (mode === "reply" && text.startsWith("/"))) return;
    onSend(text, mode);
    setVal("");
    setShowCanned(false);
    setAiDraft(false);
    requestAnimationFrame(() => {
      if (ta.current) ta.current.style.height = "auto";
    });
  }

  function onKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (showCanned && filtered.length) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHl((h) => (h + 1) % filtered.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setHl((h) => (h - 1 + filtered.length) % filtered.length);
        return;
      }
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        pick(filtered[hl]);
        return;
      }
      if (e.key === "Escape") {
        setShowCanned(false);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function suggest() {
    setAiErr(false);
    setAiBusy(true);
    onSuggest()
      .then((draft) => {
        setAiBusy(false);
        setAiDraft(true);
        setVal(draft);
        requestAnimationFrame(() => {
          ta.current?.focus();
          auto();
        });
      })
      .catch(() => {
        setAiBusy(false);
        setAiErr(true);
      });
  }

  function switchMode(m: ComposerMode) {
    setMode(m);
    setShowCanned(false);
  }

  const isNote = mode === "note";
  const sendDisabled = !val.trim() || (mode === "reply" && val.startsWith("/")) || !!disabled;

  return (
    <div className={"composer" + (isNote ? " note-mode" : "")}>
      {showCanned && filtered.length > 0 && (
        <div className="canned">
          <div className="ch">
            <span>Balasan cepat</span>
            <span>↑↓ pilih · Enter sisip · Esc tutup</span>
          </div>
          <div className="canned-scroll">
            {filtered.map((c, i) => (
              <button
                key={c.name}
                className={i === hl ? "hl" : ""}
                onMouseEnter={() => setHl(i)}
                onClick={() => pick(c)}
              >
                <div>
                  <span className="slug">/{c.shortcut}</span>
                  <span className="ttl">{c.title}</span>
                </div>
                <div className="bd">{c.message}</div>
              </button>
            ))}
          </div>
          {role === "manager" && (
            <button className="manage" onClick={onManageCanned}>
              <Ic.Edit size={14} />
              Kelola balasan cepat
            </button>
          )}
        </div>
      )}

      <div className="composer-modes">
        <button
          className={"cmode" + (mode === "reply" ? " on-reply" : "")}
          onClick={() => switchMode("reply")}
        >
          <Ic.Reply size={14} />
          Balas
        </button>
        <button
          className={"cmode" + (mode === "note" ? " on-note" : "")}
          onClick={() => switchMode("note")}
        >
          <Ic.Lock size={14} />
          Catatan internal
        </button>
      </div>

      {isNote && (
        <div className="note-flag">
          <Ic.Eye size={14} />
          <span>
            Mode catatan internal — pesan ini <b>tidak akan terkirim ke pelanggan</b>, hanya
            terlihat oleh agen.
          </span>
        </div>
      )}
      {aiErr && (
        <div className="ai-fail">
          <Ic.AlertCircle size={14} />
          <span>Fitur AI belum aktif / koneksi gagal — cek Settingan AI. Anda tetap bisa menulis manual.</span>
          <button className="rt" onClick={suggest}>
            Coba lagi
          </button>
        </div>
      )}
      {uploadErr && (
        <div className="ai-fail">
          <Ic.AlertCircle size={14} />
          <span>Gagal mengunggah lampiran. Coba lagi.</span>
          <button className="rt" onClick={() => setUploadErr(false)}>
            Tutup
          </button>
        </div>
      )}

      <div className={"composer-inner" + (focus ? " focus" : "")}>
        <textarea
          ref={ta}
          rows={1}
          value={val}
          placeholder={
            isNote
              ? "Tulis catatan internal untuk tim…"
              : `Balas via ${channelName}…  ketik / untuk balasan cepat`
          }
          onChange={onChange}
          onKeyDown={onKey}
          onFocus={() => setFocus(true)}
          onBlur={() => setFocus(false)}
        />
        <div className="composer-bar">
          <input
            ref={imageInput}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) => onPickFile(e, "Image")}
          />
          <input
            ref={fileInput}
            type="file"
            style={{ display: "none" }}
            onChange={(e) => onPickFile(e, "File")}
          />
          <button
            className="tool"
            title="Lampirkan gambar"
            disabled={uploading}
            onClick={() => imageInput.current?.click()}
          >
            {uploading ? (
              <span className="spin">
                <Ic.Loader size={18} />
              </span>
            ) : (
              <Ic.Image size={18} />
            )}
          </button>
          <button
            className="tool"
            title="Lampirkan file"
            disabled={uploading}
            onClick={() => fileInput.current?.click()}
          >
            <Ic.Paperclip size={18} />
          </button>
          <button className="tool" title="Emoji">
            <Ic.Smile size={18} />
          </button>
          {docEnabled && (
            <button className="tool" title="Kirim dokumen" onClick={onOpenDocPicker}>
              <Ic.File size={18} />
            </button>
          )}
          {!isNote && aiEnabled && (
            <button
              className="ai-btn"
              onClick={suggest}
              disabled={aiBusy}
              title="Sarankan balasan dengan AI"
            >
              {aiBusy ? (
                <>
                  <span className="spin">
                    <Ic.Loader size={14} />
                  </span>
                  Menyusun…
                </>
              ) : (
                <>
                  <Ic.Sparkles size={14} />
                  Sarankan balasan
                </>
              )}
            </button>
          )}
          {aiDraft && !aiBusy && (
            <span className="ai-draft-flag">
              <Ic.Sparkles size={12} />
              Draft AI — edit dulu sebelum kirim
            </span>
          )}
          <span className="spacer" />
          <button
            className={"send-btn" + (isNote ? " note" : "")}
            disabled={sendDisabled}
            onClick={send}
          >
            {isNote ? (
              <>
                Simpan catatan <Ic.Lock size={15} />
              </>
            ) : (
              <>
                Kirim <Ic.Send size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
