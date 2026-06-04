/* Typed API contract for the Sopwer Inbox backend. */

export type ConvStatus = "Open" | "Pending" | "Resolved";
export type UIStatus = "open" | "pending" | "resolved";
export type ChannelType = "Telegram" | "WhatsApp" | "Facebook Messenger" | "Instagram";
export type Direction = "Incoming" | "Outgoing";
export type MessageType = "Text" | "Image" | "File" | "Audio" | "Video" | "Location";
export type DeliveryStatus = "Pending" | "Sent" | "Delivered" | "Read" | "Failed";

/** Raw `Inbox Conversation` doc fields (subset used by the UI). */
export interface InboxConversation {
  name: string;
  contact: string | null;
  channel: string | null;
  external_conversation_id?: string;
  subject?: string;
  status: ConvStatus;
  assigned_to: string | null;
  last_message_at: string | null;
  last_message_preview: string | null;
  unread_count: number;
  tags?: string | null;
}

/** Raw `Inbox Message` doc fields. */
export interface InboxMessage {
  name: string;
  conversation: string;
  direction: Direction;
  sender_type?: string;
  sender_user?: string | null;
  is_internal: 0 | 1;
  message_type: MessageType;
  content: string | null;
  media_file: string | null;
  external_message_id?: string | null;
  delivery_status: DeliveryStatus | null;
  message_timestamp: string | null;
  creation?: string;
}

/** Raw `Inbox Channel` doc fields. */
export interface InboxChannel {
  name: string;
  channel_name: string;
  channel_type: ChannelType;
  enabled: 0 | 1;
}

/** Raw `Inbox Canned Response` doc fields. */
export interface InboxCannedResponse {
  name: string;
  title: string;
  shortcut: string;
  message: string;
}

/** get_contact_context() response. */
export interface ContactContext {
  contact: {
    name: string;
    full_name?: string;
    first_name?: string;
    phone?: string | null;
    inbox_notes?: string | null;
  } | null;
  previous_conversations: PreviousConversation[];
  erp: ErpContext | null;
}

export interface PreviousConversation {
  name: string;
  channel?: string | null;
  status?: ConvStatus;
  last_message_at?: string | null;
  last_message_preview?: string | null;
}

export interface ErpContext {
  customer: string;
  sales_orders: ErpDoc[];
  invoices: ErpDoc[];
}

export interface ErpDoc {
  name: string;
  grand_total?: number;
  status?: string;
  transaction_date?: string;
  posting_date?: string;
  currency?: string;
}

/** check_channel_health() response. */
export interface ChannelHealth {
  ok: boolean;
  status: string;
  [k: string]: unknown;
}

/** Realtime: inbox:new_message */
export interface NewMessageEvent {
  conversation: string;
  channel: string;
  message: string;
  direction: Direction;
  is_internal: 0 | 1;
}

/** Realtime: inbox:conversation_updated */
export interface ConversationUpdatedEvent {
  conversation: string;
  status: ConvStatus;
  assigned_to: string | null;
  unread_count: number;
}

/* ── UI view models (decorated from raw docs) ── */

export interface AgentVM {
  id: string;
  name: string;
  initials: string;
  color: string;
}

export interface MediaVM {
  url?: string;
  name?: string;
  size?: string;
  label?: string;
  dur?: string;
}

export interface MessageVM {
  id: string;
  dir: "in" | "out";
  type: "text" | "note" | "image" | "video" | "file" | "audio" | "location";
  text?: string;
  caption?: string;
  media?: MediaVM;
  time: string;
  status?: "pending" | "sent" | "delivered" | "read" | "failed";
  agent?: string;
  /** transient client-only optimistic flag */
  optimistic?: boolean;
}

export interface ChannelVM {
  id: string;
  type: "wa" | "tg" | "ig" | "fb";
  name: string;
  addr: string;
}

export interface ConversationVM {
  id: string;
  contact: { name: string; handle: string; initials: string; color: string };
  channelId: string;
  status: UIStatus;
  assignee: string | null;
  unread: number;
  lastTime: string;
  lastAt: string | null;
  tags: string[];
  preview: string;
}

export interface SendableDocument {
  name: string;
  date?: string;
  grand_total?: number;
  status?: string;
  currency?: string;
  doctype?: string;
}
