# Agent skill

**English** · [简体中文](../agent-skill.md)

The repository includes `.agents/skills/render-midi/SKILL.md`. The skill composes to a brief, chooses sounds, works with each engine's characteristics, calls the same command-line tool and delivers the files; all synthesis happens in the command-line tool.

Use it in an agent workspace that discovers that folder, or install the whole skill folder the way your agent expects. For a user-level install, keep the `references` folder, which holds the sound-selection and composing guides. Install `midi-orchestra` and prepare your private configuration first.

Example requests:

- "Use render-midi to write a 20-second upbeat transition with pluck and synth bass, and give me the WAVs and source credits."
- "Use render-midi to turn this MIDI into a soft pad, and give me a WAV to listen to plus the source credits."

The agent writes a multi-track MIDI file to match the style, length, tempo and key, saves the generating script next to the MIDI so the piece is easy to revise, then renders each track and returns the audio. The skill is discovered and invoked like any other, needs no MCP server and contains no account credentials. You judge how it sounds; the agent tells you which conclusions come from measurements and which sounds have been listened to.
