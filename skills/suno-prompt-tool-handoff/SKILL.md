---
name: suno-prompt-tool-handoff
description: Help Prompt Compiler prepare provider-safe prompts and handoff data for Suno/KIE generation and post-analysis tools.
---

# Suno Prompt Tool Handoff

- Compile one concise provider-ready prompt from structured lyrics, melody, and arrangement fields.
- Keep provider details out of Agent responsibilities: actual generation is handled by `providers.kie_suno.KieSunoProvider`.
- Include useful generation hints: genre, mood, vocal/instrumental, tempo, structure, instrumentation, production texture, and hook.
- Respect prompt length limits by prioritizing musical essentials over explanation.
- After generation, `tools.audio.summarize_generated_audio` may analyze downloaded audio and `tools.audio.render_waveform` may create a visualization.
- Do not include API keys, callback URLs, local absolute paths, or implementation details in the final prompt.
