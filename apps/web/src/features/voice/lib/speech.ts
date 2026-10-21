/**
 * Minimal Web Speech API typings + feature detection. The recognition API is still
 * prefixed (webkitSpeechRecognition) in Chrome/Edge/Android and missing in Firefox,
 * so everything here degrades to "unsupported" and the UI falls back to text input.
 */

export interface SpeechRecognitionAlternativeLike {
  transcript: string;
  confidence: number;
}

export interface SpeechRecognitionResultLike {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: SpeechRecognitionAlternativeLike;
}

export interface SpeechRecognitionEventLike {
  readonly resultIndex: number;
  readonly results: {
    readonly length: number;
    [index: number]: SpeechRecognitionResultLike;
  };
}

export interface SpeechRecognitionErrorEventLike {
  readonly error: string;
  readonly message?: string;
}

export interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

export type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

type SpeechWindow = {
  SpeechRecognition?: SpeechRecognitionCtor;
  webkitSpeechRecognition?: SpeechRecognitionCtor;
};

export function getSpeechRecognitionCtor(
  scope: unknown = typeof window === "undefined" ? undefined : window,
): SpeechRecognitionCtor | null {
  if (!scope) return null;
  const w = scope as SpeechWindow;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function isSpeechSynthesisSupported(
  scope: unknown = typeof window === "undefined" ? undefined : window,
): boolean {
  return (
    !!scope &&
    "speechSynthesis" in (scope as object) &&
    "SpeechSynthesisUtterance" in (scope as object)
  );
}

export interface VoiceLike {
  lang: string;
  name: string;
  localService?: boolean;
  default?: boolean;
}

const normalise = (lang: string) => lang.replace("_", "-").toLowerCase();

/** Best voice for a BCP-47 locale: exact match, then same language, local voices first. */
export function pickVoice<V extends VoiceLike>(voices: readonly V[], locale: string): V | null {
  const want = normalise(locale);
  const language = want.split("-")[0] ?? want;
  const rank = (v: V) => (v.localService ? 0 : 1);
  const exact = voices.filter((v) => normalise(v.lang) === want).sort((a, b) => rank(a) - rank(b));
  if (exact[0]) return exact[0];
  const sameLanguage = voices
    .filter((v) => normalise(v.lang).split("-")[0] === language)
    .sort((a, b) => rank(a) - rank(b));
  return sameLanguage[0] ?? null;
}
