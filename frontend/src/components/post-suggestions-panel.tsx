"use client";

import { Copy } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { useCopyText } from "@/lib/copy-text";
import type { PostPackSuggestions } from "@/lib/social";

/** Why a clip can travel, a place to tag, and a music idea, each with a copy button. */
export function PostSuggestionsPanel({ suggestions }: { suggestions: PostPackSuggestions }) {
  const t = useTranslations("social");
  const copyToClipboard = useCopyText();
  if (!suggestions.location && !suggestions.musicStyle && !suggestions.whyViral) return null;

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-3" data-testid="post-suggestions">
      <p className="text-sm font-medium">{t("suggestions.title")}</p>
      {suggestions.whyViral && (
        <div className="space-y-0.5">
          <p className="text-xs font-medium text-muted-foreground">{t("suggestions.whyViral")}</p>
          <p className="text-sm">{suggestions.whyViral}</p>
        </div>
      )}
      {suggestions.location && (
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-0.5">
            <p className="text-xs font-medium text-muted-foreground">{t("suggestions.location")}</p>
            <p className="text-sm">{suggestions.location}</p>
          </div>
          <Button type="button" size="sm" variant="ghost" aria-label={t("suggestions.copyLocation")} onClick={() => void copyToClipboard(suggestions.location)}>
            <Copy className="size-4" />
          </Button>
        </div>
      )}
      {suggestions.musicStyle && (
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-0.5">
            <p className="text-xs font-medium text-muted-foreground">{t("suggestions.music")}</p>
            <p className="text-sm">{suggestions.musicStyle}</p>
            {suggestions.musicTip && <p className="text-xs text-muted-foreground">{suggestions.musicTip}</p>}
            <p className="text-xs text-muted-foreground">{t("suggestions.musicNote")}</p>
          </div>
          <Button type="button" size="sm" variant="ghost" aria-label={t("suggestions.copyMusic")} onClick={() => void copyToClipboard(suggestions.musicStyle)}>
            <Copy className="size-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
