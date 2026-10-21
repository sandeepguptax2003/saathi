"use client";

import { Badge } from "@/components/ui/badge";
import type { MessageKey } from "@/lib/i18n/dictionaries";
import { useT } from "@/lib/i18n/I18nProvider";
import type { EntityCounts } from "@/types/api";

const KNOWN = new Set([
  "phone",
  "email",
  "aadhaar",
  "pan",
  "upi",
  "card",
  "account",
  "ifsc",
  "name",
]);

export function entityLabelKey(entity: string): MessageKey | null {
  const key = entity.toLowerCase();
  return KNOWN.has(key) ? (`privacy.entity.${key}` as MessageKey) : null;
}

/** Shows only counts and token placeholders, never raw values. */
export function EntityCountList({ counts }: { counts: EntityCounts }) {
  const t = useT();
  const entries = Object.entries(counts).filter(([, n]) => n > 0);
  return (
    <ul className="flex flex-wrap gap-2" data-testid="entity-counts">
      {entries.map(([entity, n]) => {
        const labelKey = entityLabelKey(entity);
        return (
          <li key={entity}>
            <Badge variant="secondary" className="gap-1.5 font-mono">
              <span className="font-sans">{labelKey ? t(labelKey) : entity}</span>
              <span aria-hidden="true">&lt;{entity.toUpperCase()}_n&gt;</span>
              <span>×{n}</span>
            </Badge>
          </li>
        );
      })}
    </ul>
  );
}
