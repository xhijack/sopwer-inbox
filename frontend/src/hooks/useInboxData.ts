import { useMemo } from "react";
import { useFrappeGetDocList } from "frappe-react-sdk";
import type {
  InboxChannel,
  InboxConversation,
  InboxMessage,
  InboxCannedResponse,
  ChannelVM,
  ConversationVM,
  AgentVM,
} from "@/types";
import {
  avatarColor,
  initials,
  toUIStatus,
  channelTypeToUI,
  relativeTime,
  parseTags,
} from "@/lib/format";

interface UserDoc {
  name: string;
  full_name: string;
}

/** Enabled users available for assignment, decorated as AgentVM. */
export function useAgents() {
  const { data } = useFrappeGetDocList<UserDoc>("User", {
    fields: ["name", "full_name"],
    filters: [
      ["enabled", "=", 1],
      ["user_type", "=", "System User"],
      ["name", "not in", ["Administrator", "Guest"]],
    ],
    limit: 0,
  });

  const agents = useMemo<Record<string, AgentVM>>(() => {
    const map: Record<string, AgentVM> = {};
    (data || []).forEach((u) => {
      const name = u.full_name || u.name;
      map[u.name] = {
        id: u.name,
        name,
        initials: initials(name),
        color: avatarColor(name),
      };
    });
    return map;
  }, [data]);

  return { agents };
}

/** All channels, decorated for the UI sidebar/labels. */
export function useChannels() {
  const { data, isLoading, error } = useFrappeGetDocList<InboxChannel>(
    "Inbox Channel",
    {
      fields: ["name", "channel_name", "channel_type", "enabled"],
      limit: 0,
    },
  );

  const channels = useMemo<Record<string, ChannelVM>>(() => {
    const map: Record<string, ChannelVM> = {};
    (data || []).forEach((c) => {
      map[c.name] = {
        id: c.name,
        type: channelTypeToUI(c.channel_type),
        name: c.channel_name || c.name,
        addr: "",
      };
    });
    return map;
  }, [data]);

  return { channels, isLoading, error };
}

/** Canned responses (live, manager-editable). */
export function useCanned() {
  const { data, isLoading, mutate } = useFrappeGetDocList<InboxCannedResponse>(
    "Inbox Canned Response",
    {
      fields: ["name", "title", "shortcut", "message"],
      limit: 0,
    },
  );
  return { canned: data || [], isLoading, mutate };
}

/** Conversation list, decorated into ConversationVM[]. */
export function useConversations() {
  const { data, isLoading, error, mutate } =
    useFrappeGetDocList<InboxConversation>("Inbox Conversation", {
      fields: [
        "name",
        "contact",
        "channel",
        "subject",
        "status",
        "assigned_to",
        "last_message_at",
        "last_message_preview",
        "unread_count",
        "tags",
      ],
      orderBy: { field: "last_message_at", order: "desc" },
      limit: 0,
    });

  const conversations = useMemo<ConversationVM[]>(
    () =>
      (data || []).map((c) => {
        const name = c.subject || c.contact || c.name;
        return {
          id: c.name,
          contact: {
            name,
            handle: c.contact || c.external_conversation_id || "",
            initials: initials(name),
            color: avatarColor(name),
          },
          channelId: c.channel || "",
          status: toUIStatus(c.status),
          assignee: c.assigned_to || null,
          unread: c.unread_count || 0,
          lastTime: relativeTime(c.last_message_at),
          lastAt: c.last_message_at,
          tags: parseTags(c.tags),
          preview: c.last_message_preview || "",
        };
      }),
    [data],
  );

  return { conversations, raw: data || [], isLoading, error, mutate };
}

/** Messages for a single conversation. */
export function useMessages(conversation: string | null) {
  const { data, isLoading, mutate } = useFrappeGetDocList<InboxMessage>(
    "Inbox Message",
    {
      fields: [
        "name",
        "conversation",
        "direction",
        "sender_type",
        "sender_user",
        "is_internal",
        "message_type",
        "content",
        "media_file",
        "external_message_id",
        "delivery_status",
        "message_timestamp",
        "creation",
      ],
      filters: conversation ? [["conversation", "=", conversation]] : [["name", "=", "__none__"]],
      orderBy: { field: "message_timestamp", order: "asc" },
      limit: 0,
    },
    conversation ? `messages:${conversation}` : null,
  );

  return { messages: data || [], isLoading, mutate };
}
