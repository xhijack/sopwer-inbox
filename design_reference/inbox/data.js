/* ============================================================
   Sopwer Omnichannel Inbox — seed data (v2)
   Plain JS, assigns to window.INBOX (loaded before babel scripts)
   ============================================================ */
(function () {
  // Agents (Andi = the logged-in user)
  const AGENTS = {
    me:   { id: 'me',   name: 'Andi Nugroho', initials: 'AN', color: 'var(--sw-blue-500)' },
    rina: { id: 'rina', name: 'Rina Aulia',   initials: 'RA', color: 'var(--sw-green-600)' },
    budi: { id: 'budi', name: 'Budi Saputra', initials: 'BS', color: 'var(--sw-yellow-600)' },
    dewi: { id: 'dewi', name: 'Dewi Hartanti',initials: 'DH', color: 'var(--sw-ink-500)' },
  };

  // Channels — INDIVIDUAL named channels (one client can have many WA numbers / TG bots)
  const CHANNELS = {
    wa_cs:       { id: 'wa_cs',       type: 'wa', name: 'WA CS',         addr: '+62 811-2000-1010' },
    wa_toko:     { id: 'wa_toko',     type: 'wa', name: 'WA Toko',       addr: '+62 811-2000-2020' },
    wa_reseller: { id: 'wa_reseller', type: 'wa', name: 'WA Reseller',   addr: '+62 811-2000-3030' },
    tg_cs:       { id: 'tg_cs',       type: 'tg', name: 'Telegram CS',   addr: '@sopwer_cs_bot' },
    tg_promo:    { id: 'tg_promo',    type: 'tg', name: 'Telegram Promo',addr: '@sopwer_promo_bot' },
  };

  // Canned responses (typing "/" in composer; managed by Manager in §8 panel)
  const CANNED = [
    { id:'cn1', slug: 'halo',   title: 'Salam pembuka',  body: 'Halo! Terima kasih sudah menghubungi Sopwer. Ada yang bisa kami bantu hari ini?' },
    { id:'cn2', slug: 'tunggu', title: 'Minta waktu',    body: 'Mohon ditunggu sebentar ya, saya cek dulu datanya di sistem.' },
    { id:'cn3', slug: 'resi',   title: 'Info resi',      body: 'Berikut nomor resi pengiriman pesanan Anda: [RESI]. Bisa dilacak di halaman ekspedisi terkait.' },
    { id:'cn4', slug: 'refund', title: 'Proses refund',  body: 'Untuk proses refund, mohon kirimkan nomor order dan alasan pengembalian ya. Akan kami proses 1–2 hari kerja.' },
    { id:'cn5', slug: 'jam',    title: 'Jam operasional',body: 'Jam operasional CS kami Senin–Jumat 08.00–17.00 WIB. Pesan di luar jam akan dibalas pada hari kerja berikutnya.' },
    { id:'cn6', slug: 'tutup',  title: 'Penutup',        body: 'Terima kasih sudah menghubungi kami. Jika ada kendala lagi, jangan ragu chat kembali ya. Semoga harinya menyenangkan!' },
  ];

  const t = (h, m) => `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;

  const CONVERSATIONS = [
    {
      id: 'c1',
      contact: { name: 'Budi Santoso', handle: '+62 812-3344-5566', initials: 'BS', color: 'var(--sw-blue-600)' },
      channelId: 'wa_cs',
      status: 'open', assignee: null, unread: 2, lastTime: '2m',
      tags: ['Pengiriman'],
      note: 'Pelanggan langganan, sering order kain cotton. Lebih suka dihubungi sore hari.',
      orders: [
        { no: 'SO-2026-1184', label: 'Sales Order', amount: 'Rp 1.250.000', status: 'paid', date: '02 Jun 2026' },
        { no: 'INV-2026-0991', label: 'Invoice', amount: 'Rp 1.250.000', status: 'paid', date: '02 Jun 2026' },
      ],
      messages: [
        { id:'m1', dir:'in', type:'text', text:'Halo min, saya mau tanya pesanan saya kok belum sampai ya?', time:t(9,12) },
        { id:'m2', dir:'in', type:'text', text:'Order SO-2026-1184, sudah 3 hari statusnya masih "dikirim"', time:t(9,12) },
        { id:'m3', dir:'out', type:'text', text:'Halo Pak Budi, terima kasih sudah menghubungi Sopwer. Mohon ditunggu sebentar ya, saya cek dulu status pengirimannya.', time:t(9,14), status:'read', agent:'me' },
        { id:'mn1', dir:'out', type:'note', text:'Cek ke gudang: paket Pak Budi tertahan di transit Bandung karena salah sortir. Sudah saya minta dipercepat.', time:t(9,15), agent:'me' },
        { id:'m4', dir:'out', type:'text', text:'Pesanan Bapak sudah dalam perjalanan dan saat ini berada di gudang transit Bandung. Estimasi tiba besok sore.', time:t(9,16), status:'read', agent:'me' },
        { id:'m5', dir:'in', type:'text', text:'Oh gitu, boleh minta nomor resinya min biar saya bisa pantau?', time:t(9,18) },
        { id:'m6', dir:'in', type:'location', media:{ label:'Rumah — Jl. Melati No. 12, Bandung' }, caption:'Ini alamat pengiriman saya ya', time:t(9,18) },
        { id:'m7', dir:'out', type:'text', text:'Baik, berikut nomor resi pengiriman pesanan Anda: JNE-0048213776. Bisa dilacak langsung di aplikasi JNE ya Pak.', time:t(9,21), status:'delivered', agent:'me' },
      ],
    },
    {
      id: 'c2',
      contact: { name: 'Siti Rahmawati', handle: '@siti_rahma', initials: 'SR', color: 'var(--sw-green-600)' },
      channelId: 'tg_cs',
      status: 'open', assignee: 'me', unread: 0, lastTime: '14m',
      tags: ['Demo', 'Prospek'],
      note: '',
      orders: [],
      messages: [
        { id:'m1', dir:'in', type:'text', text:'Selamat siang, apakah produk Paket ERP Retail masih tersedia untuk demo?', time:t(13,2) },
        { id:'m2', dir:'out', type:'text', text:'Selamat siang Bu Siti! Tentu, demo Sopwer Cloud untuk Retail masih tersedia. Boleh saya tahu skala bisnis Ibu agar kami siapkan skenarionya?', time:t(13,5), status:'read', agent:'me' },
        { id:'m3', dir:'in', type:'text', text:'Toko bahan bangunan, 3 cabang di Bekasi. Kira-kira cocok modul yang mana ya?', time:t(13,9) },
        { id:'m4', dir:'in', type:'video', media:{ w:240, h:150, dur:'0:38', tone:'green' }, caption:'Ini kondisi gudang kami sekarang', time:t(13,10) },
        { id:'m5', dir:'out', type:'text', text:'Untuk 3 cabang, kami sarankan modul Penjualan + Inventory multi-gudang + Akuntansi. Saya jadwalkan demo minggu depan ya, hari apa yang nyaman?', time:t(13,11), status:'read', agent:'me' },
      ],
    },
    {
      id: 'c3',
      contact: { name: 'Ahmad Fauzi', handle: '+62 813-9988-1100', initials: 'AF', color: 'var(--sw-yellow-700)' },
      channelId: 'wa_toko',
      status: 'pending', assignee: 'rina', unread: 0, lastTime: '1j',
      tags: ['Komplain', 'Refund'],
      note: '',
      orders: [ { no: 'SO-2026-1170', label: 'Sales Order', amount: 'Rp 3.400.000', status: 'pending', date: '28 Mei 2026' } ],
      messages: [
        { id:'m1', dir:'in', type:'text', text:'Min saya mau refund untuk order SO-2026-1170, barangnya tidak sesuai deskripsi', time:t(11,40) },
        { id:'m2', dir:'in', type:'file', media:{ name:'bukti-kerusakan.pdf', size:'1,4 MB' }, time:t(11,41) },
        { id:'m3', dir:'out', type:'text', text:'Mohon maaf atas ketidaknyamanannya Pak Ahmad. Untuk proses refund, sudah kami terima dokumennya. Akan kami proses 1–2 hari kerja ya.', time:t(11,52), status:'delivered', agent:'rina' },
        { id:'mn1', dir:'out', type:'note', text:'@Rina refund ini sudah saya ajukan ke tim finance, tinggal tunggu approval. Tolong follow up besok pagi ya.', time:t(11,54), agent:'me' },
        { id:'m4', dir:'in', type:'text', text:'Baik, saya tunggu ya', time:t(11,55) },
      ],
    },
    {
      id: 'c4',
      contact: { name: 'Toko Berkah Jaya', handle: '+62 877-1212-3434', initials: 'TB', color: 'var(--sw-blue-500)' },
      channelId: 'wa_reseller',
      status: 'open', assignee: null, unread: 1, lastTime: '2j',
      tags: ['Grosir', 'VIP'],
      note: 'Reseller grosir aktif. Minta format PO khusus & harga tier reseller.',
      orders: [],
      messages: [
        { id:'m1', dir:'in', type:'text', text:'Selamat pagi, kami tertarik untuk pemesanan dalam jumlah besar (grosir). Apakah ada harga khusus?', time:t(8,30) },
        { id:'m2', dir:'in', type:'audio', media:{ dur:'0:24' }, time:t(8,31) },
      ],
    },
    {
      id: 'c5',
      contact: { name: 'Rizki Pratama', handle: '@rizkipra', initials: 'RP', color: 'var(--sw-green-600)' },
      channelId: 'tg_promo',
      status: 'open', assignee: 'me', unread: 0, lastTime: '3j',
      tags: [],
      note: '',
      orders: [ { no: 'INV-2026-0980', label: 'Invoice', amount: 'Rp 780.000', status: 'pending', date: '01 Jun 2026' } ],
      messages: [
        { id:'m1', dir:'in', type:'text', text:'Halo, saya sudah transfer untuk invoice INV-2026-0980. Mohon dicek ya', time:t(7,15) },
        { id:'m2', dir:'in', type:'image', media:{ w:200, h:240, label:'bukti-transfer.jpg', tone:'green' }, time:t(7,15) },
        { id:'m3', dir:'out', type:'text', text:'Terima kasih Pak Rizki, pembayaran sudah kami terima dan verifikasi. Pesanan akan segera diproses.', time:t(7,40), status:'read', agent:'me' },
      ],
    },
    {
      id: 'c6',
      contact: { name: 'Maya Putri', handle: '+62 856-7788-9900', initials: 'MP', color: 'var(--sw-yellow-700)' },
      channelId: 'wa_cs',
      status: 'open', assignee: 'me', unread: 0, lastTime: '5j',
      tags: ['Pengiriman'],
      note: '',
      orders: [],
      messages: [
        { id:'m1', dir:'in', type:'text', text:'Min apakah bisa ganti alamat pengiriman? Saya salah input', time:t(6,5) },
        { id:'m2', dir:'out', type:'text', text:'Bisa Bu Maya, boleh kirimkan alamat yang benar? Selama pesanan belum dikirim masih bisa kami ubah.', time:t(6,8), status:'failed', agent:'me' },
      ],
    },
    {
      id: 'c7',
      contact: { name: 'Hendra Wijaya', handle: '@hendraw', initials: 'HW', color: 'var(--sw-ink-500)' },
      channelId: 'tg_cs',
      status: 'pending', assignee: 'budi', unread: 0, lastTime: 'Kemarin',
      tags: ['Integrasi'],
      note: '',
      orders: [],
      messages: [
        { id:'m1', dir:'in', type:'text', text:'Mau tanya soal integrasi WhatsApp ke sistem kami, apakah bisa dijadwalkan call?', time:t(16,20) },
        { id:'m2', dir:'out', type:'text', text:'Tentu Pak Hendra, tim teknis kami akan menghubungi. Boleh share nomor & waktu yang nyaman?', time:t(16,35), status:'delivered', agent:'budi' },
      ],
    },
    {
      id: 'c8',
      contact: { name: 'Linda Kusuma', handle: '+62 821-4455-6677', initials: 'LK', color: 'var(--sw-green-600)' },
      channelId: 'wa_toko',
      status: 'resolved', assignee: 'rina', unread: 0, lastTime: 'Kemarin',
      tags: ['VIP'],
      note: '',
      orders: [ { no: 'INV-2026-0955', label: 'Invoice', amount: 'Rp 2.100.000', status: 'paid', date: '30 Mei 2026' } ],
      messages: [
        { id:'m1', dir:'in', type:'text', text:'Pesanan sudah sampai dengan baik, terima kasih banyak ya min!', time:t(15,2) },
        { id:'m2', dir:'out', type:'text', text:'Sama-sama Bu Linda, senang bisa membantu. Terima kasih sudah berbelanja di kami!', time:t(15,4), status:'read', agent:'rina' },
      ],
    },
    {
      id: 'c9',
      contact: { name: 'CV Sumber Makmur', handle: '@sumbermakmur', initials: 'SM', color: 'var(--sw-blue-600)' },
      channelId: 'tg_promo',
      status: 'resolved', assignee: 'me', unread: 0, lastTime: '2 hari',
      tags: [],
      note: '',
      orders: [],
      messages: [
        { id:'m1', dir:'in', type:'text', text:'Sudah jelas semua, terima kasih penjelasannya.', time:t(10,12) },
        { id:'m2', dir:'out', type:'text', text:'Baik Pak, terima kasih kembali. Jika ada kebutuhan lain kami siap membantu.', time:t(10,15), status:'read', agent:'me' },
      ],
    },
  ];

  // AI draft suggestions keyed loosely; app picks based on last inbound msg
  const AI_DRAFTS = [
    'Halo, terima kasih sudah menghubungi kami. Mengenai hal tersebut, izinkan saya cek dulu detailnya di sistem ya — mohon ditunggu sebentar.',
    'Baik, saya bantu prosesnya sekarang. Boleh konfirmasi nomor pesanan Anda agar saya bisa menindaklanjuti dengan tepat?',
    'Terima kasih atas informasinya. Untuk mempercepat, saya teruskan ke tim terkait dan akan kabari Anda secepatnya hari ini juga.',
  ];

  window.INBOX = { AGENTS, CHANNELS, CANNED, CONVERSATIONS, AI_DRAFTS };
})();
