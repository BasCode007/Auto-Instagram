# Voice: VoiceStudio (replaces ElevenLabs)

VoiceStudio (AGPL, github.com/debpalash/VoiceStudio) runs as the `voice`
container under the `gpu` profile and speaks an OpenAI-compatible API:

- `POST /v1/audio/speech` — text in, MP3 out. Engine **OmniVoice** with a
  free-text voice-design instruction (`VOICE_INSTRUCT`), or a cloned voice
  profile by name/ID (`VOICE_PROFILE`) that you create once in its UI at
  http://localhost:3900 from a clean 10–30 s reference recording.
- `POST /v1/audio/transcriptions` — Whisper with word timestamps, which gives
  the captions their word-perfect timing.

The renderer uses it whenever `VOICE_BASE_URL` is set (default
`http://voice:3900` inside compose). Models download once:

```bash
docker compose --profile gpu up -d voice
VOICE_API_KEY=... bash voice/setup_models.sh        # ~3 GB (OmniVoice + Whisper turbo)
```

`VOICE_API_KEY` is any long random string; it is the container's own admin
key, set once in `.env`. VRAM: OmniVoice plus Whisper need about 4 GB, so on a
16 GB card they coexist with the Wan 2.2 5B video model; the renderer runs voice
first and video second.
