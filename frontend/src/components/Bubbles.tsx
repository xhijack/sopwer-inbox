import { Ic } from "./icons";
import type { AgentVM, MediaVM, MessageVM } from "@/types";

export function DeliveryTick({ status }: { status: MessageVM["status"] }) {
  if (status === "pending")
    return (
      <span className="tick pending" title="Mengirim…">
        <Ic.Clock size={13} />
      </span>
    );
  if (status === "sent")
    return (
      <span className="tick sent" title="Terkirim">
        <Ic.Check size={15} />
      </span>
    );
  if (status === "delivered")
    return (
      <span className="tick delivered" title="Tersampaikan">
        <Ic.CheckCheck size={15} />
      </span>
    );
  if (status === "read")
    return (
      <span className="tick read" title="Dibaca">
        <Ic.CheckCheck size={15} />
      </span>
    );
  return null;
}

function MediaImage({ media }: { media: MediaVM }) {
  if (media.url) {
    return (
      <div className="media-img" style={{ maxWidth: 260 }}>
        <img src={media.url} alt={media.name || "gambar"} style={{ width: "100%", display: "block" }} />
      </div>
    );
  }
  return (
    <div className="media-img" style={{ width: 220, maxWidth: "100%" }}>
      <div
        className="ph"
        style={{ height: 200, background: "linear-gradient(135deg, var(--sw-blue-400), var(--sw-blue-600))" }}
      >
        <Ic.Image size={30} style={{ opacity: 0.7 }} />
      </div>
    </div>
  );
}

function MediaVideo({ media }: { media: MediaVM }) {
  if (media.url) {
    return (
      <div className="media-video" style={{ maxWidth: 280 }}>
        <video src={media.url} controls style={{ width: "100%", display: "block" }} />
      </div>
    );
  }
  return (
    <div className="media-video" style={{ width: 240, maxWidth: "100%" }}>
      <div
        className="pv"
        style={{ height: 150, background: "linear-gradient(135deg, var(--sw-blue-500), var(--sw-ink-700))" }}
      >
        <Ic.Video size={30} style={{ opacity: 0.6 }} />
      </div>
      <div className="pl">
        <span>
          <Ic.Play size={16} />
        </span>
      </div>
      {media.dur && <span className="dur">{media.dur}</span>}
    </div>
  );
}

function MediaLocation({ media }: { media: MediaVM }) {
  return (
    <div className="media-loc">
      <div className="map">
        <span className="pin">
          <Ic.MapPin size={26} />
        </span>
      </div>
      <div className="lc">
        <Ic.MapPin size={16} style={{ color: "var(--sw-error)", flexShrink: 0 }} />
        <div style={{ minWidth: 0 }}>
          <div className="nm">{media.label || "Lokasi"}</div>
          <div className="sub">Lokasi dibagikan</div>
        </div>
      </div>
    </div>
  );
}

function MediaFile({ media }: { media: MediaVM }) {
  return (
    <a
      className="media-file"
      href={media.url || "#"}
      target="_blank"
      rel="noreferrer"
      style={{ textDecoration: "none" }}
      onClick={(e) => {
        if (!media.url) e.preventDefault();
      }}
    >
      <div className="fic">
        <Ic.File size={18} />
      </div>
      <div style={{ minWidth: 0 }}>
        <div className="fn">{media.name || "Lampiran"}</div>
        <div className="fs">{media.size || "File"}</div>
      </div>
      <span className="dl" title="Unduh">
        <Ic.Download size={17} />
      </span>
    </a>
  );
}

function MediaAudio({ media }: { media: MediaVM }) {
  if (media.url) {
    return (
      <div className="media-audio">
        <audio src={media.url} controls style={{ width: 230 }} />
      </div>
    );
  }
  return (
    <div className="media-audio">
      <button className="play">
        <Ic.Play size={14} />
      </button>
      <div className="wave">
        {[10, 16, 8, 20, 13, 18, 7, 15, 22, 11, 17, 9, 14, 19, 12, 8, 16, 10].map((h, i) => (
          <i key={i} style={{ height: h }} />
        ))}
      </div>
      {media.dur && <span className="dur">{media.dur}</span>}
    </div>
  );
}

export function NoteCard({ m, agent }: { m: MessageVM; agent?: AgentVM }) {
  return (
    <div className="note-row">
      <div className="note-card">
        <div className="nh">
          <Ic.Lock size={12} /> Catatan internal{" "}
          <span className="who">{agent ? agent.name : ""}</span>
        </div>
        <div className="nb">{m.text}</div>
        <div className="nt">{m.time} · tidak terkirim ke pelanggan</div>
      </div>
    </div>
  );
}

export function Bubble({
  m,
  agent,
  onRetry,
}: {
  m: MessageVM;
  agent?: AgentVM;
  onRetry: (id: string) => void;
}) {
  const isOut = m.dir === "out";
  return (
    <div className={"row " + (isOut ? "out" : "in") + (m.status === "failed" ? " failed" : "")}>
      {isOut && agent && (
        <div className="ava" style={{ background: agent.color }} title={agent.name}>
          {agent.initials}
        </div>
      )}
      <div className="bubble">
        {m.type === "image" && m.media && <MediaImage media={m.media} />}
        {m.type === "video" && m.media && <MediaVideo media={m.media} />}
        {m.type === "location" && m.media && <MediaLocation media={m.media} />}
        {m.type === "file" && m.media && <MediaFile media={m.media} />}
        {m.type === "audio" && m.media && <MediaAudio media={m.media} />}
        {(m.text || m.caption) && (
          <div className="caption-txt" style={{ marginTop: m.type === "text" ? 0 : 5 }}>
            {m.text || m.caption}
          </div>
        )}
        {m.status !== "failed" && (
          <div className="meta">
            <span className="tm">{m.time}</span>
            {isOut && <DeliveryTick status={m.status} />}
          </div>
        )}
        {m.status === "failed" && (
          <div className="fail-line">
            <span className="ft">
              <Ic.AlertCircle size={12} /> Gagal terkirim
            </span>
            <button className="retry" onClick={() => onRetry(m.id)}>
              <Ic.RefreshCw size={11} style={{ verticalAlign: -1 }} /> Coba lagi
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export function ThreadSkeleton() {
  const rows: [string, string][] = [
    ["in", "58%"],
    ["in", "40%"],
    ["out", "52%"],
    ["out", "34%"],
    ["in", "62%"],
    ["out", "46%"],
  ];
  return (
    <div className="msgs">
      {rows.map(([side, w], i) => (
        <div className={"sk-bubble-row " + side} key={i}>
          <div
            className="sk"
            style={{
              height: 42,
              width: w,
              borderRadius: 16,
              borderBottomLeftRadius: side === "in" ? 5 : 16,
              borderBottomRightRadius: side === "out" ? 5 : 16,
            }}
          />
        </div>
      ))}
    </div>
  );
}
