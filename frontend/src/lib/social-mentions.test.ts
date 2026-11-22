import { parseMentionInput } from "./social";

describe("parseMentionInput", () => {
  it("accepts handles with or without @, separated by commas or spaces", () => {
    expect(parseMentionInput("@WebersLink, partner  @friend.one")).toEqual(["WebersLink", "partner", "friend.one"]);
  });

  it("drops invalid and duplicate handles", () => {
    expect(parseMentionInput("@a, A, bad-handle, @@b, ,")).toEqual(["a", "b"]);
    expect(parseMentionInput("x".repeat(31))).toEqual([]);
  });

  it("keeps at most 20 handles", () => {
    const many = Array.from({ length: 25 }, (_, index) => `user${index}`).join(" ");
    expect(parseMentionInput(many)).toHaveLength(20);
  });
});
