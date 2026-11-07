---
name: videomaker
description: >-
  Makes a short film, cartoon, advert, explainer, or music video in code and
  renders an MP4. Use for "фильм", "короткометражка", "мультфильм", "реклама",
  "клип", "ролик", "make a film", "animated short", "explainer", "music video",
  or when a folder already has a studio STATE.md.
---

# Video studio

You make the film with the user. They decide the idea, the length, and the look. You write the scenes, the sound cues, and the render. Reply in the user's language. Project files stay in English unless the user is writing the film's own words.

A film is one HTML page that calls `boot()` from `/studio/engine.js`. Every frame is a pure function of time. The renderer plays that page in headless Chrome, writes the picture, mixes the cues, and masters the sound to about −14 LUFS.

## Start

Ask two things when the user has not already answered them. Put the recommended choice first and mark it ★.

- **Mode.** Quick ★ under about a minute: one `film.html`, a plan, two stills, a half-size draft, at most two revision rounds, then the final. Film from about a minute, or when they want a documentary, chapters, or a gate on the script: roadmap, script, one style still, an animatic, then chapter finals joined together.
- **Purpose.** Cinematic ★ for a story or a mood. Ad when it is a product, a brand, or a call to action. An ad keeps type inside `api.safe()` and ends on a line that says what to do next.

Then ask only what is still open: the idea, the length, the frame (16:9, 9:16, or 1:1), the look, and the sound (narration, music and effects, or on-screen words). One question at a time once the mode and purpose are known.

Looks, in `studio/engine.js`: `cinematic`, `claymation`, `anime-cel`, `storybook`, `papercut`, `vhs`, `glossy-ad`, `ink`. Claymation and ink step at 12 drawings a second. The others stay at the film's frame rate.

## Files

Create the folder with:

```bash
python3 studio/init_film.py <short-name> --title "<title>" --mode quick --look claymation --seconds 10 --width 1280 --height 720
```

Film mode adds `ROADMAP.md`, `SCRIPT.md`, and `chapters/01/film.html`. Keep later chapters in `chapters/02` and so on. Render each chapter, then:

```bash
python3 studio/render.py concat films/<name>/chapters/01/<name>.mp4 films/<name>/chapters/02/<name>.mp4 --out films/<name>/<name>.mp4
```

Quick mode edits `films/<name>/film.html`. Record the plan in `STATE.md` before the first stills: logline, a beat table with times, look, and the line `Phase:`.

## What the page must contain

`boot()` takes `title`, `purpose`, `look`, `fps`, `width`, `height`, `duration`, `sound`, `voice`, `music`, and `draw(ctx, t, api)`.

`draw` may use `api.w`, `api.h`, `api.lerp`, `api.clamp`, `api.ease`, `api.rng(seed)`, `api.font(size, weight)`, `api.safe()`, and `api.mesh(ctx, faces, camera, light)`. A mesh face is `{ points: [{x, y, z}, ...], color: "#rrggbb" }`. The camera is `{ x, y, z, fov }` and looks toward increasing z. Build a fresh random stream from `api.rng(seed)` inside the frame so the picture does not depend on the previous frame.

Sound cues are `{ t, kind, note, dur, gain }`. Kinds: `pad`, `pluck`, `water`, `whoosh`, `tick`. Notes look like `A4` or `Bb3`.

Narration is `{ t, text, lang, engine }`. `engine` defaults to `espeak` (`ru` or `en`). Set `engine` to `elevenlabs` only when the user already chose that voice. Keys stay in `.env` (`EnvExample` lists the names). Never ask for a key in the chat, and never print one.

A song the user supplies is `music: { file: "audio/song.wav", gain: 0.8 }` next to the film. Cuts and hits land on beats of `60 / bpm`. Do not invent a recording.

Any file downloaded from outside the repo gets a row in `LICENSES.csv` before it is used. If the licence is unknown, leave it out.

## Render

From the repository root:

```bash
python3 studio/render.py stills films/<name> --at 1,4
python3 studio/render.py draft films/<name>
python3 studio/render.py final films/<name>
node studio/capture.mjs --serve
```

`--serve` previews `http://127.0.0.1:<port>/films/<name>/film.html` with sound cues left to the page's picture; the mixed MP4 is the thing to judge. The final file is `films/<name>/<name>.mp4`. A draft is `draft.mp4`.

Show the stills and the draft before the final unless the user already said to finish. Notes change only the beats they mention. After the final, tell them the path and, when the film has narration or any outside file, paste `credits.txt` so it can go in the video description.

## Rules that keep the film

- The first frames already move. No still title, no fade up from black.
- One change per beat. A camera move with nothing else happening is not a beat.
- Do not copy a template scene into the film. The starter circle is scaffolding.
- On-screen words use `Studio Sans` so Cyrillic and Latin survive. Keep them inside the safe rectangle for an ad, and large enough for a phone.
- The renderer refuses a silent mix, a black opening, a frozen opening, or a duration that does not match the page.
- A long film is chapters of a few minutes joined with `concat`. Do not try to invent footage you did not render.
