import { describe, expect, it } from "vitest";

import {
  getSpeechRecognitionCtor,
  isSpeechSynthesisSupported,
  pickVoice,
} from "@/features/voice/lib/speech";

describe("speech feature detection", () => {
  it("prefers the standard constructor and falls back to webkit", () => {
    class Std {}
    class Webkit {}
    expect(
      getSpeechRecognitionCtor({ SpeechRecognition: Std, webkitSpeechRecognition: Webkit }),
    ).toBe(Std);
    expect(getSpeechRecognitionCtor({ webkitSpeechRecognition: Webkit })).toBe(Webkit);
    expect(getSpeechRecognitionCtor({})).toBeNull();
    expect(getSpeechRecognitionCtor(undefined)).toBeNull();
  });

  it("detects speechSynthesis support", () => {
    expect(
      isSpeechSynthesisSupported({ speechSynthesis: {}, SpeechSynthesisUtterance: class {} }),
    ).toBe(true);
    expect(isSpeechSynthesisSupported({})).toBe(false);
  });
});

describe("pickVoice", () => {
  const voices = [
    { name: "Google US", lang: "en-US", localService: false },
    { name: "Remote Hindi", lang: "hi-IN", localService: false },
    { name: "Local Hindi", lang: "hi_IN", localService: true },
    { name: "Indian English", lang: "en-IN", localService: true },
  ];

  it("picks an exact-locale local voice first", () => {
    expect(pickVoice(voices, "hi-IN")?.name).toBe("Local Hindi");
  });

  it("falls back to the same language", () => {
    expect(pickVoice(voices, "en-GB")?.name).toBe("Indian English");
  });

  it("returns null when nothing matches", () => {
    expect(pickVoice(voices, "ta-IN")).toBeNull();
  });
});
