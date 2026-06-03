/* Sopwer Inbox — inline SVG icons (Lucide-style, 2px stroke, currentColor) */
const Ic = {};
const mk = (paths, vb = 24) => ({ size = 18, ...p } = {}) => (
  <svg width={size} height={size} viewBox={`0 0 ${vb} ${vb}`} fill="none"
       stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}>
    {paths}
  </svg>
);

Ic.Inbox    = mk(<><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></>);
Ic.Clock    = mk(<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>);
Ic.Check    = mk(<path d="M20 6 9 17l-5-5"/>);
Ic.CheckCheck = mk(<><path d="M18 6 7 17l-5-5"/><path d="m22 10-7.5 7.5L13 16"/></>);
Ic.CheckCircle = mk(<><circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/></>);
Ic.Search   = mk(<><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></>);
Ic.Send     = mk(<><path d="M14.5 12 4 12"/><path d="M21 12 4.5 4.5 8 12l-3.5 7.5L21 12z"/></>);
Ic.Paperclip= mk(<path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>);
Ic.Image    = mk(<><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21"/></>);
Ic.File     = mk(<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></>);
Ic.Download = mk(<><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></>);
Ic.Play     = mk(<path d="M6 4l14 8-14 8z" fill="currentColor" stroke="none"/>);
Ic.Mic      = mk(<><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><path d="M12 19v3"/></>);
Ic.AlertTriangle = mk(<><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></>);
Ic.AlertCircle = mk(<><circle cx="12" cy="12" r="9"/><path d="M12 8v4"/><path d="M12 16h.01"/></>);
Ic.RefreshCw= mk(<><path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/></>);
Ic.X        = mk(<path d="M18 6 6 18M6 6l12 12"/>);
Ic.ChevronDown = mk(<path d="m6 9 6 6 6-6"/>);
Ic.ChevronRight = mk(<path d="m9 6 6 6-6 6"/>);
Ic.PanelRight = mk(<><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M15 3v18"/></>);
Ic.User     = mk(<><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>);
Ic.UserCheck= mk(<><circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 13-3.5"/><path d="m16 11 2 2 4-4"/></>);
Ic.Users    = mk(<><circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 13-3"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 20a7 7 0 0 0-3-5"/></>);
Ic.Smile    = mk(<><circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><path d="M9 9h.01M15 9h.01"/></>);
Ic.Filter   = mk(<path d="M22 3H2l8 9.46V19l4 2v-8.54z"/>);
Ic.Settings = mk(<><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></>);
Ic.Tag      = mk(<><path d="M20 13.3 13.3 20a1.7 1.7 0 0 1-2.4 0l-7-7V4h9l7.1 7a1.7 1.7 0 0 1 0 2.3z"/><path d="M7.5 7.5h.01"/></>);
Ic.MessageOff = mk(<><path d="M8.5 3H20a2 2 0 0 1 2 2v8.5"/><path d="M20.5 17H8l-4 4V5"/><path d="m2 2 20 20"/></>);
Ic.PhoneOff = mk(<><path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67m-2.67-3.34a19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91"/><path d="m2 2 20 20"/></>);

Ic.Sparkles = mk(<><path d="M12 3l1.8 4.8L18.5 9.5 13.8 11.3 12 16l-1.8-4.7L5.5 9.5l4.7-1.7L12 3z"/><path d="M19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14z"/></>);
Ic.Lock     = mk(<><rect x="4.5" y="11" width="15" height="9" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></>);
Ic.Eye      = mk(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></>);
Ic.Note     = mk(<><path d="M15 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M15 3v5h5"/><path d="M8 13h5M8 17h6"/></>);
Ic.Reply    = mk(<><path d="M9 17l-5-5 5-5"/><path d="M4 12h11a5 5 0 0 1 5 5v1"/></>);
Ic.Plus     = mk(<path d="M12 5v14M5 12h14"/>);
Ic.Edit     = mk(<><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></>);
Ic.Trash    = mk(<><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></>);
Ic.Server   = mk(<><rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/></>);
Ic.Cloud    = mk(<path d="M17.5 19a4.5 4.5 0 0 0 .5-9 6 6 0 0 0-11.6-1.5A4 4 0 0 0 6.5 19h11z"/>);
Ic.Bell     = mk(<><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9z"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></>);
Ic.MapPin   = mk(<><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/></>);
Ic.Video    = mk(<><rect x="2" y="6" width="14" height="12" rx="2"/><path d="M16 10l6-3v10l-6-3z"/></>);
Ic.SlidersH = mk(<><path d="M3 6h12M19 6h2M3 12h4M11 12h10M3 18h8M15 18h6"/><circle cx="17" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="13" cy="18" r="2"/></>);
Ic.MessageSquare = mk(<path d="M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z"/>);
Ic.ChevronUp = mk(<path d="m6 15 6-6 6 6"/>);
Ic.Loader   = mk(<><path d="M12 3v4M12 17v4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M3 12h4M17 12h4M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></>);
Ic.Wifi     = mk(<><path d="M5 12.5a10 10 0 0 1 14 0"/><path d="M8.5 16a5 5 0 0 1 7 0"/><path d="M12 19.5h.01"/></>);

// Channel glyphs (filled, brand-recognizable silhouettes)
Ic.WaGlyph = ({ size = 11 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2a10 10 0 0 0-8.5 15.2L2 22l4.9-1.5A10 10 0 1 0 12 2zm0 2a8 8 0 0 1 0 16 7.9 7.9 0 0 1-4.1-1.1l-.3-.2-2.4.7.7-2.3-.2-.3A8 8 0 0 1 12 4zm-2.6 4c-.2 0-.5 0-.7.4-.2.4-.9.9-.9 2.1s.9 2.4 1 2.6c.1.2 1.7 2.8 4.3 3.7 2.1.8 2.5.6 3 .6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2-.1-.1-.3-.2-.6-.3l-1.4-.7c-.2-.1-.4-.1-.5.1l-.6.8c-.1.2-.3.2-.5.1-.7-.3-1.3-.5-1.9-1.2-.5-.5-.8-1.1-.9-1.3-.1-.2 0-.3.1-.4l.4-.5c.1-.2.1-.3.2-.5 0-.2 0-.3 0-.4l-.7-1.6c-.2-.5-.4-.4-.5-.4z"/>
  </svg>
);
Ic.TgGlyph = ({ size = 11 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M21.9 4.3 18.7 19.4c-.2 1-.9 1.3-1.7.8l-4.6-3.4-2.2 2.1c-.2.3-.5.5-.9.5l.3-4.6 8.4-7.6c.4-.3-.1-.5-.6-.2L7.3 13.1l-4.5-1.4c-1-.3-1-1 .2-1.5l17.6-6.8c.8-.3 1.5.2 1.3 1z"/>
  </svg>
);

window.Ic = Ic;
