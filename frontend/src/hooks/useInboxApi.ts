import { useFrappePostCall } from "frappe-react-sdk";
import type { ConvStatus, MessageType } from "@/types";

const M = "sopwer_inbox.api.conversation";

/** Typed wrappers over the whitelisted conversation methods. */
export function useInboxApi() {
  const { call: sendCall } = useFrappePostCall(`${M}.send_message`);
  const { call: noteCall } = useFrappePostCall(`${M}.add_internal_note`);
  const { call: statusCall } = useFrappePostCall(`${M}.set_status`);
  const { call: assignCall } = useFrappePostCall(`${M}.assign`);
  const { call: readCall } = useFrappePostCall(`${M}.mark_read`);
  const { call: retryCall } = useFrappePostCall(`${M}.retry_message`);

  return {
    sendMessage: (args: {
      conversation: string;
      text: string;
      message_type?: MessageType;
      media_path?: string | null;
      is_internal?: 0 | 1;
    }) =>
      sendCall({
        conversation: args.conversation,
        text: args.text,
        message_type: args.message_type || "Text",
        media_path: args.media_path ?? null,
        is_internal: args.is_internal ?? 0,
      }),
    addInternalNote: (conversation: string, text: string) =>
      noteCall({ conversation, text }),
    setStatus: (conversation: string, status: ConvStatus) =>
      statusCall({ conversation, status }),
    assign: (conversation: string, user: string | null) =>
      assignCall({ conversation, user }),
    markRead: (conversation: string) => readCall({ conversation }),
    retryMessage: (message: string) => retryCall({ message }),
  };
}
