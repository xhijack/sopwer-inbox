/* Sopwer Inbox icons — Lucide (design-system mandated) + custom channel glyphs. */
import {
  Inbox,
  Clock,
  Check,
  CheckCheck,
  CheckCircle2,
  Search,
  Send,
  Paperclip,
  Image,
  File,
  Download,
  Play,
  Mic,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  X,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  ChevronLeft,
  PanelRight,
  PanelLeft,
  PanelLeftClose,
  Menu,
  User,
  UserCheck,
  Users,
  Smile,
  Settings,
  Tag,
  PhoneOff,
  Sparkles,
  Lock,
  Eye,
  Reply,
  Plus,
  Pencil,
  Trash2,
  Server,
  Cloud,
  Bell,
  MapPin,
  Video,
  SlidersHorizontal,
  MessageSquare,
  Loader2,
  Wifi,
  Volume2,
  VolumeX,
} from "lucide-react";

export const Ic = {
  Inbox,
  Clock,
  Check,
  CheckCheck,
  CheckCircle: CheckCircle2,
  Search,
  Send,
  Paperclip,
  Image,
  File,
  Download,
  Play,
  Mic,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  X,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  ChevronLeft,
  PanelRight,
  PanelLeft,
  PanelLeftClose,
  Menu,
  User,
  UserCheck,
  Users,
  Smile,
  Settings,
  Tag,
  PhoneOff,
  Sparkles,
  Lock,
  Eye,
  Reply,
  Plus,
  Edit: Pencil,
  Trash: Trash2,
  Server,
  Cloud,
  Bell,
  MapPin,
  Video,
  SlidersH: SlidersHorizontal,
  MessageSquare,
  Loader: Loader2,
  Wifi,
  Volume2,
  VolumeX,
};

export function WaGlyph({ size = 11 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2a10 10 0 0 0-8.5 15.2L2 22l4.9-1.5A10 10 0 1 0 12 2zm0 2a8 8 0 0 1 0 16 7.9 7.9 0 0 1-4.1-1.1l-.3-.2-2.4.7.7-2.3-.2-.3A8 8 0 0 1 12 4zm-2.6 4c-.2 0-.5 0-.7.4-.2.4-.9.9-.9 2.1s.9 2.4 1 2.6c.1.2 1.7 2.8 4.3 3.7 2.1.8 2.5.6 3 .6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2-.1-.1-.3-.2-.6-.3l-1.4-.7c-.2-.1-.4-.1-.5.1l-.6.8c-.1.2-.3.2-.5.1-.7-.3-1.3-.5-1.9-1.2-.5-.5-.8-1.1-.9-1.3-.1-.2 0-.3.1-.4l.4-.5c.1-.2.1-.3.2-.5 0-.2 0-.3 0-.4l-.7-1.6c-.2-.5-.4-.4-.5-.4z" />
    </svg>
  );
}

export function TgGlyph({ size = 11 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M21.9 4.3 18.7 19.4c-.2 1-.9 1.3-1.7.8l-4.6-3.4-2.2 2.1c-.2.3-.5.5-.9.5l.3-4.6 8.4-7.6c.4-.3-.1-.5-.6-.2L7.3 13.1l-4.5-1.4c-1-.3-1-1 .2-1.5l17.6-6.8c.8-.3 1.5.2 1.3 1z" />
    </svg>
  );
}

export function ChannelGlyph({ ch, size }: { ch: "wa" | "tg"; size?: number }) {
  return ch === "wa" ? <WaGlyph size={size} /> : <TgGlyph size={size} />;
}
