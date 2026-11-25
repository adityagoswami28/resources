---
name: popup-explainer
description: Turn any topic into a short narrated explainer video that looks like a paper pop-up book opening page by page. Use when someone asks for an explainer video, a pop-up book video, or "explain X as a video".
license: MIT
metadata:
  version: "1.0.0"
---

# Pop-up Explainer

Makes a 20 to 60 second video: a closed book with the title on its cover lies on a desk, the cover opens and the first pop-up rises, a voice tells the story one page per idea, each page turns over to the next (the old pop-up folds into the turning page, the new one rises behind it), and at the end the cover swings shut on the closed book. The `title` in the storyboard is what is printed on the cover, so keep it short (up to about 40 letters).

You write **one small storyboard file**. The bundled engine does everything else. **Run the scripts, never read them**: everything you need is in this file and `references/storyboard.md`.

## Steps

1. **Story first.** From the topic, write 3 to 6 pages. One idea per page, one or two spoken sentences each (about 15 to 25 words). Start with a hook, end with the point. If the person gave facts or data, use theirs and do not invent numbers.
2. **Pick the look** (ask only if the person cares): `cut-paper` (default, warm and friendly), `risograph` (bright print), `field-atlas` (soft watercolour), `night-lantern` (glowing, dark), `gilded-engraving` (old book).
   Then make the book fit **this topic**, so no two videos look or sound alike:
   - `cover`: a colour that suits the topic and a picture from the story, e.g. `{"colour":"#b7791f","piece":"bee"}` (honey → amber, ocean → deep blue, money → dark green).
   - `music`: the mood of the tune: `gentle`, `bright`, `curious`, `dreamy` or `stately` (`none` for no music). The title decides the notes, so every topic gets its own tune.
   - `air`: the background sound: `birds` (outdoors by day), `night` (crickets), `quiet` (indoors, ideas, money, machines).
3. **Write the storyboard** as `<name>.json`. Read `references/storyboard.md` once for the format. Start from `examples/bees.json` if useful.
   - For each page decide the **one thing the viewer must see**. Use a ready-made piece if one fits. If none fits, **draw it** from shapes (see "Drawing a new piece"). Never bend the story to fit the ready-made list.
   - Give every video at least one drawn-for-this-story centrepiece.
4. **Preview**: `python scripts/popup.py <name>.json --preview`
   It prints one line per problem (`CHECK page 2: …`) and writes one picture, `<name>-preview.png`: the cover first, then every page. A piece that pokes off its sheet is slid back in for you (`FITTED …`, nothing to do). Fix each CHECK line, then look at the picture **once**. Ask of each page: is the main thing big and obvious? does it match the sentence? Fix and preview again only if something is wrong (repeat previews take seconds).
5. **Make the video**: `python scripts/popup.py <name>.json` → `<name>.mp4` (about 2 to 3 minutes for 30 seconds of video). It speaks the `say` lines, fits each page to its sentence and mixes in the tune and paper sounds. The last line printed names the voice used, e.g. `voice: free (af_heart)`.
6. Give the person the video. Offer one change at a time.

## Example

Ask: "Make a pop-up explainer about how bees make honey." The storyboard for that ask is `examples/bees.json`: 3 pages, the `cut-paper` look, an amber cover with a bee, `gentle` music and `birds` in the background. Preview it with `python scripts/popup.py examples/bees.json --preview`, or copy it as a starting point for a new topic.

## Rules that keep pages looking good

- The main piece of a page goes on `far`, `left` or `right` and stands **0.7 to 0.85 tall**. Smaller and the page looks empty.
- Fill the layers: something far (hills, sun), something in the middle, something low in front (grass, a label).
- Keep thin things (stems, posts) away from x = 0. That is the fold of the book.
- Hills must not be the same colour as the floor.
- Flying things: size 0.12 or more.
- The top of a sun with rays sits at y + s × 0.8, so keep that under 0.9.
- Words on the page: 1 to 4 words per label, at most two labels a page. The voice carries the explanation.

## Voice

Nothing to set up. The free voice runs on the machine (first use downloads about 120 MB once). If `ELEVENLABS_API_KEY` is set, the premium voice is used instead; only the narration text is sent. On a Mac with neither, the built-in voice is used. If no voice is available the video still gets made, with paper sounds only, and the last line says `voice: none`: tell the person.

Optional in the storyboard: `"voice":{"name":"am_michael","speed":0.95}` (free voices include `af_heart` default, `af_bella`, `am_michael`, `bf_emma`, `bm_george`; for premium, `name` is the voice id). `--no-voice` skips narration.

Write `say` lines for the ear: short sentences, numbers as words ("seven percent"), no brackets or symbols.

## Setup

Python 3.10+ and `ffmpeg`. Install the Python parts into their own folder (a plain `pip install` is refused on many Macs and Linux machines):

```
python3 -m venv ~/.popup-venv
~/.popup-venv/bin/pip install skia-python numpy scipy kokoro-onnx soundfile
```

Then run the scripts with `~/.popup-venv/bin/python` in place of `python`. If something is missing the script says so in one line (`SETUP missing: …`).

## Make it your own

Every choice lives in the storyboard, so the engine never needs editing:

- **Look:** `style`, one of the 5 looks.
- **Cover:** `cover`, a colour and a picture from the story.
- **Sound:** `music` (a mood or `none`) and `air` (the background sound).
- **Voice:** `voice`, any of the free voices, or your own premium voice id.
- **Pictures:** your own `pieces`, drawn from shapes (see "Drawing a new piece" in `references/storyboard.md`).
