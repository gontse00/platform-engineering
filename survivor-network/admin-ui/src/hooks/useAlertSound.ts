import { useCallback, useRef } from "react";

export function useAlertSound() {
  const ctxRef = useRef<AudioContext | null>(null);
  const lastPlayedRef = useRef(0);

  const play = useCallback((urgency: "critical" | "high" = "critical") => {
    const now = Date.now();
    if (now - lastPlayedRef.current < 1000) return;
    lastPlayedRef.current = now;

    try {
      if (!ctxRef.current) {
        ctxRef.current = new AudioContext();
      }
      const ctx = ctxRef.current;
      const t = ctx.currentTime;

      if (urgency === "critical") {
        const osc1 = ctx.createOscillator();
        const gain1 = ctx.createGain();
        osc1.type = "sine";
        osc1.frequency.value = 880;
        gain1.gain.setValueAtTime(0.3, t);
        gain1.gain.exponentialRampToValueAtTime(0.01, t + 0.15);
        osc1.connect(gain1).connect(ctx.destination);
        osc1.start(t);
        osc1.stop(t + 0.15);

        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = "sine";
        osc2.frequency.value = 1100;
        gain2.gain.setValueAtTime(0.3, t + 0.18);
        gain2.gain.exponentialRampToValueAtTime(0.01, t + 0.35);
        osc2.connect(gain2).connect(ctx.destination);
        osc2.start(t + 0.18);
        osc2.stop(t + 0.35);
      } else {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = 660;
        gain.gain.setValueAtTime(0.2, t);
        gain.gain.exponentialRampToValueAtTime(0.01, t + 0.2);
        osc.connect(gain).connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.2);
      }
    } catch {
      // Audio not available
    }
  }, []);

  return play;
}