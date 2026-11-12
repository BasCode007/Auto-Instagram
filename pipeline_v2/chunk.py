import json,sys
t=json.load(open('transcript.json'))
EMPH={"time","wealthy","assets","hours","invest","compounding","follow","flip","scarcest","buy","one"}
out=[]
for seg in t['segments']:
    ws=seg['words']; i=0
    while i<len(ws):
        n=3
        # take up to 3 words but stop after punctuation
        chunk=[]
        while i<len(ws) and len(chunk)<n:
            chunk.append(ws[i]); i+=1
            if chunk[-1]['text'][-1] in ',.?!': break
        # avoid orphan single word at end: merge if remaining is 1 word
        if i==len(ws)-1 and len(chunk)<4:
            chunk.append(ws[i]); i+=1
        out.append(chunk)
segs=[]
for k,ch in enumerate(out):
    start=ch[0]['start']
    nxt=out[k+1][0]['start'] if k+1<len(out) else None
    last=ch[-1]['end']
    end = min(last+0.6, nxt-0.02) if nxt else last+0.6
    if end<=start: end=start+0.3
    text=" ".join(w['text'].strip().upper() for w in ch)
    emph=[j for j,w in enumerate(ch) if w['text'].strip().lower().strip(',.?!') in EMPH]
    s={"start":round(start,3),"end":round(end,3),"text":text,
       "words":[{"text":w['text'].strip().upper(),"start":w['start'],"end":w['end']} for w in ch]}
    if emph: s["emphasize"]=emph
    segs.append(s)
json.dump({"segments":segs},open('captions.json','w'),indent=1)
print(len(segs),"segments")
for s in segs: print(f"{s['start']:6.2f}-{s['end']:6.2f} {s['text']}")
