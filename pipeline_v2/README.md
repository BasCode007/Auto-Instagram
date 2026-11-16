# Pipeline v2 — prototype and scene builder

**Production now runs in the Docker stack:** `scripts/render_montage.sh` behind
the renderer service renders at the standard in `docs/STANDARD.md` with ffmpeg
alone, so n8n needs no chat connectors. This folder holds the prototype that set
that standard (vidIQ voice + Picsart compositor, first two test reels) and the
ComfyUI client the renderer uses for AI shots.


The first renderer (ffmpeg + ImageMagick in `scripts/`) was judged too poor to
post. This folder is the replacement production path, built from the connectors
now attached to the account. It produced the first test reel on 2026-11-12.

## How the prototype reel was made

| Step | Tool | Cost |
|---|---|---|
| Script (hook + 80–95 words + CTA) | LLM, rules in `config/niche.md` | ~cents |
| Voiceover | vidIQ `voiceover_generate` (ElevenLabs voices) | 28 credits / 1000 chars |
| Word timings | Picsart `transcribe` (word-level, caption-ready) | free |
| Footage | vidIQ `find_broll` (Pexels, portrait) — prefer the `hd_1080_*` renditions | 1 credit / search |
| Music | vidIQ `generate_music` (original instrumental) — reuse across reels | 25 credits / track |
| Composite | Picsart scene: track of clips with `blur_dissolve`, `ai_realism` grade + `ken_burns` motion, word-revealed captions with gold highlight, brand tag, voice + ducked music | free (GPU render) |
| Publish | vidIQ `instagram_publish_reel` once the Instagram OAuth is connected | free |

`chunk.py` turns the transcript into 2–4 word caption beats (`captions.json`);
`build_scene.py` assembles the Picsart scene (`scene.example.json` is the
validated scene of the test reel). Caption style: Montserrat ExtraBold 80 px,
white with 8 px stroke + shadow, offset 230 px below centre (inside the Reels
safe zone), spoken words revealed with a gold (`#F7C948`) highlight.

## Credits per reel at this standard

~28 (voice) + ~5 (b-roll) ≈ 33 vidIQ credits, plus a music track every few
reels. Two reels a day ≈ 2,000 credits / month → needs a paid vidIQ tier.
Higgsfield's free plan cannot generate (“Requires basic plan or higher”); AI
hero shots are an upgrade once a budget is set.
