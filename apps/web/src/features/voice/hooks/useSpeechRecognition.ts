"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  getSpeechRecognitionCtor,
  type SpeechRecognitionEventLike,
  type SpeechRecognitionLike,
} from "../lib/speech";

export type SpeechLocale = "hi-IN" | "en-IN";

export interface UseSpeechRecognitionOptions {
  locale: SpeechLocale;
  /** Called once with the final transcript when the user stops speaking. */
  onFinal: (transcript: string) => void;
}

export function useSpeechRecognition({ locale, onFinal }: UseSpeechRecognitionOptions) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const finalRef = useRef("");
  const onFinalRef = useRef(onFinal);
  onFinalRef.current = onFinal;

  useEffect(() => {
    setSupported(getSpeechRecognitionCtor() !== null);
    return () => recognitionRef.current?.abort();
  }, []);

  const start = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return;
    recognitionRef.current?.abort();
    const recognition = new Ctor();
    recognition.lang = locale;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    finalRef.current = "";
    setInterim("");
    setError(null);

    recognition.onstart = () => setListening(true);
    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result?.[0]?.transcript ?? "";
        if (result?.isFinal) finalRef.current += text;
        else interimText += text;
      }
      setInterim(`${finalRef.current}${interimText}`);
    };
    recognition.onerror = (event) => {
      // "no-speech" and "aborted" are normal; surface the rest.
      if (event.error !== "no-speech" && event.error !== "aborted") setError(event.error);
    };
    recognition.onend = () => {
      setListening(false);
      setInterim("");
      const transcript = finalRef.current.trim();
      finalRef.current = "";
      if (transcript) onFinalRef.current(transcript);
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      setError("start-failed");
    }
  }, [locale]);

  const stop = useCallback(() => recognitionRef.current?.stop(), []);

  return { supported, listening, interim, error, start, stop };
}
