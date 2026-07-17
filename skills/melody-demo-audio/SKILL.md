---
name: melody-demo-audio
description: Help 旋律南郭 prepare simple melodic plans that can produce intermediate demo audio.
---

# Melody Demo Audio

- Write melody plans with explicit tempo, rhythm feel, hook contour, harmony, and emotional arc.
- If a local demo is requested, the structured melody plan may be passed to `tools.demo_audio.render_prompt_demo_audio`.
- The demo tool creates a lightweight synthetic reference, not a final production track.
- Keep score specs simple enough for MusicXML/MIDI export: practical pitch names, positive durations, and limited part count.
- Prefer clear motifs and stable tempo over dense ornamentation when downstream demo rendering is expected.
