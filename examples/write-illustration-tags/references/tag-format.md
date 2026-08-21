# Required output format

Return exactly these Markdown headings in this order:

### Positive Prompt

Write one comma-delimited English tag list. Begin with these quality and resolution tags:
`masterpiece`, `best quality`, `absurdres`, and `highres`. Then describe the requested image in a
useful order: subject count, identity or explicitly supplied style, appearance and clothing,
action, composition, setting, lighting, mood, and detail. Prefer 12–90 tags.

### Negative Prompt

Write one comma-delimited English tag list. Include at least four applicable quality or anatomy
baseline tags from this set: `worst quality`, `low quality`, `lowres`, `bad anatomy`, `bad hands`,
`extra digits`, `fewer digits`, `missing fingers`, `extra limbs`, `text`, `watermark`,
`signature`, `username`, `jpeg artifacts`, `blurry`, and `unfinished`. Then add only requested or
scene-relevant exclusions. Prefer 4–50 tags.

Do not repeat a normalized tag within either list or across the two lists. Treat underscores and
spaces as equivalent for this check. Do not use a negative tag that reverses an explicit positive
requirement.
