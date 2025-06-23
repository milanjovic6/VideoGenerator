import os, webbrowser, threading
import numpy as np
from datetime import datetime
from tkinter import Tk, Label, Entry, Button, Checkbutton, BooleanVar, filedialog
from PIL import Image, ImageDraw, ImageFont
import imageio
import moviepy.editor as mpy
from moviepy.audio.fx import audio_loop

# KONFIG
W, H = 1920, 1080
P = 2
fps = 30
intro = 2
static_t = 3
end_t = 5
fade_t = 5
pixels = 5
END_IMAGE = "end_graphic.png"

class App:
    def __init__(self, root):
        self.folder = ""
        self.music = ""
        self.logo = ""
        self.root = root
        root.title("Scroll Generator")
        Label(root, text="Folder slika:").pack()
        self.e = Entry(root, width=60); self.e.pack()
        Button(root, text="Izaberi", command=self.choose).pack()
        self.var_music = BooleanVar(); self.var_text = BooleanVar(); self.var_water = BooleanVar()
        Checkbutton(root, text="Muzika", var=self.var_music).pack()
        Checkbutton(root, text="Like/Share text", var=self.var_text).pack()
        Checkbutton(root, text="Watermark logo", var=self.var_water).pack()
        Button(root, text="MP3", command=self.choose_music).pack()
        Button(root, text="Logo PNG", command=self.choose_logo).pack()
        self.btn = Button(root, text="START", bg="green", fg="white", font=("Arial",14,"bold"), command=self.start)
        self.btn.pack(pady=10)
        self.status = Label(root, text="", fg="green"); self.status.pack()
        self.open_btn = Button(root, text="Otvori video", command=self.open_vid, state="disabled")
        self.open_btn.pack()
        self.outpath = ""

    def choose(self):
        f= filedialog.askdirectory()
        self.e.delete(0,'end'); self.e.insert(0,f)

    def choose_music(self):
        p = filedialog.askopenfilename(filetypes=[("MP3","*.mp3")]); self.music = p

    def choose_logo(self):
        p = filedialog.askopenfilename(filetypes=[("PNG","*.png")]); self.logo = p

    def start(self):
        self.status.config(text="Pokrenuto..."); self.btn.config(state="disabled")
        threading.Thread(target=self.make).start()

    def log(self, msg): print(msg); self.status.config(text=msg); self.root.update()

    def open_vid(self):
        if os.path.exists(self.outpath): webbrowser.open(self.outpath)

    def make(self):
        fldr=self.e.get()
        imgs = sorted([f for f in os.listdir(fldr) if f.lower().endswith((".jpg",".png",".jpeg"))])
        if len(imgs)<4: self.log("Molim min. 4 slike."); self.btn.config(state="normal"); return
        odir=os.path.join(fldr,"video"); os.makedirs(odir,exist_ok=True)
        fn=os.path.join(odir,f"panorama_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp4")
        imlist, ws = [], []
        for fnm in imgs:
            im=Image.open(os.path.join(fldr,fnm)).convert("RGB")
            sc=H/im.height; nw=int(im.width*sc); im=im.resize((nw,H))
            imlist.append(im); ws.append(nw)

        pad=lambda w: w+P
        wv=imageio.get_writer(fn,fps=fps)
        blk = np.zeros((H,W,3),dtype=np.uint8)
        for _ in range(int(intro*fps)): wv.append_data(blk)
        self.log("Ulazak 3 slike...")
        base = W//2 - sum(pad(ws[i]) for i in range(3))*0.5
        dirs=["bottom","top","bottom"]
        efr=int(static_t*fps)
        static=Image.new("RGB",(W,H),blk)
        for i in range(3):
            im, w = imlist[i], ws[i]
            x = base + sum(pad(ws[j]) for j in range(i))
            for f in range(efr):
                fr=static.copy()
                y = (H+10)*(1-f/efr) if dirs[i]=="bottom" else -(H+10)*(1-f/efr)
                fr.paste(im,(int(x),int(y)))
                d=ImageDraw.Draw(fr); d.rectangle([int(x)+w,0,int(x)+w+P,H],fill=(255,255,255))
                wv.append_data(np.array(fr))
            static.paste(im,(int(x),0))
            d=ImageDraw.Draw(static); d.rectangle([int(x)+w,0,int(x)+w+P,H],fill=(255,255,255))
        for _ in range(efr): wv.append_data(np.array(static))
        self.log("Scroll...")
        full=sum(pad(w) for w in ws)
        frames=int((full+W)/pixels)
        for i in range(frames+1):
            fr=Image.new("RGB",(W,H),blk)
            xs=W - i*pixels
            # paste all images scrolling
            x=xs
            for im,w in zip(imlist,ws):
                if x+w>0 and x< W:
                    fr.paste(im,(int(x),0))
                    d=ImageDraw.Draw(fr); d.rectangle([int(x)+w,0,int(x)+w+P,H],fill=(255,255,255))
                x+=pad(w)
            wv.append_data(np.array(fr))
        self.log("End...")
        font = ImageFont.truetype("arial.ttf",60) if os.path.exists("arial.ttf") else ImageFont.load_default()
        for _ in range(int(end_t*fps)):
            fr=Image.new("RGB",(W,H),blk)
            if self.var_text.get():
                d=ImageDraw.Draw(fr); t="Like, Share & Subscribe"
                tw,th=d.textsize(t,font=font)
                d.text(((W-tw)//2,(H-th)//2),t,fill=(255,255,255),font=font)
            if os.path.exists(END_IMAGE):
                gi=Image.open(END_IMAGE).convert("RGBA")
                w2,h2=gi.size; gi=gi.resize((w2*2,h2*2))
                fr.paste(gi,((W-(w2*2))//2,(H-(h2*2))//2),gi)
            wv.append_data(np.array(fr))
        wv.close()
        self.outpath=fn
        if self.var_music.get() and os.path.exists(self.music):
            self.log("Muzika...")
            vc=mpy.VideoFileClip(fn)
            ac=mpy.AudioFileClip(self.music)
            if ac.duration < vc.duration: ac = audio_loop(ac, duration=vc.duration)
            ac = ac.audio_fadeout(fade_t)
            fn2=fn.replace(".mp4","_audio.mp4")
            vc.set_audio(ac).write_videofile(fn2, codec="libx264", audio_codec="aac")
            self.outpath=fn2
        self.log("Gotovo")
        self.btn.config(state="normal"); self.open_btn.config(state="normal")

if __name__=="__main__":
    root=Tk(); App(root); root.mainloop()
