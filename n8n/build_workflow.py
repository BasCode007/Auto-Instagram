#!/usr/bin/env python3
"""Generate the n8n workflow JSON files. Run: python3 n8n/build_workflow.py

The workflows are generated rather than hand-edited so every node parameter
stays reviewable in one place. Everything configurable is read from the
environment (.env), so importing needs no editing in the n8n UI.

Targets n8n 2.x. It needs N8N_BLOCK_ENV_ACCESS_IN_NODE=false (set in
docker-compose.yml) because expressions read $env.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN_ID = "AutoIgMain000001"
ERR_ID = "AutoIgErrors0001"


class Flow:
    def __init__(self):
        self.nodes, self.connections = [], {}

    def node(self, name, ntype, version, pos, params=None, **extra):
        n = {"parameters": params or {}, "id": "".join(c for c in name.lower() if c.isalnum()),
             "name": name, "type": f"n8n-nodes-base.{ntype}", "typeVersion": version, "position": pos}
        n.update(extra)
        self.nodes.append(n)
        return name

    def link(self, src, dst, out=0):
        main = self.connections.setdefault(src, {}).setdefault("main", [])
        while len(main) <= out:
            main.append([])
        main[out].append({"node": dst, "type": "main", "index": 0})


RETRY = {"retryOnFail": True, "maxTries": 3, "waitBetweenTries": 5000}
CFG = "$('Config').first().json"


def if_params(left, op_type, operation, right=None):
    cond = {"id": "c1", "leftValue": left, "operator": {"type": op_type, "operation": operation}}
    if right is None:
        cond["operator"]["singleValue"] = True
    else:
        cond["rightValue"] = right
    return {"conditions": {"options": {"caseSensitive": True, "typeValidation": "loose", "version": 2},
                           "combinator": "and", "conditions": [cond]}, "options": {}}


def telegram_params(text_expr, extra_body=""):
    return {
        "method": "POST",
        "url": "={{ " + CFG + ".telegramBase }}/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ chat_id: $env.TELEGRAM_CHAT_ID, text: " + text_expr
                    + ", disable_web_page_preview: false" + extra_body + " }) }}",
        "options": {"timeout": 20000},
    }


PICK_CODE = r"""// Choose format, pillar and angle, and build the prompt. Remembers what was
// already posted (workflow static data) so the model is told not to repeat it.
const sd = $getWorkflowStaticData('global');
sd.counter = (sd.counter || 0) + 1;
sd.history = sd.history || [];
const n = sd.counter;

const pillars = ["wealth_mindset","money_habits","investing_basics","entrepreneurship","success_psychology","daily_motivation"];
const angles = [
  "a counter-intuitive truth most people get backwards",
  "one small concrete action someone can take today",
  "a common mistake and the calmer alternative",
  "a short story about an ordinary person (no real names)",
  "a simple number or rule of thumb, explained plainly",
  "a reframe of a limiting belief about money",
  "a question that makes the viewer reflect on their own habits",
];
const pillar = pillars[n % pillars.length];
const angle = angles[n % angles.length];              // 7 angles x 6 pillars: 42 posts before a pair repeats
const content_type = "montage";   // quote cards are kept in the renderer for manual use only (docs/STANDARD.md)
const avoid = sd.history.slice(-30).map(h => "- " + h.hook).join("\n") || "(nothing yet)";

const common = `You write for an Instagram account about finance, wealth and success with a positive, grounded voice: building wealth and keeping a calm, disciplined, grateful mindset go together. Never hype, never get-rich-quick. Speak to one person ("you"). Education and motivation only, NOT financial advice: no guaranteed returns, no "risk-free", no individual buy/sell calls, no income claims.
Pillar: ${pillar}. Angle for this post: ${angle}.
Do NOT repeat or closely paraphrase any of these earlier posts:
${avoid}
Return STRICT JSON only.`;

const narrated = `${common}
Write a faceless narrated Reel in fast montage style (see the account standard): 45-80 words, 20-35 seconds spoken. Open with a counter-intuitive command or claim that works as the first spoken line (no greeting, no "today", no "in this video"). Short declarative sentences; each sentence is one shot. End on the strongest line. NO call to action, no "follow", no "save this", no question at the end.
Keys: "hook" (the first spoken line, <= 60 characters), "script" (the full voiceover INCLUDING the hook, 45-80 words), "caption" (<= 400 characters, no hashtags, one extra insight), "hashtags" (3 to 5 lowercase tags without #), "broll_keywords" (6 concrete cinematic stock-footage search terms: luxury, city at night, skyline sunrise, supercar, private jet, yacht, penthouse, watch close-up, lone figure golden hour; never "office", "handshake" or "stock chart"), "hero_prompts" (2 text-to-video prompts for the signature shots, each one sentence: subject, camera move, light, mood, "cinematic, photoreal, 9:16"; no people's faces, no text).`;

const quote = `${common}
Write an original quote card. Keys: "quote" (<= 110 characters, one or two sentences, no quotation marks, no attribution), "hook" (same as quote), "caption" (2-4 encouraging sentences then a gentle call to action, <= 600 characters, no hashtags), "hashtags" (3 to 5 lowercase tags without #).`;

return [{ json: { content_type, pillar, angle, system_prompt: content_type === "montage" ? narrated : quote } }];
"""

PARSE_CODE = r"""// Parse and validate the model's JSON, then build the final caption.
// Mirrors auto_instagram/caption.py: 2,200 characters, at most 5 hashtags
// (Instagram's limit since December 2025), de-duplicated case-insensitively.
const raw = $json.choices?.[0]?.message?.content ?? $json.message?.content ?? $json.content;
let d;
try { d = typeof raw === "string" ? JSON.parse(raw) : raw; }
catch (e) { throw new Error("Model did not return JSON: " + String(raw).slice(0, 300)); }
if (!d || typeof d !== "object") throw new Error("Model returned nothing usable");

const pick = $('Pick format and topic').first().json;
const type = pick.content_type;
const MAX_LEN = 2200, MAX_TAGS = 5;

const need = type === "montage" ? ["script", "caption", "broll_keywords"] : ["quote", "caption"];
for (const k of need) if (!d[k] || (Array.isArray(d[k]) && !d[k].length)) throw new Error(`Model output is missing "${k}"`);

// Compliance backstop: the prompt forbids these, this refuses to publish them.
const banned = /\b(guaranteed?\s+(returns?|profits?|income)|risk[- ]free|can'?t lose|get rich quick|double your money|financial advice:)/i;
const allText = [d.script, d.quote, d.caption, d.on_screen_hook].filter(Boolean).join(" ");
const hit = allText.match(banned);
if (hit) throw new Error(`Blocked by compliance check: "${hit[0]}"`);

const words = (d.script || "").trim().split(/\s+/).filter(Boolean).length;
if (type === "montage" && (words < 30 || words > 120)) throw new Error(`Script is ${words} words; expected 45-80`);
if (type === "quote" && d.quote.length > 180) throw new Error(`Quote is ${d.quote.length} characters; too long for the card`);

const normTag = (t) => { const c = String(t || "").trim().replace(/^#+/, "").replace(/[^\p{L}\p{N}_]/gu, ""); return c ? "#" + c : null; };
const tags = []; const seen = new Set();
for (const t of (d.hashtags || [])) { const x = normTag(t); if (!x || seen.has(x.toLowerCase())) continue; seen.add(x.toLowerCase()); tags.push(x); if (tags.length >= MAX_TAGS) break; }

let body = String(d.caption).trim().replace(/#[\p{L}\p{N}_]+/gu, "").replace(/[ \t]+\n/g, "\n").trim();
if (pick.pillar === "investing_basics") body += "\n\nEducational only, not financial advice.";
let caption = [body, tags.join(" ")].filter(Boolean).join("\n\n");
if (caption.length > MAX_LEN) caption = caption.slice(0, MAX_LEN - 1) + "…";

let onScreen = String(d.on_screen_hook || "").trim();
if (onScreen.length > 44) onScreen = onScreen.slice(0, 43).trimEnd() + "…";

return [{ json: {
  content_type: type, pillar: pick.pillar, caption,
  hook: String(d.hook || d.quote || d.on_screen_hook || "").trim(),
  render_request: type === "montage"
    ? { type, script: String(d.script).trim(), keywords: d.broll_keywords, hero_prompts: d.hero_prompts || [], pillar: pick.pillar }
    : { type, quote: String(d.quote).trim(), pillar: pick.pillar },
} }];
"""

POST_CODE = r"""// Combine the rendered video with the caption for the publish steps.
const p = $('Parse and build caption').first().json;
if (!$json.video_url) throw new Error("Renderer returned no video_url: " + JSON.stringify($json).slice(0, 300));
return [{ json: { video_url: $json.video_url, duration: $json.duration, caption: p.caption,
                  content_type: p.content_type, pillar: p.pillar, hook: p.hook } }];
"""

RECORD_CODE = r"""// Remember what was posted so future prompts avoid repeating it.
const sd = $getWorkflowStaticData('global');
const post = $('Prepare post').first().json;
sd.history = (sd.history || []).concat([{ hook: post.hook, pillar: post.pillar, type: post.content_type,
  permalink: $json.permalink || "", at: new Date().toISOString() }]).slice(-120);
return [{ json: { permalink: $json.permalink || "", media_id: $('Publish Reel').first().json.id, hook: post.hook } }];
"""


def build_main():
    f = Flow()
    f.node("Schedule", "scheduleTrigger", 1.2, [-1320, 200],
           {"rule": {"interval": [{"field": "cronExpression", "expression": "30 7,18 * * *"}]}})
    f.node("Run once now", "manualTrigger", 1, [-1320, 400])
    f.node("Config", "set", 3.4, [-1100, 300], {"assignments": {"assignments": [
        {"id": "a1", "name": "graphBase", "type": "string",
         "value": "={{ ($env.IG_GRAPH_BASE_URL || ('https://' + ($env.IG_GRAPH_HOST || 'graph.instagram.com'))) + '/' + ($env.GRAPH_VERSION || 'v27.0') }}"},
        {"id": "a2", "name": "igUserId", "type": "string", "value": "={{ $env.IG_USER_ID || 'me' }}"},
        {"id": "a3", "name": "handle", "type": "string", "value": "={{ $env.IG_HANDLE || '' }}"},
        {"id": "a4", "name": "autoPublish", "type": "boolean",
         "value": "={{ String($env.AUTO_PUBLISH || 'false').toLowerCase() === 'true' }}"},
        {"id": "a5", "name": "llmBase", "type": "string", "value": "={{ $env.LLM_BASE_URL || 'https://api.openai.com/v1' }}"},
        {"id": "a6", "name": "llmModel", "type": "string", "value": "={{ $env.LLM_MODEL || 'gpt-4o-mini' }}"},
        {"id": "a7", "name": "rendererUrl", "type": "string", "value": "={{ $env.RENDERER_URL || 'http://renderer:8080' }}"},
        {"id": "a8", "name": "telegramBase", "type": "string", "value": "={{ $env.TELEGRAM_BASE_URL || 'https://api.telegram.org' }}"},
    ]}, "options": {}})
    f.node("Pick format and topic", "code", 2, [-880, 300], {"jsCode": PICK_CODE})
    f.node("Write script (LLM)", "httpRequest", 4.2, [-660, 300], {
        "method": "POST", "url": "={{ " + CFG + ".llmBase }}/chat/completions",
        "sendHeaders": True, "headerParameters": {"parameters": [
            {"name": "Authorization", "value": "=Bearer {{ $env.LLM_API_KEY || $env.OPENAI_API_KEY }}"}]},
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ model: " + CFG + ".llmModel, temperature: 0.9, response_format: { type: 'json_object' }, "
                    "messages: [ { role: 'system', content: $json.system_prompt }, "
                    "{ role: 'user', content: 'Write the post now. JSON only.' } ] }) }}",
        "options": {"timeout": 90000}}, **RETRY)
    f.node("Parse and build caption", "code", 2, [-440, 300], {"jsCode": PARSE_CODE})
    f.node("Render video", "httpRequest", 4.2, [-220, 300], {
        "method": "POST", "url": "={{ " + CFG + ".rendererUrl }}/render",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify(Object.assign({ handle: " + CFG + ".handle }, $json.render_request)) }}",
        "options": {"timeout": 900000}}, retryOnFail=True, maxTries=2, waitBetweenTries=5000)
    f.node("Prepare post", "code", 2, [0, 300], {"jsCode": POST_CODE})
    f.node("Autopilot?", "if", 2.2, [220, 300], if_params("={{ " + CFG + ".autoPublish }}", "boolean", "true"))

    # --- review branch: Telegram message with approve/skip links, wait for the tap
    f.node("Ask for approval", "httpRequest", 4.2, [440, 480], telegram_params(
        "'Review this ' + $json.content_type + ' post (' + $json.pillar + '):\\n\\n' + $json.caption + '\\n\\nVideo: ' + $json.video_url",
        ", reply_markup: { inline_keyboard: [[ { text: 'Approve', url: $execution.resumeUrl + '?decision=approve' }, "
        "{ text: 'Skip', url: $execution.resumeUrl + '?decision=skip' } ]] }"), **RETRY)
    f.node("Wait for decision", "wait", 1.1, [660, 480], {
        "resume": "webhook", "httpMethod": "GET", "responseMode": "onReceived",
        "limitWaitTime": True, "limitType": "afterTimeInterval", "resumeAmount": 12, "resumeUnit": "hours",
        "options": {"responseData": "Recorded. You can close this tab."}}, webhookId="autoig-approval")
    f.node("Approved?", "if", 2.2, [880, 480], if_params("={{ $json.query?.decision }}", "string", "equals", "approve"))
    f.node("Notify skipped", "httpRequest", 4.2, [1100, 620], telegram_params(
        "'Skipped (no approval): ' + $('Prepare post').first().json.hook"), onError="continueRegularOutput")

    # --- publish: container -> bounded poll -> publish
    auth = {"sendHeaders": True, "headerParameters": {"parameters": [
        {"name": "Authorization", "value": "=Bearer {{ $env.IG_ACCESS_TOKEN }}"}]}}
    post = "$('Prepare post').first().json"
    f.node("Create media container", "httpRequest", 4.2, [1100, 300], {
        "method": "POST", "url": "={{ " + CFG + ".graphBase }}/{{ " + CFG + ".igUserId }}/media", **auth,
        "sendBody": True, "contentType": "form-urlencoded", "bodyParameters": {"parameters": [
            {"name": "media_type", "value": "REELS"},
            {"name": "video_url", "value": "={{ " + post + ".video_url }}"},
            {"name": "caption", "value": "={{ " + post + ".caption }}"},
            {"name": "thumb_offset", "value": "1500"},
            {"name": "share_to_feed", "value": "true"}]},
        "options": {"timeout": 60000}}, **RETRY)
    f.node("Wait for processing", "wait", 1.1, [1320, 300], {"amount": 20, "unit": "seconds"}, webhookId="autoig-poll")
    f.node("Check container status", "httpRequest", 4.2, [1540, 300], {
        "method": "GET", "url": "={{ " + CFG + ".graphBase }}/{{ $('Create media container').first().json.id }}", **auth,
        "sendQuery": True, "queryParameters": {"parameters": [{"name": "fields", "value": "status_code,status"}]},
        "options": {"timeout": 30000}}, **RETRY)
    f.node("Finished?", "if", 2.2, [1760, 300], if_params("={{ $json.status_code }}", "string", "equals", "FINISHED"))
    f.node("Failed or timed out?", "if", 2.2, [1980, 440], if_params(
        "={{ ['ERROR','EXPIRED'].includes($json.status_code) || $runIndex >= 20 }}", "boolean", "true"))
    f.node("Stop: Instagram rejected video", "stopAndError", 1, [2200, 560], {
        "errorMessage": "=Instagram did not accept the video (status: {{ $json.status_code }} {{ $json.status }}). Nothing was published."})
    f.node("Publish Reel", "httpRequest", 4.2, [1980, 200], {
        "method": "POST", "url": "={{ " + CFG + ".graphBase }}/{{ " + CFG + ".igUserId }}/media_publish", **auth,
        "sendBody": True, "contentType": "form-urlencoded", "bodyParameters": {"parameters": [
            {"name": "creation_id", "value": "={{ $('Create media container').first().json.id }}"}]},
        "options": {"timeout": 60000}})   # no retry: a retried publish could double-post
    f.node("Get permalink", "httpRequest", 4.2, [2200, 200], {
        "method": "GET", "url": "={{ " + CFG + ".graphBase }}/{{ $json.id }}", **auth,
        "sendQuery": True, "queryParameters": {"parameters": [{"name": "fields", "value": "permalink"}]},
        "options": {"timeout": 30000}}, onError="continueRegularOutput")
    f.node("Record post", "code", 2, [2420, 200], {"jsCode": RECORD_CODE})
    f.node("Notify posted", "httpRequest", 4.2, [2640, 200], telegram_params(
        "'Posted: ' + $json.hook + '\\n' + $json.permalink"), onError="continueRegularOutput")

    f.link("Schedule", "Config"); f.link("Run once now", "Config")
    for a, b in [("Config", "Pick format and topic"), ("Pick format and topic", "Write script (LLM)"),
                 ("Write script (LLM)", "Parse and build caption"), ("Parse and build caption", "Render video"),
                 ("Render video", "Prepare post"), ("Prepare post", "Autopilot?"),
                 ("Ask for approval", "Wait for decision"), ("Wait for decision", "Approved?"),
                 ("Create media container", "Wait for processing"), ("Wait for processing", "Check container status"),
                 ("Check container status", "Finished?"), ("Publish Reel", "Get permalink"),
                 ("Get permalink", "Record post"), ("Record post", "Notify posted")]:
        f.link(a, b)
    f.link("Autopilot?", "Create media container", 0); f.link("Autopilot?", "Ask for approval", 1)
    f.link("Approved?", "Create media container", 0); f.link("Approved?", "Notify skipped", 1)
    f.link("Finished?", "Publish Reel", 0); f.link("Finished?", "Failed or timed out?", 1)
    f.link("Failed or timed out?", "Stop: Instagram rejected video", 0)
    f.link("Failed or timed out?", "Wait for processing", 1)
    return {"id": MAIN_ID, "name": "Auto-Instagram — create and publish", "nodes": f.nodes,
            "connections": f.connections, "active": False, "pinData": {},
            "settings": {"executionOrder": "v1", "errorWorkflow": ERR_ID}, "tags": []}


def build_errors():
    f = Flow()
    f.node("On any failure", "errorTrigger", 1, [0, 0])
    f.node("Alert owner", "httpRequest", 4.2, [240, 0], {
        "method": "POST",
        "url": "={{ $env.TELEGRAM_BASE_URL || 'https://api.telegram.org' }}/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ chat_id: $env.TELEGRAM_CHAT_ID, text: 'Auto-Instagram FAILED at \"' + "
                    "($json.execution?.lastNodeExecuted || 'unknown step') + '\": ' + "
                    "String($json.execution?.error?.message || 'no message').slice(0, 600) + "
                    "'\\nNothing was posted for this slot.' }) }}",
        "options": {"timeout": 20000}}, **RETRY)
    f.link("On any failure", "Alert owner")
    return {"id": ERR_ID, "name": "Auto-Instagram — failure alerts", "nodes": f.nodes,
            "connections": f.connections, "active": False, "pinData": {},
            "settings": {"executionOrder": "v1"}, "tags": []}


if __name__ == "__main__":
    for name, wf in (("auto-instagram-workflow.json", build_main()), ("auto-instagram-errors.json", build_errors())):
        (HERE / name).write_text(json.dumps(wf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote n8n/{name}: {len(wf['nodes'])} nodes")
