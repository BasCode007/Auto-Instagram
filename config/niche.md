# Niche & brand guide

The single source of truth for *what* this account posts and *how* it sounds.
The LLM prompts in `prompts/` reference these rules, and `auto_instagram/content.py`
mirrors the pillar list in code.

## Topic

Finance, wealth, and success — with a **positive, empowering** framing. The
throughline is that building wealth and keeping a healthy, grateful mindset go
together: profit as a by-product of discipline, value creation, and a calm,
optimistic headspace.

## Content pillars

Rotate across these so the feed stays varied. Keys match
`config/hashtags.json` and `auto_instagram/content.py`.

| Pillar | Focus |
| --- | --- |
| `wealth_mindset` | Beliefs and habits behind wealth: discipline, patience, abundance. |
| `money_habits` | Practical behaviours: saving, budgeting, cash flow, paying yourself first. |
| `investing_basics` | Compounding, long-term thinking, diversification (educational, **never advice**). |
| `entrepreneurship` | Side hustles, value creation, business mindset. |
| `success_psychology` | Positive headspace, gratitude, resilience, self-discipline. |
| `daily_motivation` | Short quotes and affirmations tied to money and growth. |

## Voice

- Encouraging, grounded, and specific — not hype, not "get rich quick".
- Short sentences. Speak to one person ("you").
- Lead with a hook in the first 2 seconds. End with a clear, gentle CTA.

## Hook formulas

- "The habit that quietly builds wealth: …"
- "If you're under 30, do this with your first $1,000."
- "Broke isn't a number. It's a mindset. Here's the shift…"
- "Nobody talks about the *calm* side of getting rich."

## CTA examples

- "Save this so future-you actually does it."
- "Follow for one wealth habit a day."
- "Which one are you starting today? 👇"

## Compliance — read this

This account shares **education and motivation, not financial advice.** To keep
it safe and platform-compliant:

- **No guarantees or specific return promises** ("get X% returns", "double your
  money"). Ban words like *guaranteed*, *risk-free*, *can't lose*.
- **No individualised advice** ("buy this stock/coin now"). Keep it general and
  educational.
- **Include a light disclaimer** on investing-pillar posts, e.g.
  *"Educational only, not financial advice."* (`content.DISCLAIMER`).
- Avoid unverifiable income claims and screenshots of "earnings".
- Respect Instagram's terms — this system publishes only through the **official
  Instagram Graph API** on an account you own.
