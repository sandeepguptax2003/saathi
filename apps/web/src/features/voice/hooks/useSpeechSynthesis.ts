"use client";

import { useCallback, useEffect, useState } from "react";

import { isSpeechSynthesisSupported, pickVoice } from "../lib/speech";

/** Browser TTS (primary for the live demo; VoxCPM2 is video-only for now). */
export function useSpeechSynthesis() {
  const [supported, setSupported] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    if (!isSpeechSynthesisSupported()) return;
    setSupported(true);
    const synth = window.speechSynthesis;
    const load = () => setVoices(synth.getVoices());
    load();
    synth.addEventListener("voiceschanged", load);
    return () => {
      synth.removeEventListener("voiceschanged", load);
      synth.cancel();
    };
  }, []);

  const speak = useCallback(
    (text: string, locale: string) => {
      if (!supported || !text.trim()) return;
      const synth = window.speechSynthesis;
      synth.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      // Prefer a Hindi voice for hi-IN; fall back to Indian English, then the default.
      const voice = pickVoice(voices, locale) ?? pickVoice(voices, "en-IN");
      if (voice) utterance.voice = voice;
      utterance.lang = voice?.lang ?? locale;
      utterance.rate = 1;
      utterance.onstart = () => setSpeaking(true);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      synth.speak(utterance);
    },
    [supported, voices],
  );

  const cancel = useCallback(() => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  return { supported, voices, speaking, speak, cancel };
}
