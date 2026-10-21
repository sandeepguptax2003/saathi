"use client";

import { useState } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { LocaleToggle } from "@/components/common/LocaleToggle";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AuthPanel } from "@/features/auth/components/AuthPanel";
import { useSession } from "@/features/auth/hooks/useSession";
import { PreferencesForm } from "@/features/settings/components/PreferencesForm";
import { useResetDemo } from "@/features/settings/hooks/useMe";
import { useT } from "@/lib/i18n/I18nProvider";

export default function SettingsPage() {
  const t = useT();
  const { user } = useSession();
  const resetDemo = useResetDemo();
  const [confirmReset, setConfirmReset] = useState(false);

  return (
    <>
      <PageHeader title={t("settings.title")} />
      <div className="flex flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{t("auth.title")}</CardTitle>
          </CardHeader>
          <CardContent>
            <AuthPanel />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("settings.preferences")}</CardTitle>
          </CardHeader>
          <CardContent>
            <PreferencesForm signedIn={!!user} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("settings.appearance")}</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-2">
            <ThemeToggle />
            <LocaleToggle />
          </CardContent>
        </Card>
        {user?.is_anonymous ? (
          <Card>
            <CardHeader>
              <CardTitle>{t("settings.demo.title")}</CardTitle>
              <CardDescription>{t("settings.demo.body")}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" onClick={() => setConfirmReset(true)}>
                {t("settings.demo.reset")}
              </Button>
              <ConfirmDialog
                open={confirmReset}
                onOpenChange={setConfirmReset}
                title={t("settings.demo.reset")}
                description={t("settings.demo.body")}
                destructive
                onConfirm={() => resetDemo.mutateAsync()}
              />
            </CardContent>
          </Card>
        ) : null}
      </div>
    </>
  );
}
