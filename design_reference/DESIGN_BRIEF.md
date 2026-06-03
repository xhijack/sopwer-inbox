# DESIGN_BRIEF.md — sopwer_inbox

> Brief untuk **Claude Design**. Tujuan: merancang antarmuka **inbox customer service omnichannel** yang dipakai agen CS sepanjang hari. Setelah desain di-review & disetujui Ramdani, hasilnya menjadi acuan implementasi React (BUILD_PLAN Phase 6).
>
> Cukup baca dokumen ini saja — tidak perlu PRD/CLAUDE/BUILD_PLAN untuk mendesain.

---

## 1. Konteks produk

Inbox CS omnichannel bergaya **Chatwoot / Intercom / Front**. Agen menangani chat pelanggan dari **Telegram & WhatsApp** dalam satu layar. **Bukan** chat tim internal (bukan Slack/Discord/Raven).

Dipakai berjam-jam tiap hari → prioritas desain: **kecepatan kerja, kepadatan informasi yang nyaman, kejelasan status.** Ini app kerja yang tidak melelahkan mata, bukan app yang "wah".

**Referensi pola (ambil ide, jangan jiplak):** Chatwoot, Intercom, Front, Crisp, Missive.

**Pengguna:** Agen CS (Inbox Agent) dan Supervisor (Inbox Manager). Pelanggan akhir tidak memakai app ini — mereka tetap pakai WhatsApp/Telegram biasa.

---

## 2. Brand & tone

- **Primary blue:** `#1E5BB0`
- **Green (success / online):** `#7AB838`
- **Yellow (accent / warning):** `#F5C518`
- Netral abu-abu untuk background & teks sekunder; putih untuk panel utama.
- **Light mode** utama. Dark mode opsional (ditunda).
- Tone: profesional, bersih, sedikit warm. Bukan korporat dingin.

---

## 3. Arsitektur layar — 3-pane (desktop-first)

```
┌──────────┬─────────────────────────┬──────────────────────────┐
│ SIDEBAR  │   DAFTAR PERCAKAPAN      │   THREAD + COMPOSER       │
│ (filter) │   (conversation list)    │   (+ panel kontak kanan)  │
└──────────┴─────────────────────────┴──────────────────────────┘
```

Panel kontak (kanan) bisa di-collapse. Di layar sempit, 3-pane menjadi stack (list → tap → thread). Pilot fokus desktop, tapi layout tidak boleh mustahil di-mobile-kan nanti.

---

## 4. Pane 1 — Sidebar / filter

- Logo Sopwer kecil di atas.
- **Filter status:** Open / Pending / Resolved (badge jumlah masing-masing).
- **Filter penugasan:** "Assigned to me" vs "All".
- **Filter per kanal individual** — bukan per tipe. Satu klien bisa punya banyak kanal: "WA Toko", "WA CS", "WA Reseller", "Telegram Promo", dst — tiap kanal baris terpisah (ikon tipe + nama), bisa dicentang satu/beberapa. **Jangan desain seolah hanya ada 1 WhatsApp + 1 Telegram.**
- Akses ke **Kelola Balasan Cepat** dan **Settingan AI** (hanya tampil untuk Manager — lihat §8 & §12).

---

## 5. Pane 2 — Daftar percakapan

Tiap item:
- Avatar kontak (atau inisial).
- **Penanda kanal:** ikon tipe (WA hijau / Telegram biru) overlay di avatar **+ label nama kanal** ("WA Toko"). Karena bisa ada 4 nomor WA, ikon tipe saja tidak cukup — agen harus tahu masuk lewat nomor/bot yang **mana**.
- Nama kontak + nomor/username.
- Preview pesan terakhir (1 baris, truncate).
- Waktu pesan terakhir (relatif: "5m", "2j").
- Badge unread (angka, warna primary).
- Indikator assignment (avatar agen kecil) bila sudah di-assign.
- Status dot (Open/Pending/Resolved) — warna konsisten.
- Tag (chip kecil) bila ada.

Urutan default: pesan terbaru di atas. Item unread sedikit lebih menonjol.

**Di header list:** search bar + kontrol filter/sortir lanjutan (lihat §10).

---

## 6. Pane 3 — Thread + composer

- **Header thread:** nama kontak, kanal asal, status badge (klik → ganti Open/Pending/Resolved), dropdown assignment.
- **Area pesan (bubble):** Incoming kiri (abu-abu), Outgoing kanan (primary blue muted). Tiap outgoing menampilkan **delivery status** (Pending/Sent/Delivered/Read/Failed) lewat ikon kecil. **Failed → merah + tombol retry.**
- **Media:** gambar (thumbnail), file (kartu nama + unduh), audio (player ringkas), video, lokasi.
- **Composer:** textarea auto-grow, tombol lampiran, tombol kirim. Ketik `/` → muncul **picker canned response**.
- **Optimistic send:** pesan langsung muncul (status Pending) sebelum konfirmasi server.
- **Composer dua mode** (Balas vs Catatan internal) — lihat §9.

---

## 7. Panel kontak (kanan, collapsible)

- Avatar, nama (**bisa diedit**), nomor, kanal.
- **Tag percakapan** — chip "komplain", "VIP", dll; tambah/hapus cepat.
- **Catatan tentang kontak** — teks lengket yang muncul setiap kontak ini chat (beda dari catatan-internal-di-percakapan di §9).
- Daftar percakapan sebelumnya dengan kontak ini.
- **Kartu ERP (opsional):** bila ERPNext terpasang → ringkasan "Sales Order / Invoice terakhir" (read-only). Bila tidak ada ERPNext → kartu **tidak muncul sama sekali** (jangan tampilkan placeholder kosong). Desain dua versi: dengan & tanpa kartu ini.

---

## 8. Kelola Balasan Cepat (Canned Response)

Agen **memakai** canned lewat picker `/` (lihat §6). **Mengelola** (tambah/edit/hapus) dilakukan di dalam inbox, bukan di backend Frappe — karena dipakai harian.

- Panel/modal kelola: daftar canned (title, shortcut, isi) + aksi tambah/edit/hapus.
- **Permission: hanya Inbox Manager** yang bisa kelola. Agen hanya melihat & memakai (tidak ada tombol kelola untuk agen).
- Akses dari sidebar atau dari dalam picker ("Kelola balasan" — hanya tampil untuk Manager).
- Sederhana sesuai brand. Bukan rich editor — cukup teks + shortcut.

---

## 9. Catatan internal di percakapan (composer dua mode)

Composer punya **dua mode** yang jelas berbeda:
- **"Balas"** → terkirim ke pelanggan.
- **"Catatan internal"** → antar-agen, **TIDAK PERNAH terkirim ke pelanggan**.

Persyaratan desain:
- Saat mode "Catatan internal" aktif, **composer berubah warna** (amber/kuning lembut) agar mustahil tertukar dengan balasan biasa.
- Catatan internal di thread tampil beda jelas: background amber, label "Catatan internal", ikon gembok/mata.
- Pembedaan ini **krusial untuk keselamatan** — agen harus mustahil salah kira catatan internal akan terkirim, atau sebaliknya.

---

## 10. Pencarian, filter & sortir lanjutan

- **Search bar** di atas daftar percakapan: cari by nama/nomor kontak. (Cari isi pesan = nice-to-have, boleh ditandai sekunder.)
- **Filter/sortir lanjutan** di header list: per agen (assigned to siapa), "belum dibalas" (pesan terakhir dari pelanggan), sortir per tanggal. Ringkas (dropdown/chip), **bukan modal bertingkat**.

---

## 11. Notifikasi & status agen

- **Notifikasi:** toast halus saat chat baru masuk (+ badge unread). Tidak mengganggu, bisa di-mute. Notifikasi browser native = opsional.
- **Status agen (manual):** toggle "Available / Away" di header. **Kosmetik untuk pilot** — dipilih sendiri oleh agen, **bukan** deteksi online/offline otomatis (presence real-time ditunda). Cukup toggle + indikator warna.

---

## 12. AI Layer — DESAIN MENDAHULUI BUILD

> Didesain lebih dulu untuk **alasan produk/whitelabel** (materi jualan + flow siap), bukan kebutuhan operasional pilot. **Build tetap ditunda (Phase 9).** Desain harus **provider-agnostic** — flow Ollama vs cloud masih bisa berubah.

**Tombol "Sarankan balasan" (agent-assist) di composer:**
- Tombol kecil (mis. ikon ✨). Hanya tampil bila AI **aktif**.
- Klik → loading singkat → **draft muncul di composer, bisa diedit, BELUM terkirim.** Agen edit/terima/buang, lalu kirim manual.
- **Tidak ada auto-send.** Agen selalu di loop.
- State: AI nonaktif (tombol tidak ada), loading, gagal (pesan halus, composer tetap bisa dipakai manual).

**Panel Settingan AI (akses Inbox Manager saja):**
- Toggle Aktif / Nonaktif AI.
- Pilih provider: `Ollama (lokal)` / `Claude` / `OpenAI`.
- Field kondisional: Ollama → `endpoint` + `model`; Claude/OpenAI → `API key` + `model`.
- **Indikator data-residency** (angkat nilai Sopwer jadi terlihat):
  - Ollama → badge **hijau**: "Data tinggal di server Anda, tidak keluar."
  - Cloud → banner **amber**: "Isi chat dikirim ke server [provider] di luar negeri."
- Tombol "Tes koneksi" + indikator status.

---

## 13. State yang WAJIB didesain (jangan hanya layar ideal)

- Empty — daftar percakapan kosong ("Belum ada percakapan").
- Empty — thread belum dipilih (ilustrasi ringan + hint).
- Loading — list & thread (skeleton, bukan spinner penuh layar).
- **Pesan gagal kirim (Failed)** — jelas + tombol retry.
- **Kanal terputus** (mis. Wuzapi disconnect) — banner non-blocking di atas, warna amber.
- Unread vs read — pembeda visual jelas.
- Hasil pencarian kosong ("Tidak ada percakapan cocok").
- Mode catatan internal aktif — composer & preview berubah tampilan.
- AI nonaktif / AI loading / AI gagal (bila §12 didesain).

---

## 14. Interaksi & UX notes

- **Kecepatan agen prioritas:** keyboard-friendly (Enter kirim, Shift+Enter baris baru, `/` canned).
- Ganti status & assignment cukup 1–2 klik, tanpa modal bertingkat.
- Realtime: pesan baru → item naik ke atas list + badge unread + notifikasi halus. **Jangan auto-scroll** yang mengganggu saat agen sedang membaca pesan lama.
- Mobile: 3-pane → stack (list → tap → thread).

---

## 15. Yang TIDAK perlu didesain (di luar scope pilot)

> **Prinsip pemilahan:** scope ditentukan oleh **siapa yang pakai & seberapa sering**, bukan label "settings". Aksi harian agen/manager → layak UI di dalam inbox. Aksi admin sekali-setup → cukup form Frappe bawaan.

- Reporting / analytics dashboard.
- SLA timer.
- **Auto-reply penuh / bot menjawab pelanggan tanpa agen** (risiko tinggi) — yang didesain hanya agent-assist (§12).
- Composer template Cloud API + indikator window 24 jam.
- Whitelabel theming.
- **Pengaturan/tambah kanal** (input token, scan QR) — aksi admin sekali di awal, cukup form DocType bawaan Frappe. Jangan desain UI "Sambungkan kanal baru". (Bandingkan: kelola canned = aksi harian → **didesain**, §8.)

---

## 16. Deliverable yang diharapkan dari Claude Design

1. **3-pane layout** desktop lengkap (sidebar, list, thread+composer, panel kontak).
2. **Conversation list item** — semua varian: unread, assigned, per kanal (label nama kanal), bertag.
3. **Bubble pesan** — incoming / outgoing / media / failed + ikon delivery status.
4. **Composer** — picker canned (`/`), lampiran, optimistic send.
5. **Composer dua mode** — Balas vs Catatan internal (tampilan jelas berbeda).
6. **Panel kontak** — versi dengan & tanpa kartu ERP; edit nama, tag, catatan kontak.
7. **Panel kelola canned response** (akses Manager).
8. **Search bar + filter/sortir lanjutan** di header list.
9. **Toast notifikasi** + toggle status agen (manual Available/Away).
10. **Tombol "Sarankan balasan" + Panel Settingan AI** (provider + indikator residency, akses Manager) — desain mendahului build.
11. **Semua state** di §13.
12. **Palet warna & token** (turunan brand §2) yang bisa langsung dipetakan ke Tailwind.

Setelah disetujui, token & komponen ini menjadi acuan implementasi React (Phase 6).
