"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { dictionaries, translate, type MessageKey, type UiLocale } from "./dictionaries";

const STORAGE_KEY = "saathi.uiLocale";

interface I18nContextValue {
  locale: UiLocale;
  /** BCP-47 tag for Intl and speech APIs. */
  bcp47: "en-IN" | "hi-IN";
  setLocale: (locale: UiLocale) => void;
  toggleLocale: () => void;
  t: (key: MessageKey, vars?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({
  children,
  initialLocale = "en",
}: {
  children: React.ReactNode;
  initialLocale?: UiLocale;
}) {
  const [locale, setLocaleState] = useState<UiLocale>(initialLocale);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "hi") setLocaleState(stored);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((next: UiLocale) => {
    setLocaleState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      bcp47: locale === "hi" ? "hi-IN" : "en-IN",
      setLocale,
      toggleLocale: () => setLocale(locale === "hi" ? "en" : "hi"),
      t: (key, vars) => translate(dictionaries[locale], key, vars),
    }),
    [locale, setLocale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}

export function useT(): I18nContextValue["t"] {
  return useI18n().t;
}
