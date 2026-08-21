---
name: write-illustration-tags
description: Turn a natural-language image idea into separate positive and negative comma-delimited English tag lists for a tag-oriented local illustration workflow. Use when the target accepts concise tags rather than prose and needs independently inspectable prompt structure.
---

# Write Illustration Tags

Turn the user's image idea into a compact positive tag list and a focused negative tag list.
Read [`references/tag-format.md`](references/tag-format.md) and return its two headings exactly.

## Workflow

1. Preserve explicit subject count, age when supplied, appearance, clothing, action, composition,
   environment, lighting, mood, text requirements, and exclusions. Ask a follow-up instead of
   inventing a named character, franchise, artist, custom model, LoRA, or watermark.
2. Translate ordinary language into concrete English tags. Keep each tag short and meaningful;
   avoid sentence fragments, duplicate synonyms, or sampler settings.
3. Put positive tags in a deliberate order: quality and resolution, subject count, identity or
   supplied style tags, appearance, action, framing, environment, lighting, then finishing
   detail. Choose one framing unless the user explicitly requests a multi-panel image.
4. Add only relevant failure modes and explicit exclusions to the negative list. Remove any
   default negative tag that conflicts with an explicit positive request.
5. Never sexualize a minor or an age-ambiguous young-looking subject. If the request makes age
   material, use the user's explicit adult constraint or keep the result non-sexual.
6. Return only the two completed tag lists. Do not add prose, a title, a Markdown fence, JSON, or
   sampler settings.

Use English unless the user explicitly asks for another language. Keep the tags ASCII so they are
easy to paste into local model interfaces.
