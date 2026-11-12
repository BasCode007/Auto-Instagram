import json
caps=json.load(open('captions.json'))
VO="https://assets.vidiq.com/voiceovers/ca76f78c-d497-41e8-890c-459d833fda35/d23c7b26-5048-4a6e-ab4a-adae308ed30c.mp3"
P="https://videos.pexels.com/video-files/"
clips=[ # (uri,w,h,dur,in,len,motion)
 (P+"19932267/19932267-hd_1080_1920_30fps.mp4",1080,1920,20.22,3.0,3.7,"zoom_in"),
 (P+"7942762/7942762-hd_1080_2048_25fps.mp4",1080,2048,11.49,1.0,4.2,"zoom_out"),
 (P+"12976044/12976044-hd_1080_1920_30fps.mp4",1080,1920,10.01,0.5,5.7,"zoom_in"),
 (P+"11267671/11267671-hd_1080_1920_30fps.mp4",720,1280,14.78,1.0,5.9,"pan_up"),
 (P+"5827649/5827649-hd_720_1280_24fps.mp4",720,1280,10.02,0.0,7.1,"zoom_in"),
 (P+"17980163/17980163-hd_720_1280_24fps.mp4",720,1280,46.79,10.0,5.1,"zoom_out"),
 (P+"19932267/19932267-hd_1080_1920_30fps.mp4",1080,1920,20.22,10.0,2.9,"zoom_in"),
]
import os
if os.path.exists('clips.json'):            # [{uri,width,height,duration}] from find_broll / ComfyUI
    clips=[(c['uri'],c['width'],c['height'],c['duration'],0.0,0.0,"zoom_in") for c in json.load(open('clips.json'))]
VO_SECONDS=float(os.environ.get("VO_SECONDS","34.12"))
CUT=float(os.environ.get("CUT","1.3"))      # a new shot every ~1.3 s (docs/STANDARD.md)
DUR=round((int((VO_SECONDS+0.5)*30)//3)*3/30,3)   # on the frame grid, multiple of 0.1
track=[]; t=0.0; i=0; used={}
motions=["zoom_in","zoom_out","pan_up","zoom_in","pan_down"]
while t<DUR-1e-6:
    u,w,h,d,_,_,_=clips[i%len(clips)]
    ln=min(CUT,round(DUR-t,3))
    tin=used.get(u,0.5)
    if tin+ln>d-0.2: tin=0.5
    used[u]=tin+ln+0.8                        # skip ahead so a reused clip shows new frames
    track.append({"id":f"c{len(track)+1}","duration":ln,
      "content":{"kind":"media","asset":{"type":"video","uri":u,"width":w,"height":h,"duration":d},
                 "fit":"cover","muted":True,"trim":{"in":round(tin,3),"out":round(tin+ln,3)}},
      "looks":[{"look":"ai_realism","params":{"strength":0.7,"temperature":0.12,"grain":0.1,"skin":0.6}},
               {"look":"ken_burns","params":{"motion":motions[len(track)%len(motions)],"scale":1.1}}]})
    t=round(t+ln,3); i+=1
trans=[]                                    # hard cuts, as the references do
scene={
 "version":"1.0",
 "assets":{
   "mont_xb":{"type":"font","uri":"https://pastatic.picsart.com/32344542781040042364.ttf","name":"Montserrat ExtraBold"},
   "mont_md":{"type":"font","uri":"https://pastatic.picsart.com/10609558443589390885.ttf","name":"Montserrat Medium"}
 },
 "composition":{"width":1080,"height":1920,"fps":30,"duration":DUR,"background":"#000000"},
 "layers":[
  {"id":"footage","start":0,"duration":DUR,"content":{"kind":"track","clips":track,"transitions":trans}},
  {"id":"dim","start":0,"duration":DUR,"transform":{"position":[540,960],"opacity":0.22},
   "content":{"kind":"color","color":"#000000","size":[1080,1920]}},
  {"id":"captions","start":0,"duration":DUR,"content":{"kind":"captions","transcript":caps,
    "style":{"font":{"family":"mont_xb","size":112},"color":"#FFFFFF","alignment":"center","wrapWidth":960,
             "offset":[0,-40],"reveal":{"window":"sustain","fade":0.06},
             "effects":[{"id":"drop_shadow","params":{"offset":[0,8],"blur":28,"color":"#000000cc"}}],
             "decorations":[{"target":"emphasized","place":"text","color":"#F7C948"},
                            {"target":"highlighted","place":"text","color":"#F7C948","fade":0.05}]}}},
  {"id":"music","start":0,"duration":DUR,
   "content":{"kind":"audio","asset":{"type":"audio","uri":os.environ.get("MUSIC_URL","https://ai-music-tracks.s3.us-east-1.amazonaws.com/ca76f78c-d497-41e8-890c-459d833fda35/c90f60e0-bc9d-4cdc-a1f4-423e8621a31f.wav"),"duration":float(os.environ.get("MUSIC_SECONDS","63.9"))},"volume":100},
   "animations":{"volume":{"keyframes":[{"time":0,"value":0},{"time":1.0,"value":25},{"time":DUR-2.5,"value":25},{"time":DUR,"value":0}]}}},
  {"id":"vo","start":0,"duration":DUR,"content":{"kind":"audio","asset":{"type":"audio","uri":VO,"duration":VO_SECONDS},"volume":100}}
 ]}
json.dump(scene,open('scene.json','w'),separators=(',',':'))
print(len(json.dumps(scene)),"bytes")
