import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { PostSuggestionsButton } from "./post-suggestions";

const pack = {
  caption: "Can he finish before the clock hits ZERO?! 👀\nThe final moments are INSANE! 🔥",
  hashtags: ["GTA6", "Challenge"],
  location: "Los Angeles, USA",
  music: { style: "tense cinematic build", tip: "Search for suspense beats and keep it quiet under speech" },
  why_viral: "A countdown creates a clear reason to watch to the end.",
  mentions: ["@WebersLink"],
};

let writeText: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.resetAllMocks();
  window.localStorage.clear();
  writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  vi.stubGlobal("fetch", vi.fn(async () => Response.json(pack)));
});

const bodyOfCall = (index: number) => JSON.parse((vi.mocked(fetch).mock.calls[index][1] as RequestInit).body as string);

it("writes the post when opened, without any connected account", async () => {
  render(<PostSuggestionsButton taskId="task-1" clipId="clip-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Post ideas" }));
  await waitFor(() => expect(screen.getByTestId("idea-caption")).toHaveTextContent("Can he finish before the clock hits ZERO?!"));
  expect(bodyOfCall(0)).toEqual({ task_id: "task-1", clip_id: "clip-1", provider: "tiktok", mentions: [] });
  expect(screen.getByTestId("idea-hashtags")).toHaveTextContent("#GTA6 #Challenge");
  expect(screen.getByTestId("idea-mentions")).toHaveTextContent("@WebersLink");
  const panel = screen.getByTestId("post-suggestions");
  expect(panel).toHaveTextContent("A countdown creates a clear reason");
  expect(panel).toHaveTextContent("Los Angeles, USA");
  expect(panel).toHaveTextContent("tense cinematic build");
});

it("sends the saved accounts to tag", async () => {
  window.localStorage.setItem("weberslinkclip.post-mentions", "@WebersLink, partner");
  render(<PostSuggestionsButton taskId="task-1" clipId="clip-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Post ideas" }));
  await waitFor(() => expect(screen.getByTestId("idea-caption")).toBeInTheDocument());
  expect(bodyOfCall(0).mentions).toEqual(["WebersLink", "partner"]);
});

it("writes a new post when the platform changes", async () => {
  render(<PostSuggestionsButton taskId="task-1" clipId="clip-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Post ideas" }));
  await waitFor(() => expect(screen.getByTestId("idea-caption")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "Instagram" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(bodyOfCall(1).provider).toBe("instagram");
  expect(screen.getByRole("button", { name: "Instagram" })).toHaveAttribute("aria-pressed", "true");
});

it("copies the caption, tags and hashtags as one post", async () => {
  render(<PostSuggestionsButton taskId="task-1" clipId="clip-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Post ideas" }));
  await waitFor(() => expect(screen.getByTestId("idea-caption")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "Copy full post" }));
  await waitFor(() => expect(writeText).toHaveBeenCalled());
  expect(writeText).toHaveBeenCalledWith(`${pack.caption}\n\n@WebersLink\n\n#GTA6 #Challenge`);
});

it("shows the server's message when it fails", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail: "Post suggestions need an AI model key on the server." }, { status: 503 })));
  render(<PostSuggestionsButton taskId="task-1" clipId="clip-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Post ideas" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Post suggestions need an AI model key on the server.");
  expect(screen.getByRole("button", { name: "Copy full post" })).toBeDisabled();
});
