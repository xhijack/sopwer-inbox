/* Tiny Web Audio sound cues — no audio files, very light & quiet.
 * Soft "blip" for an incoming message, soft "tup" for an outgoing one.
 * Respects a global mute flag (toggled from the UI). */

let muted = false;
let ctx: AudioContext | null = null;

export function setMuted(m: boolean) {
  muted = m;
}

function getCtx(): AudioContext | null {
  if (muted) return null;
  try {
    if (!ctx) {
      const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      ctx = new AC();
    }
    if (ctx.state === "suspended") void ctx.resume();
    return ctx;
  } catch {
    return null;
  }
}

/** Play a single soft tone. gain kept low (≤0.06) so it stays subtle. */
function tone(freq: number, durMs: number, when = 0, gain = 0.05, sweepTo?: number) {
  const ac = getCtx();
  if (!ac) return;
  const t0 = ac.currentTime + when;
  const osc = ac.createOscillator();
  const g = ac.createGain();
  osc.type = "sine";
  osc.frequency.setValueAtTime(freq, t0);
  if (sweepTo) osc.frequency.exponentialRampToValueAtTime(sweepTo, t0 + durMs / 1000);
  // quick attack, smooth decay — avoids clicks
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(gain, t0 + 0.012);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + durMs / 1000);
  osc.connect(g);
  g.connect(ac.destination);
  osc.start(t0);
  osc.stop(t0 + durMs / 1000 + 0.02);
}

/** Incoming: a gentle two-note rise. */
export function playIncoming() {
  tone(587, 90, 0, 0.05); // D5
  tone(784, 120, 0.08, 0.045); // G5
}

/** Outgoing: a single soft, short tone. */
export function playOutgoing() {
  tone(440, 80, 0, 0.035, 360); // soft downward "tup"
}
