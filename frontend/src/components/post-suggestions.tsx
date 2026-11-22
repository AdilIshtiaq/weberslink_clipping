"use client";

import { useEffect, useRef, useState } from "react";
import { Copy, Loader2, RefreshCw, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";

import { PostSuggestionsPanel } from "@/components/post-suggestions-panel";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCopyText } from "@/lib/copy-text";
import { MENTION_STORAGE_KEY, parseMentionInput, type PostPackSuggestions } from "@/lib/social";
import { cn } from "@/lib/utils";

type Platform = "tiktok" | "instagram" | "youtube";
const PLATFORMS: { id: Platform; labelKey: "tiktok" | "instagram" | "youtube" }[] = [
  { id: "tiktok", labelKey: "tiktok" },
  { id: "instagram", labelKey: "instagram" },
  { id: "youtube", labelKey: "youtube" },
];

interface Pack {
  caption: string;
  hashtags: string[];
  mentions: string[];
  suggestions: PostPackSuggestions;
}

const strings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];

async function readError(response: Response, fallback: string): Promise<string> {
  const data = await response.json().catch(() => ({}));
  if (typeof data?.detail === "string") return data.detail;
  if (typeof data?.error === "string") return data.error;
  return fallback;
}

/** "Post ideas" for a finished clip: caption, hashtags, mentions, location and music to copy into a post. */
export function PostSuggestionsButton({ taskId, clipId, className }: { taskId: string; clipId: string; className?: string }) {
  const t = useTranslations("social");
  const copyToClipboard = useCopyText();
  const [open, setOpen] = useState(false);
  const [platform, setPlatform] = useState<Platform>("tiktok");
  const [mentionList, setMentionList] = useState("");
  const [pack, setPack] = useState<Pack | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef(0);

  const generate = async (target: Platform, mentionText = mentionList) => {
    const request = ++latest.current;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/social/captions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: taskId, clip_id: clipId, provider: target, mentions: parseMentionInput(mentionText) }),
      });
      if (!response.ok) throw new Error(await readError(response, t("captionFailed")));
      const data = await response.json();
      if (typeof data.caption !== "string" || !data.caption.trim()) throw new Error(t("captionFailed"));
      if (request !== latest.current) return;
      setPack({
        caption: data.caption,
        hashtags: strings(data.hashtags),
        mentions: strings(data.mentions),
        suggestions: {
          location: typeof data.location === "string" ? data.location : "",
          musicStyle: typeof data.music?.style === "string" ? data.music.style : "",
          musicTip: typeof data.music?.tip === "string" ? data.music.tip : "",
          whyViral: typeof data.why_viral === "string" ? data.why_viral : "",
        },
      });
    } catch (err) {
      if (request === latest.current) setError(err instanceof Error ? err.message : t("captionFailed"));
    } finally {
      if (request === latest.current) setLoading(false);
    }
  };

  useEffect(() => {
    if (!open) latest.current++;
  }, [open]);

  const openDialog = () => {
    let saved = "";
    try {
      saved = window.localStorage.getItem(MENTION_STORAGE_KEY) ?? "";
    } catch {
      /* storage can be unavailable; the field starts empty */
    }
    setMentionList(saved);
    setPack(null);
    setOpen(true);
    void generate(platform, saved);
  };

  const hashtagText = pack ? pack.hashtags.map((tag) => `#${tag}`).join(" ") : "";
  const fullPost = pack
    ? [pack.caption, pack.mentions.join(" "), hashtagText].filter((part) => part.trim()).join("\n\n")
    : "";

  return (
    <>
      <Button type="button" size="sm" variant="outline" className={className} onClick={openDialog}>
        <Sparkles className="size-4" />
        {t("ideas.button")}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("ideas.title")}</DialogTitle>
            <DialogDescription>{t("ideas.description")}</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t("ideas.platform")}</Label>
              <div className="flex flex-wrap gap-2" role="group" aria-label={t("ideas.platform")}>
                {PLATFORMS.map((item) => (
                  <Button
                    key={item.id}
                    type="button"
                    size="sm"
                    variant={platform === item.id ? "default" : "outline"}
                    aria-pressed={platform === item.id}
                    disabled={loading}
                    onClick={() => {
                      setPlatform(item.id);
                      void generate(item.id);
                    }}
                  >
                    {t(`ideas.platforms.${item.labelKey}`)}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor={`ideas-mentions-${clipId}`}>{t("mentionsLabel")}</Label>
              <Input
                id={`ideas-mentions-${clipId}`}
                value={mentionList}
                placeholder={t("mentionsPlaceholder")}
                onChange={(event) => {
                  setMentionList(event.target.value);
                  try {
                    window.localStorage.setItem(MENTION_STORAGE_KEY, event.target.value);
                  } catch {
                    /* not saved, still used for this session */
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">{t("mentionsHint")}</p>
            </div>

            {loading && (
              <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
                <Loader2 className="size-4 animate-spin" />
                {t("ideas.generating")}
              </p>
            )}
            {error && <p className="text-sm text-destructive" role="alert">{error}</p>}

            {pack && (
              <div className={cn("space-y-4", loading && "opacity-60")}>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">{t("ideas.caption")}</p>
                    <Button type="button" size="sm" variant="ghost" aria-label={t("ideas.copyCaption")} onClick={() => void copyToClipboard(pack.caption)}>
                      <Copy className="size-4" />
                    </Button>
                  </div>
                  <p className="whitespace-pre-line rounded-lg border bg-muted/30 p-3 text-sm" data-testid="idea-caption">{pack.caption}</p>
                </div>

                {pack.hashtags.length > 0 && (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{t("ideas.hashtags")}</p>
                      <Button type="button" size="sm" variant="ghost" aria-label={t("ideas.copyHashtags")} onClick={() => void copyToClipboard(hashtagText)}>
                        <Copy className="size-4" />
                      </Button>
                    </div>
                    <p className="rounded-lg border bg-muted/30 p-3 text-sm" data-testid="idea-hashtags">{hashtagText}</p>
                  </div>
                )}

                {pack.mentions.length > 0 && (
                  <p className="text-sm" data-testid="idea-mentions">
                    <span className="font-medium">{t("ideas.mentions")}</span> {pack.mentions.join(" ")}
                  </p>
                )}

                <PostSuggestionsPanel suggestions={pack.suggestions} />
              </div>
            )}
          </div>

          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <Button type="button" variant="outline" disabled={loading} onClick={() => void generate(platform)}>
              <RefreshCw className="size-4" />
              {t("ideas.regenerate")}
            </Button>
            <Button type="button" disabled={!pack || loading} onClick={() => void copyToClipboard(fullPost)}>
              <Copy className="size-4" />
              {t("ideas.copyAll")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
