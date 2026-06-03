import { useFrappeGetCall } from "frappe-react-sdk";
import type { ContactContext } from "@/types";

/** Wraps sopwer_inbox.api.context.get_contact_context. */
export function useContactContext(conversation: string | null) {
  const { data, isLoading, error, mutate } = useFrappeGetCall<{
    message: ContactContext;
  }>(
    "sopwer_inbox.api.context.get_contact_context",
    conversation ? { conversation } : undefined,
    conversation ? `ctx:${conversation}` : null,
    { revalidateOnFocus: false },
  );

  return { context: data?.message ?? null, isLoading, error, mutate };
}
