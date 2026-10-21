"use client";

import { SendIcon, SquareIcon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useT } from "@/lib/i18n/I18nProvider";

export function Composer({
  onSend,
  onStop,
  streaming,
}: {
  onSend: (text: string) => void;
  onStop: () => void;
  streaming: boolean;
}) {
  const t = useT();
  const [text, setText] = useState("");

  function submit() {
    const value = text.trim();
    if (!value || streaming) return;
    onSend(value);
    setText("");
  }

  return (
    <form
      className="flex items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <label htmlFor="console-input" className="sr-only">
        {t("console.placeholder")}
      </label>
      <Textarea
        id="console-input"
        rows={1}
        value={text}
        placeholder={t("console.placeholder")}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
        className="max-h-40 min-h-11 resize-none"
      />
      {streaming ? (
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={onStop}
          aria-label={t("console.stop")}
        >
          <SquareIcon aria-hidden="true" />
        </Button>
      ) : (
        <Button type="submit" size="icon" aria-label={t("console.send")} disabled={!text.trim()}>
          <SendIcon aria-hidden="true" />
        </Button>
      )}
    </form>
  );
}
