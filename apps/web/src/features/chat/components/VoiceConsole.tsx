"use client";

import { InfoIcon, ShieldCheckIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { PendingActionList } from "@/features/approvals/components/PendingActionList";
import { BudgetMeter } from "@/features/budget/components/BudgetMeter";
import { PrivacyPanel } from "@/features/privacy/components/PrivacyPanel";
import { MicButton } from "@/features/voice/components/MicButton";
import {
  useSpeechRecognition,
  type SpeechLocale,
} from "@/features/voice/hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "@/features/voice/hooks/useSpeechSynthesis";
import { useI18n } from "@/lib/i18n/I18nProvider";

import { useAssistantTurn } from "../hooks/useAssistantTurn";
import { Composer } from "./Composer";
import { Transcript } from "./Transcript";

const SPEAK_KEY = "saathi.speakReplies";

export function VoiceConsole() {
  const { t, bcp47 } = useI18n();
  const [speechLocale, setSpeechLocale] = useState<SpeechLocale>(bcp47);
  const [speakReplies, setSpeakReplies] = useState(true);
  const tts = useSpeechSynthesis();

  useEffect(() => setSpeechLocale(bcp47), [bcp47]);
  useEffect(() => {
    setSpeakReplies(window.localStorage.getItem(SPEAK_KEY) !== "false");
  }, []);

  const turn = useAssistantTurn({
    locale: speechLocale,
    onReply: (text) => {
      if (speakReplies) tts.speak(text, speechLocale);
    },
  });

  const stt = useSpeechRecognition({
    locale: speechLocale,
    onFinal: (transcript) => void turn.send(transcript, "voice"),
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <section className="flex min-h-[60vh] flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">{t("console.title")}</h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Label htmlFor="speech-locale" className="text-xs">
                {t("console.speechLang")}
              </Label>
              <select
                id="speech-locale"
                value={speechLocale}
                onChange={(e) => setSpeechLocale(e.target.value as SpeechLocale)}
                className="h-8 rounded-md border border-input bg-transparent px-2 text-xs"
              >
                <option value="hi-IN">हिंदी</option>
                <option value="en-IN">English</option>
              </select>
            </div>
            {tts.supported ? (
              <div className="flex items-center gap-2">
                <Switch
                  id="speak-replies"
                  checked={speakReplies}
                  onCheckedChange={(checked) => {
                    setSpeakReplies(checked);
                    window.localStorage.setItem(SPEAK_KEY, String(checked));
                    if (!checked) tts.cancel();
                  }}
                />
                <Label htmlFor="speak-replies" className="text-xs">
                  {t("console.speakReplies")}
                </Label>
              </div>
            ) : null}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto rounded-2xl border bg-muted/30 p-4">
          {turn.messages.length === 0 && !stt.interim ? (
            <EmptyState
              title={t("console.empty.title")}
              description={t("console.empty.body")}
              className="border-0"
            />
          ) : (
            <Transcript
              messages={turn.messages}
              interim={stt.interim}
              activeTool={turn.activeTool}
            />
          )}
        </div>

        {turn.pendingActions.length > 0 ? (
          <Card className="border-primary/40" data-testid="inline-pending-actions">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm">
                <ShieldCheckIcon aria-hidden="true" className="size-4 text-primary" />
                {t("approvals.pendingInline")}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <ul className="list-disc pl-5 text-sm">
                {turn.pendingActions.map((p) => (
                  <li key={p.id}>{p.summary}</li>
                ))}
              </ul>
              <Button asChild size="sm" variant="outline" className="self-start">
                <Link href="/approvals">{t("nav.approvals")}</Link>
              </Button>
            </CardContent>
          </Card>
        ) : null}

        <div className="flex flex-col items-center gap-3">
          <MicButton
            supported={stt.supported}
            listening={stt.listening}
            disabled={turn.isStreaming}
            onStart={() => {
              tts.cancel();
              stt.start();
            }}
            onStop={stt.stop}
          />
          <p className="text-xs text-muted-foreground" aria-live="polite">
            {stt.listening ? t("console.mic.listening") : null}
            {stt.error === "not-allowed" ? t("console.micDenied") : null}
          </p>
          {!stt.supported ? (
            <p
              data-testid="stt-fallback-notice"
              className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground"
            >
              <InfoIcon aria-hidden="true" className="size-4" />
              {t("console.noStt")}
            </p>
          ) : null}
        </div>

        <Composer
          streaming={turn.isStreaming}
          onStop={turn.stop}
          onSend={(text) => {
            tts.cancel();
            void turn.send(text, "text");
          }}
        />
      </section>

      <aside className="flex flex-col gap-4">
        <PrivacyPanel counts={turn.entityCounts} />
        <ErrorBoundary>
          <PendingActionList status="pending" limit={3} compact />
        </ErrorBoundary>
        <ErrorBoundary>
          <BudgetMeter />
        </ErrorBoundary>
      </aside>
    </div>
  );
}
