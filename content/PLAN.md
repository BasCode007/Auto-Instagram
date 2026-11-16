# Content plan — first five reels

Format for all five: narrated montage per `docs/STANDARD.md`. 60–70 spoken
words (about 25–30 s), a counter-intuitive first line, one idea per sentence,
no call to action. Each opens with two AI signature shots (ComfyUI) and cuts to
cinematic stock every 1.3 s; 1–2 word centred captions; deep calm narrator;
score 12 dB under the voice. Posting slots 07:30 and 18:30 Australia/Sydney,
each post approved in Telegram for the first two weeks.

| # | Hook | Pillar | Signature shots |
|---|---|---|---|
| 1 | Your salary is the most expensive thing you own. | wealth mindset | empty corner office at dawn; banknotes into a briefcase |
| 2 | Rich people are boring with money. That's the whole trick. | money habits | watch movement macro; yacht deck at golden hour |
| 3 | Nobody is coming to make you rich. Good. | success psychology | lone figure on a rooftop at sunrise; supercar showroom dolly |
| 4 | You don't need more motivation. You need fewer decisions. | daily motivation | bedroom at dawn; chess piece on marble |
| 5 | Stop asking what it costs. Ask what it pays. | wealth mindset | banknotes on marble; villa with infinity pool at dusk |

The full scripts, captions, hashtags, shot prompts and stock keywords are in
`content/queue.json`. The workflow posts queued items first, in order, then
goes back to writing its own scripts in the same voice. Add to the queue by
appending an item with a new `id`; items already posted are remembered in the
renderer's state volume.
