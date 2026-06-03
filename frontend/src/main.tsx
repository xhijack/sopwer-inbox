import React from "react";
import ReactDOM from "react-dom/client";
import { FrappeProvider } from "frappe-react-sdk";
import { InboxApp } from "./InboxApp";
import "./styles/index.css";

declare global {
  interface Window {
    csrf_token?: string;
    socketio_port?: number | string;
  }
}

const siteName = import.meta.env.VITE_SITE_NAME;
const socketPort = window.socketio_port ? String(window.socketio_port) : "9000";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <FrappeProvider
      url=""
      socketPort={socketPort}
      siteName={siteName}
      enableSocket
      swrConfig={{
        revalidateOnFocus: false,
        shouldRetryOnError: false,
      }}
    >
      <InboxApp />
    </FrappeProvider>
  </React.StrictMode>,
);
