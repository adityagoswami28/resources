# Pop-up Explainer

Give it a topic. It makes a short narrated video that looks like a paper pop-up book, opening page by page.

A closed book lies on a desk with the title on its cover. The cover opens, a pop-up rises, and a voice tells the story, one page per idea. Each page turns over to the next. At the end the cover swings shut.

**Works with any AI agent** that can read a skill folder and run Python. Version 1.0.0, MIT license.

## Setup

1. Put this folder where your agent reads skills. For Claude Code that is `.claude/skills/` in a project, or `~/.claude/skills/` for every project. Other agents: point them at this folder and its `SKILL.md`.
2. Once, on the computer that makes the videos, install Python 3.10+ and `ffmpeg`, then:

```
python3 -m venv ~/.popup-venv
~/.popup-venv/bin/pip install skia-python numpy scipy kokoro-onnx soundfile
```

The free voice downloads about 120 MB the first time. If anything is missing, the script says what in one line.

## Example

Ask your agent: *"Make a pop-up explainer about how volcanoes erupt."* It writes a story of 3 to 6 pages, checks one preview picture of every page, then makes the video with the voice, a tune and paper sounds (about 2 to 3 minutes of making for 30 seconds of video). `examples/bees.json` is a finished storyboard to look at.

## Make it your own

Ask for any of these, or let the skill pick:

| Choice | Options |
|---|---|
| Look | `cut-paper`, `risograph`, `field-atlas`, `night-lantern`, `gilded-engraving` |
| Cover | a colour and a picture from your story |
| Music | `gentle`, `bright`, `curious`, `dreamy`, `stately` or `none` |
| Background sound | `birds`, `night` or `quiet` |
| Voice | free voices `af_heart`, `af_bella`, `am_michael`, `bf_emma`, `bm_george` |

Your own pieces can be drawn from simple shapes: see `references/storyboard.md`.

## Known limits

- English narration only.
- The premium voice (set `ELEVENLABS_API_KEY`) is written but not tested yet.

## Folder map

```
SKILL.md                  what the agent reads
references/storyboard.md  the storyboard format, pieces, colours
examples/bees.json        a finished storyboard
scripts/                  the engine (popup.py is the command)
CHANGELOG.md              what changed in each version
LICENSE                   MIT
```
