import type {
  ConvStatus,
  UIStatus,
  ChannelType,
  DeliveryStatus,
  MessageType,
  MessageVM,
} from "@/types";

const AVATAR_PALETTE = [
  "var(--sw-blue-600)",
  "var(--sw-green-600)",
  "var(--sw-yellow-700)",
  "var(--sw-blue-500)",
  "var(--sw-ink-500)",
  "var(--sw-green-500)",
];

/** Deterministic avatar color from a name string. */
export function avatarColor(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return AVATAR_PALETTE[h % AVATAR_PALETTE.length];
}

/** Up to two-letter initials. */
export function initials(name: string): string {
  const parts = (name || "?").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function toUIStatus(s: ConvStatus | undefined | null): UIStatus {
  switch (s) {
    case "Pending":
      return "pending";
    case "Resolved":
      return "resolved";
    default:
      return "open";
  }
}

export function toApiStatus(s: UIStatus): ConvStatus {
  switch (s) {
    case "pending":
      return "Pending";
    case "resolved":
      return "Resolved";
    default:
      return "Open";
  }
}

export function channelTypeToUI(t: ChannelType | undefined): "wa" | "tg" {
  return t === "WhatsApp" ? "wa" : "tg";
}

export function deliveryToUI(
  d: DeliveryStatus | null | undefined,
): MessageVM["status"] {
  switch (d) {
    case "Sent":
      return "sent";
    case "Delivered":
      return "delivered";
    case "Read":
      return "read";
    case "Failed":
      return "failed";
    default:
      return "pending";
  }
}

export function messageTypeToUI(t: MessageType): MessageVM["type"] {
  switch (t) {
    case "Image":
      return "image";
    case "Video":
      return "video";
    case "File":
      return "file";
    case "Audio":
      return "audio";
    case "Location":
      return "location";
    default:
      return "text";
  }
}

/** Format an ISO timestamp to HH:MM (local). */
export function hhmm(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d.getTime())) return "";
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** Relative "5m" / "2j" / "Kemarin" label for the conversation list. */
export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d.getTime())) return "";
  const diff = Date.now() - d.getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "baru";
  if (min < 60) return `${min}m`;
  const jam = Math.floor(min / 60);
  if (jam < 24) return `${jam}j`;
  const hari = Math.floor(jam / 24);
  if (hari === 1) return "Kemarin";
  if (hari < 7) return `${hari} hari`;
  return d.toLocaleDateString("id-ID", { day: "2-digit", month: "short" });
}

/** Tag chip CSS modifier. */
export function tagClass(t: string): string {
  const s = t.toLowerCase();
  if (s === "vip") return "vip";
  if (s === "komplain") return "komplain";
  return "";
}

/** Parse a conversation `tags` field (comma list or JSON) into a string[]. */
export function parseTags(raw: string | null | undefined): string[] {
  if (!raw) return [];
  const trimmed = raw.trim();
  if (trimmed.startsWith("[")) {
    try {
      const arr = JSON.parse(trimmed);
      if (Array.isArray(arr)) return arr.map(String).filter(Boolean);
    } catch {
      /* fall through */
    }
  }
  return trimmed
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

export function serializeTags(tags: string[]): string {
  return tags.join(", ");
}

/** Format a numeric amount as Rupiah. */
export function rupiah(amount: number | undefined, currency = "Rp"): string {
  if (amount == null) return "—";
  return `${currency} ${amount.toLocaleString("id-ID")}`;
}
