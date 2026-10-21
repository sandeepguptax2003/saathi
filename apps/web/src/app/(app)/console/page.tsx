import type { Metadata } from "next";

import { VoiceConsole } from "@/features/chat/components/VoiceConsole";

export const metadata: Metadata = { title: "Console" };

export default function ConsolePage() {
  return <VoiceConsole />;
}
