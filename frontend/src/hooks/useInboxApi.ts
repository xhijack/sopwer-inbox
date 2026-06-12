import { useFrappePostCall } from "frappe-react-sdk";
import type { ConvStatus, MessageType } from "@/types";
import type { AIConfig } from "@/components/Modals";

const M = "sopwer_inbox.api.conversation";
const D = "sopwer_inbox.api.document";
const A = "sopwer_inbox.api.ai";

// Backend stores the provider capitalised; the UI uses a lowercase union.
const PROV_TO_API: Record<AIConfig["provider"], string> = {
  ollama: "Ollama",
  claude: "Claude",
  openai: "OpenAI",
};
function provFromApi(p: string): AIConfig["provider"] {
  const l = (p || "").toLowerCase();
  return l === "claude" || l === "openai" ? l : "ollama";
}

/** Typed wrappers over the whitelisted conversation methods. */
export function useInboxApi() {
  const { call: sendCall } = useFrappePostCall(`${M}.send_message`);
  const { call: noteCall } = useFrappePostCall(`${M}.add_internal_note`);
  const { call: statusCall } = useFrappePostCall(`${M}.set_status`);
  const { call: assignCall } = useFrappePostCall(`${M}.assign`);
  const { call: readCall } = useFrappePostCall(`${M}.mark_read`);
  const { call: retryCall } = useFrappePostCall(`${M}.retry_message`);
  const { call: sendDocCall } = useFrappePostCall(`${D}.send_document`);
  const { call: suggestCall } = useFrappePostCall(`${A}.suggest_reply`);
  const { call: getAiCall } = useFrappePostCall(`${A}.get_ai_settings`);
  const { call: saveAiCall } = useFrappePostCall(`${A}.save_ai_settings`);
  const { call: testAiCall } = useFrappePostCall(`${A}.test_ai_connection`);

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
    sendDocument: (conversation: string, doctype: string, name: string) =>
      sendDocCall({ conversation, doctype, name }),

    // -- AI agent-assist --------------------------------------------------
    /** Draft a reply for the conversation. Resolves to the draft string. */
    suggestReply: async (conversation: string): Promise<string> => {
      const res = await suggestCall({ conversation });
      return (res?.message?.draft as string) ?? "";
    },
    /** Load AI settings as an AIConfig (apiKey is never returned by the server). */
    getAiSettings: async (): Promise<AIConfig> => {
      const res = await getAiCall({});
      const m = res?.message ?? {};
      return {
        enabled: !!m.enabled,
        provider: provFromApi(m.provider),
        endpoint: m.endpoint ?? "",
        model: m.model ?? "",
        apiKey: "",
      };
    },
    /** Persist AI settings. A blank apiKey leaves the stored key untouched. */
    saveAiSettings: (ai: AIConfig) =>
      saveAiCall({
        enabled: ai.enabled ? 1 : 0,
        provider: PROV_TO_API[ai.provider],
        endpoint: ai.endpoint,
        model: ai.model,
        api_key: ai.apiKey || "",
      }),
    /** Ping the provider with the given (possibly unsaved) config. Rejects on failure. */
    testAi: (ai: AIConfig) =>
      testAiCall({
        provider: PROV_TO_API[ai.provider],
        endpoint: ai.endpoint,
        model: ai.model,
        api_key: ai.apiKey || "",
      }),
  };
}
