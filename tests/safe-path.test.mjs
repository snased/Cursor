import assert from "node:assert/strict";
import test from "node:test";

import { safePath } from "../studio/capture.mjs";

test("serves a file inside the repo root", () => {
  assert.equal(safePath("/repo", "/films/paper-boat/film.html"), "/repo/films/paper-boat/film.html");
});

test("rejects paths that climb out of the root", () => {
  assert.equal(safePath("/repo", "/../../etc/passwd"), null);
  assert.equal(safePath("/repo", "/%2e%2e/%2e%2e/etc/passwd"), null);
  assert.equal(safePath("/repo", "/"), null);
});
