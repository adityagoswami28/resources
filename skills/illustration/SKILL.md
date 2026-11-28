---
name: illustration
description: Draw hand-drawn sketchbook pictures (grid paper, black pen, pencil, marker washes) for any post. 30 kinds of picture, each for one kind of idea, plus hand-drawn app logos and icons, sized for Instagram, X, LinkedIn, blogs (day and night) and newsletters. Use when a post needs a picture, cover, carousel or diagram, or when asked to "draw", "illustrate" or "sketch" an idea.
license: MIT
metadata:
  version: "1.0.0"
---

# Illustration

Turns one idea into a finished hand-drawn picture: grid paper, black pen, a pencil, soft marker washes, taped-in paper and hand lettering. Every picture looks like it came from the same notebook, in the right size for each app.

You write **one small post file** (JSON). The bundled engine draws it. **Run the scripts, never read them**: everything you need is in this file and `references/pictures.md`.

## First run: setup (3 questions)

Open `brand.json` (next to this file). If `"setup_done"` is `false`, ask these 3 questions before the first picture, **one at a time**. Show the 3 answers, mark the recommended one, and always offer "type your own".

**1. What goes in the corner of every picture?**
- a) **Your name and handle, in handwriting** (recommended). Then ask for: the name, the handle (like `@yourname`) and the website (blog pictures show the website).
- b) **Your logo image and handle.** Ask for the path of an SVG or PNG file. Optional: a light version for night pictures.
- c) **Nothing.** Clean pictures, no corner.
- Type your own: for example only the website, or a different handle per app.

**2. Which colors?**
- a) **Notebook**: cream paper, navy headlines, blue pen, peach wash (recommended)
- b) **Sea**: white paper, pale teal wash, coral pen
- c) **Ink**: white paper, grey wash, red pen
- Type your own: 4 colors, for example from a brand guide: `soft` (the big wash), `accent` (the one pen mark to notice), `highlight` (the highlighter), `deep` (headlines), and optionally `paper`. Hex codes like `#1D3557`.

**3. Which paper?**
- a) **Grid** (recommended)
- b) **Dots**
- c) **Plain** (no lines)
- Type your own: a paper color (hex), on grid, dots or plain.

Then:
1. Write the answers into `brand.json` (fields below) and run `python3 scripts/brand.py`. Fix any line that starts with `PROBLEM`.
2. Draw one sample with their brand: `python3 scripts/sketch.py examples/carousel.json --out preview --format ig-portrait --only 1,3` and show both pictures.
3. If they like it, set `"setup_done": true`. If not, change the one thing they name and draw again.

| `brand.json` field | What it holds |
|---|---|
| `name`, `handle`, `site` | your name, your handle on Instagram, X and LinkedIn, your website (blog and newsletter pictures) |
| `handles` | optional: a different handle per app, e.g. `{"x": "@other", "linkedin": "Your Name"}` |
| `corner` | `"name"`, `"file"` or `"none"` |
| `logo_file`, `logo_file_night` | your logo image (path from this folder, or a full path); the night one is optional |
| `colors` | `"notebook"`, `"sea"`, `"ink"`, or `{"soft": "#…", "accent": "#…", "highlight": "#…", "deep": "#…", "paper": "#…"}` |
| `paper`, `paper_color` | `"grid"`, `"dots"` or `"plain"`; optional day paper color |

## Steps

1. **Pick the picture.** Fill these lines before drawing anything:
   - **The point** in one sentence: what should a stranger know after 2 seconds? One idea per picture. Take it from the person's words; never add facts.
   - **The shape** of that idea, in plain words: one becomes many? A versus B? Steps in order? A loop? Parts of a whole? A number?
   - **The picture**: the 1 of 30 with that shape (`python3 scripts/sketch.py --list`, or "Shape quick pick" in `references/pictures.md`). Pick by shape, never by looks.
   - **The one thing to notice**: one part gets the colored pen (`pick`), one phrase of the headline gets the highlighter (`==words==`).
   - **The job**: `save` (they will need it again), `send` (it fits someone they know) or `repost` (a clear claim they agree with).
2. **Write the post file** `<name>.json`. Read `references/pictures.md` once for the fields and each picture's data. Start from `examples/carousel.json`.
3. **Check:** `python3 scripts/sketch.py <name>.json --check`. Fix every warning.
4. **Draw:** `python3 scripts/sketch.py <name>.json --out OUT --format ig-portrait` (every format is in `references/pictures.md`; blog pictures: `--format blog-inline,blog-square --theme both`).
5. **Look at every picture** before showing anyone: no words running into each other, nothing cut off, the drawing big and centered, one pen mark, one highlight. Fix and draw again.
6. Give the person the pictures with their alt text. Offer one change at a time.

## Example

Ask: *"Make an Instagram carousel: 4 ways to write a better prompt."* The post file for that ask is `examples/carousel.json`: 5 images, a cover (`anatomy`: a good prompt and its 4 parts), then one fix per image (`fix`, `compare`, `prompt`, `checklist`), each with a headline, one highlight, a "next" hint and alt text. Draw it with:

```
python3 scripts/sketch.py examples/carousel.json --out OUT --format ig-portrait
```

`examples/blog.json` is the same idea as two blog pictures (day and night), and `examples/icons.json` shows the hand-drawn icons.

## Rules that keep pictures good

- **One of each per picture:** one idea, one colored pen mark, one highlight.
- **The headline states the point.** Labels inside the drawing: 1 to 4 words each.
- **Real numbers only** in `bars`, `curve`, `bignumber`, `donut` and `funnel`. The pen wobbles, the numbers never do.
- **Icons are a sprinkle:** about 1 image in 3. App logos appear by themselves when a label names the app.
- **Alt text says the point**, not the look.
- Carousels: 1 image, or 5 and more (2 to 4 do worst).

## Setup

Python 3 and Chrome or Chromium. Nothing to install with pip: the fonts are bundled, and it needs no internet.

- Chrome is found by itself on a Mac and on most Linux machines. If not, set `CHROME=/path/to/chrome`.
- Put this folder where your agent reads skills. For Claude Code that is `.claude/skills/` in a project, or `~/.claude/skills/` for every project. Other agents: point them at this folder and its `SKILL.md`.

If something is missing the script says so in one line.

## Make it your own

Everything that makes the pictures yours lives in **`brand.json`**, so the engine never needs editing:

- **Corner:** your name and handle, your logo image, or nothing.
- **Colors:** one of 3 palettes, or your own 4 colors. The engine works out every other shade, and the night version, from them.
- **Paper:** grid, dots or plain, in any color.
- **Handles:** one for every app, or a different one per app.
- **A second brand:** keep another file and run with `BRAND_FILE=other.json`.
- **More pictures, logos or icons:** see "Adding a picture" and "Adding a logo or icon" in `references/pictures.md`.
- **Fonts:** Young Serif (headlines), Atkinson Hyperlegible (reading text), Gochi Hand (handwriting), set in `scripts/sketch.css`.
