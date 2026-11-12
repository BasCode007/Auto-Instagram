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
track=[]
for i,(u,w,h,d,tin,ln,mo) in enumerate(clips):
    track.append({"id":f"c{i+1}","duration":ln,
      "content":{"kind":"media","asset":{"type":"video","uri":u,"width":w,"height":h,"duration":d},
                 "fit":"cover","muted":True,"trim":{"in":tin,"out":round(tin+ln,3)}},
      "looks":[{"look":"ken_burns","params":{"motion":mo,"scale":1.12}},
               {"look":"ai_realism","params":{"strength":0.7,"temperature":0.12,"grain":0.1,"skin":0.6}}]})
trans=[{"between":i,"id":"blur_dissolve","duration":0.4} for i in range(len(clips)-1)]
DUR=34.6
scene={
 "version":"1.0",
 "assets":{
   "mont_xb":{"type":"font","uri":"https://pastatic.picsart.com/32344542781040042364.ttf","name":"Montserrat ExtraBold"},
   "mont_md":{"type":"font","uri":"https://pastatic.picsart.com/10609558443589390885.ttf","name":"Montserrat Medium"}
 },
 "composition":{"width":1080,"height":1920,"fps":30,"duration":DUR,"background":"#000000"},
 "layers":[
  {"id":"footage","start":0,"duration":DUR,"content":{"kind":"track","clips":track,"transitions":trans}},
  {"id":"dim","start":0,"duration":DUR,"transform":{"position":[540,960],"opacity":0.18},
   "content":{"kind":"color","color":"#000000","size":[1080,1920]}},
  {"id":"captions","start":0,"duration":DUR,"content":{"kind":"captions","transcript":caps,
    "style":{"font":{"family":"mont_xb","size":80},"color":"#FFFFFF","alignment":"center","wrapWidth":900,
             "offset":[0,230],"reveal":{"window":"sustain","fade":0.06},
             "effects":[{"id":"stroke","params":{"width":8,"color":"#000000ff"}},
                        {"id":"drop_shadow","params":{"offset":[0,6],"blur":16,"color":"#000000a0"}}],
             "decorations":[{"target":"emphasized","place":"text","color":"#F7C948"},
                            {"target":"highlighted","place":"text","color":"#F7C948","fade":0.05}]}}},
  {"id":"brand","start":0.3,"duration":DUR-0.3,"transform":{"position":[540,250]},
   "content":{"kind":"text","text":"ONE WEALTH HABIT A DAY","font":{"family":"mont_md","size":30},"color":"#FFFFFFCC","alignment":"center"},
   "effects":[{"id":"drop_shadow","params":{"offset":[0,2],"blur":8,"color":"#00000099"}}],
   "looks":[{"look":"fade","params":{"role":"in","length":0.6}}]},
  {"id":"vo","start":0,"duration":34.2,"content":{"kind":"audio","asset":{"type":"audio","uri":VO,"duration":34.12},"volume":1}}
 ]}
json.dump(scene,open('scene.json','w'),separators=(',',':'))
print(len(json.dumps(scene)),"bytes")
