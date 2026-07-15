---
name: arrangement-audio-analysis
description: Help Arrange Agent use audio inspection, preview, and waveform outputs for arrangement decisions.
---

# Arrangement Audio Analysis

- Use `tools.audio.inspect_audio` metadata to reason about duration, density, and technical format.
- Use `tools.audio.trim_audio_preview` output as a short reference clip location, not as text content.
- Use `tools.audio.render_waveform` output to infer broad energy shape only when available.
- Do not infer exact chords, lyrics, artist, or instrumentation from metadata alone.
- Translate reference constraints into instrumentation, texture, section development, and production direction.
- Keep the Suno provider boundary separate: Arrange describes music; Prompt Compiler prepares provider-ready text.
