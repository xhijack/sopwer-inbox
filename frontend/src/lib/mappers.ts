import type { InboxMessage, MessageVM, AgentVM } from "@/types";
import {
  hhmm,
  deliveryToUI,
  messageTypeToUI,
  initials,
  avatarColor,
} from "@/lib/format";

/** Map a raw Inbox Message doc to the bubble view-model. */
export function messageToVM(m: InboxMessage): MessageVM {
  const dir = m.direction === "Outgoing" ? "out" : "in";
  const type = m.is_internal ? "note" : messageTypeToUI(m.message_type);
  const time = hhmm(m.message_timestamp || m.creation);

  const vm: MessageVM = {
    id: m.name,
    dir,
    type,
    time,
    agent: dir === "out" && m.sender_user ? m.sender_user : undefined,
  };

  if (dir === "out" && !m.is_internal) {
    vm.status = deliveryToUI(m.delivery_status);
  }

  if (type === "text" || type === "note") {
    vm.text = m.content || "";
  } else {
    // media types: content acts as caption, media_file is the URL/path
    vm.caption = m.content || undefined;
    const url = m.media_file || undefined;
    const fname = url ? url.split("/").pop() : undefined;
    vm.media = {
      url,
      name: fname,
      label: m.content || fname,
    };
  }

  return vm;
}

/** Build a lightweight agent VM from a user id. */
export function agentVM(userId: string, fullName?: string): AgentVM {
  const name = fullName || userId;
  return {
    id: userId,
    name,
    initials: initials(name),
    color: avatarColor(name),
  };
}
