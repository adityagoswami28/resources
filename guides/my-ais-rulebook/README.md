# My AI's rulebook

Ten plain rules your AI reads before every job, so the same slip never happens twice. One short file (`SKILL.md`) that any AI can read. Version 1.0.0, MIT license.

## Setup

Pick one way:

1. **Saved instructions (best):** copy the numbered rules from `SKILL.md` into your AI's saved or custom instructions. It reads them before every job.
2. **A project:** add `SKILL.md` to a project, so every chat in that project follows it.
3. **A skill:** put this whole folder where your AI agent reads skills. It already has the `SKILL.md` a skill needs.

## Example

You ask for a new logo.

- **Without the rules:** it makes 30 versions in one go, guesses your colors, and you look through all of them.
- **With rule 1:** it tells you back what you asked for, makes one first draft, and you build on that.

## Make it your own

Add a line each time your AI slips:

1. **Name the slip in plain words.** Not "the output was off". Say what happened: "it guessed my city".
2. **Write the fix as one line, to your AI.** Say what it should do, not what it did wrong: "If you don't know a fact about me, ask."
3. **Put it where the AI reads it every time.** A rule in a chat it will never see again doesn't count.
4. **Check the next run.** If the slip comes back, the line isn't clear enough yet. Rewrite it.

Rules you don't need can go. Keep the list short enough to read in a minute.
