"use client";

import { motion } from "framer-motion";
import {
  BrainCircuitIcon,
  CpuIcon,
  EyeOffIcon,
  LockIcon,
  MicIcon,
  ShieldCheckIcon,
  WalletIcon,
  ZapIcon,
} from "lucide-react";
import Link from "next/link";

import { LocaleToggle } from "@/components/common/LocaleToggle";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TryDemoButton } from "@/features/auth/components/TryDemoButton";
import type { MessageKey } from "@/lib/i18n/dictionaries";
import { useT } from "@/lib/i18n/I18nProvider";

const STEPS: { icon: typeof MicIcon; title: MessageKey; body: MessageKey }[] = [
  { icon: MicIcon, title: "landing.how.step1.title", body: "landing.how.step1.body" },
  { icon: EyeOffIcon, title: "landing.how.step2.title", body: "landing.how.step2.body" },
  { icon: CpuIcon, title: "landing.how.step3.title", body: "landing.how.step3.body" },
  { icon: ShieldCheckIcon, title: "landing.how.step4.title", body: "landing.how.step4.body" },
];

const MODELS: { name: string; id: string; role: MessageKey; icon: typeof ZapIcon }[] = [
  {
    name: "Nemotron 3 Nano",
    id: "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    role: "landing.models.nano",
    icon: ZapIcon,
  },
  {
    name: "Nemotron 3 Super",
    id: "nvidia/nemotron-3-super-120b-a12b",
    role: "landing.models.super",
    icon: BrainCircuitIcon,
  },
  {
    name: "Qwen3 Embedding 8B",
    id: "Qwen/Qwen3-Embedding-8B",
    role: "landing.models.embed",
    icon: LockIcon,
  },
];

const PRIVACY: { icon: typeof EyeOffIcon; text: MessageKey }[] = [
  { icon: EyeOffIcon, text: "landing.privacy.mask" },
  { icon: LockIcon, text: "landing.privacy.memory" },
  { icon: ShieldCheckIcon, text: "landing.privacy.approve" },
  { icon: WalletIcon, text: "landing.privacy.budget" },
];

export function Landing() {
  const t = useT();
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4">
        <span className="flex items-center gap-2 font-semibold">
          <span aria-hidden="true">🪔</span>
          {t("app.name")}
        </span>
        <div className="flex items-center gap-1">
          <LocaleToggle />
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-16 md:grid-cols-[1.2fr_1fr] md:py-24">
          <div className="flex flex-col gap-6">
            <p className="text-sm font-medium text-primary">{t("app.tagline")}</p>
            <h1 className="text-4xl leading-tight font-bold tracking-tight md:text-5xl">
              {t("landing.hero.title")}
            </h1>
            <p className="max-w-xl text-lg text-muted-foreground">{t("landing.hero.subtitle")}</p>
            <div className="flex flex-wrap gap-3">
              <TryDemoButton />
              <Button asChild size="lg" variant="outline">
                <Link href="#how">{t("landing.cta.how")}</Link>
              </Button>
            </div>
          </div>
          <div
            aria-hidden="true"
            className="relative mx-auto flex size-64 items-center justify-center"
          >
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                className="absolute inset-0 rounded-full bg-primary/15"
                animate={{ scale: [0.7, 1.15], opacity: [0.6, 0] }}
                transition={{ duration: 3, repeat: Infinity, delay: i, ease: "easeOut" }}
              />
            ))}
            <div className="relative flex size-32 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-xl">
              <MicIcon className="size-14" />
            </div>
          </div>
        </section>

        <section id="how" className="border-y bg-muted/30">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <h2 className="mb-8 text-2xl font-semibold md:text-3xl">{t("landing.how.title")}</h2>
            <ol className="grid gap-4 md:grid-cols-4">
              {STEPS.map(({ icon: Icon, title, body }, i) => (
                <li key={title}>
                  <Card className="h-full">
                    <CardHeader>
                      <span className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span className="flex size-6 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
                          {i + 1}
                        </span>
                        <Icon aria-hidden="true" className="size-4" />
                      </span>
                      <CardTitle className="text-base">{t(title)}</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground">{t(body)}</CardContent>
                  </Card>
                </li>
              ))}
            </ol>

            <h3 className="mt-12 mb-4 text-lg font-semibold">{t("landing.models.title")}</h3>
            <ul className="grid gap-4 md:grid-cols-3">
              {MODELS.map(({ name, id, role, icon: Icon }) => (
                <li key={id} className="flex flex-col gap-2 rounded-xl border bg-card p-5">
                  <span className="flex items-center gap-2 font-medium">
                    <Icon aria-hidden="true" className="size-4 text-primary" />
                    {name}
                  </span>
                  <code className="text-xs break-all text-muted-foreground">{id}</code>
                  <p className="text-sm">{t(role)}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="mb-8 text-2xl font-semibold md:text-3xl">{t("landing.privacy.title")}</h2>
          <ul className="grid gap-4 sm:grid-cols-2">
            {PRIVACY.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3 rounded-xl border p-5">
                <Icon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-primary" />
                <span className="text-sm">{t(text)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-10 flex justify-center">
            <TryDemoButton />
          </div>
        </section>
      </main>

      <footer className="border-t">
        <p className="mx-auto max-w-6xl px-4 py-6 text-center text-xs text-muted-foreground">
          {t("landing.footer")}
        </p>
      </footer>
    </div>
  );
}
