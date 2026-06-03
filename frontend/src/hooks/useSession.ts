import { useMemo } from "react";

interface FrappeBoot {
  user?: {
    name?: string;
    full_name?: string;
    roles?: string[];
  };
  sysdefaults?: Record<string, unknown>;
}

declare global {
  interface Window {
    frappe?: { boot?: FrappeBoot };
    csrf_token?: string;
    dev_server?: number | string;
    socketio_port?: number | string;
  }
}

export type Role = "agent" | "manager";

/**
 * Reads role + identity from frappe.boot. Falls back to "manager" in dev
 * (no boot available) so all manager surfaces are reachable while building.
 */
export function useSession() {
  return useMemo(() => {
    const boot = window.frappe?.boot;
    const user = boot?.user;
    const roles: string[] = user?.roles || [];
    const isManager = roles.includes("Inbox Manager") || roles.includes("System Manager");
    const isAgent = isManager || roles.includes("Inbox Agent");

    // In dev (no boot) default to manager so all surfaces render.
    const hasBoot = !!boot;
    const role: Role = !hasBoot ? "manager" : isManager ? "manager" : "agent";

    return {
      userId: user?.name || "Administrator",
      fullName: user?.full_name || user?.name || "Pengguna",
      role,
      isManager: !hasBoot ? true : isManager,
      isAgent: !hasBoot ? true : isAgent,
    };
  }, []);
}
