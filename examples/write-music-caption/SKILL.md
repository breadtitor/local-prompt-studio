---
name: write-music-caption
description: Turn a short music brief and optional bracketed section directions into a structured, section-aware caption for a music-generation workflow. Use when a user needs musical identity, vocal treatment, and an evolving arrangement expressed without copying lyrics or inventing unsupported precision.
---

# Write Music Caption

Create a new production-oriented music caption from the user's brief. Read
[`references/format.md`](references/format.md) and follow its three-section contract exactly.

## Workflow

1. Extract explicit genre, mood, tempo character, groove, vocal presence, instruments, section
   changes, production texture, and exclusions.
2. Treat bracketed labels such as `[Intro]`, `[Chorus]`, or `[Instrumental]` as arrangement
   directions. Do not quote, rewrite, or summarize lyric lines.
3. Preserve hard constraints. An instrumental request must stay instrumental; do not reverse a
   specified vocal type, required instrument, tempo boundary, or prohibited element.
4. Infer only what is needed for a coherent result. Prefer a tempo range or qualitative pace when
   the brief does not justify an exact BPM, key, scale, or production technique.
5. Build an arrangement in which instruments enter, change, and leave deliberately. Describe a
   readable energy arc rather than a static list of equipment.
6. Return only the finished caption. Do not add a title, template identifier, track identifier,
   analysis, or fenced code block.

Use English unless the user explicitly requests another language.
