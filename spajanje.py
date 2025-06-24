
import os
import numpy as np
from PIL import Image, ImageDraw
import imageio
import tkinter as tk
from tkinter import filedialog, ttk
import threading
import datetime
import webbrowser
import time

# === PODEŠAVANJA ===
video_width = 1920
video_height = 1088
padding = 2                # razmak između slika (u px)
pad_color = (255, 255, 255)  # boja razmaka
bg_color = (0, 0, 0)       # pozadina (crno)
fps = 30
pixels_per_frame = 3       # brzina horiz. skrola (u px po frame-u)
intro_duration = 0         # crni ekran na početku (s)
end_duration = 10          # crni ekran na kraju (s)
entry_duration = int(fps * 3.5)  # trajanje animacije ulaska u frame-ovima (3.5 s)
output_folder_name = "video"


class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Generator")

        # ---------- Unos foldera ----------
        frm_folder = tk.Frame(root)
        frm_folder.pack(pady=5)
        tk.Label(frm_folder, text="Folder sa slikama:").pack(side=tk.LEFT)
        self.entry_folder = tk.Entry(frm_folder, width=50)
        self.entry_folder.pack(side=tk.LEFT, padx=5)
        tk.Button(frm_folder, text="Izaberi…", command=self.choose_folder).pack(side=tk.LEFT)

        # ---------- Prazan razmak (≈ 3 reda) ----------
        tk.Frame(root, height=20).pack()  # oko 3 tekstualna reda visine

        # ---------- START dugme ----------
        frm_start = tk.Frame(root)
        frm_start.pack(pady=5)
        self.btn_start = tk.Button(
            frm_start,
            text="START",
            bg="green",
            fg="white",
            font=("Arial", 14, "bold"),
            width=12,
            command=self.start,
        )
        self.btn_start.pack()

        # ---------- Progress ----------
        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=6)
        self.lbl_progress = tk.Label(root, text="0% – preostalo: 00:00")
        self.lbl_progress.pack()

        # ---------- Dugmad za otvaranje ----------
        frm_open = tk.Frame(root)
        frm_open.pack(pady=6)
        self.btn_open = tk.Button(frm_open, text="Otvori video", command=self.open_video, state=tk.DISABLED)
        self.btn_open.pack(side=tk.LEFT, padx=4)
        self.btn_open_folder = tk.Button(frm_open, text="📂", command=self.open_folder, state=tk.DISABLED)
        self.btn_open_folder.pack(side=tk.LEFT, padx=2)

        # ---------- Status ----------
        self.status = tk.Label(root, text="", fg="blue", font=("Arial", 12, "bold"))
        self.status.pack(pady=4)

        self.generated_video_path = None
        self.total_frames = 1  # placeholder
        self.frames_done = 0

    # -------------- GUI pomoćne funkcije --------------
    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry_folder.delete(0, tk.END)
            self.entry_folder.insert(0, folder)

    def start(self):
        self.status.config(text="⏳ Generisanje u toku…")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_open.config(state=tk.DISABLED)
        self.btn_open_folder.config(state=tk.DISABLED)
        threading.Thread(target=self.generate_video, daemon=True).start()

    def open_video(self):
        if self.generated_video_path:
            webbrowser.open(self.generated_video_path)

    def open_folder(self):
        if self.generated_video_path:
            folder = os.path.dirname(self.generated_video_path)
            webbrowser.open(f"file://{folder}")

    def log(self, msg):
        print(msg)
        self.status.config(text=msg)
        self.root.update()

    def update_progress(self, inc=1):
        self.frames_done += inc
        self.progress['value'] = self.frames_done
        percent = int(self.frames_done / self.total_frames * 100)
        remaining_frames = self.total_frames - self.frames_done
        remaining_sec = remaining_frames / fps
        mm, ss = divmod(int(remaining_sec + 0.5), 60)
        self.lbl_progress.config(text=f"{percent}% – preostalo: {mm:02d}:{ss:02d}")
        if self.frames_done % fps == 0 or self.frames_done == self.total_frames:
            self.root.update()

    # -------------- Glavna logika --------------
    def generate_video(self):
        import moviepy.editor as mpy

        t_start = time.time()
        folder = self.entry_folder.get()
        if not folder:
            self.log("⚠️ Niste izabrali folder.")
            self.btn_start.config(state=tk.NORMAL)
            return

        image_files = sorted(
            f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".png", ".jpeg"))
        )
        if not image_files:
            self.log("⚠️ Nisu pronađene slike u odabranom folderu.")
            self.btn_start.config(state=tk.NORMAL)
            return

        images = []
        widths = []
        for file in image_files:
            img = Image.open(os.path.join(folder, file)).convert("RGB")
            scale = video_height / img.height
            new_width = int(img.width * scale)
            images.append(img.resize((new_width, video_height)))
            widths.append(new_width)

        def get_padded_width(w):
            return w + padding

        output_folder = os.path.join(folder, output_folder_name)
        os.makedirs(output_folder, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = os.path.join(output_folder, f"output_{timestamp}.mp4")

        writer = imageio.get_writer(output_path, fps=fps)

        # ----- total frames -----
        intro_frames = intro_duration * fps
        entry_frames = 3 * entry_duration
        x_base = video_width // 2 - sum(get_padded_width(widths[i]) for i in range(3)) // 2
        total_strip_width = sum(get_padded_width(w) for w in widths) - padding
        total_scroll_pixels = x_base + total_strip_width
        scroll_frames = (total_scroll_pixels + pixels_per_frame - 1) // pixels_per_frame
        end_frames = end_duration * fps

        self.total_frames = intro_frames + entry_frames + scroll_frames + end_frames
        self.frames_done = 0
        self.progress['maximum'] = self.total_frames
        self.update_progress(0)

        # ----- crni intro -----
        if intro_frames:
            black = np.zeros((video_height, video_width, 3), dtype=np.uint8)
            for _ in range(intro_frames):
                writer.append_data(black)
                self.update_progress()

        # ----- animacija ulaska -----
        self.log("🗳️ Animiram prve 3 slike…")
        directions = ["bottom", "top", "bottom"]
        static_frame = Image.new("RGB", (video_width, video_height), bg_color)

        for idx in range(3):
            img = images[idx]
            w = widths[idx]
            x_pos = x_base + sum(get_padded_width(widths[i]) for i in range(idx))
            for f in range(entry_duration):
                frame = static_frame.copy()
                if directions[idx] == "bottom":
                    y_pos = video_height - int((f / entry_duration) * video_height)
                else:
                    y_pos = -img.height + int((f / entry_duration) * video_height)
                frame.paste(img, (int(x_pos), int(y_pos)))
                writer.append_data(np.array(frame))
                self.update_progress()
            static_frame.paste(img, (int(x_pos), 0))
            draw = ImageDraw.Draw(static_frame)
            draw.rectangle([int(x_pos) + w, 0, int(x_pos) + w + padding, video_height], fill=pad_color)

        # ----- horizontalni skrol -----
        self.log("🔁 Scroll…")
        for i in range(scroll_frames + 1):
            frame = Image.new("RGB", (video_width, video_height), bg_color)
            offset = x_base - i * pixels_per_frame
            x_cursor = offset
            for img, w in zip(images, widths):
                if x_cursor + w < 0:
                    x_cursor += get_padded_width(w)
                    continue
                if x_cursor > video_width:
                    x_cursor += get_padded_width(w)
                    continue
                frame.paste(img, (int(x_cursor), 0))
                draw = ImageDraw.Draw(frame)
                draw.rectangle([int(x_cursor) + w, 0, int(x_cursor) + w + padding, video_height], fill=pad_color)
                x_cursor += get_padded_width(w)
            writer.append_data(np.array(frame))
            self.update_progress()

        # ----- crni ekran na kraju -----
        self.log("⏸️ Pauza na kraju…")
        black = np.zeros((video_height, video_width, 3), dtype=np.uint8)
        for _ in range(end_frames):
            writer.append_data(black)
            self.update_progress()

        writer.close()
        self.generated_video_path = output_path
        self.log("✅ Video gotov!")
        self.progress['value'] = self.total_frames
        self.lbl_progress.config(text="100% – preostalo: 00:00")

        self.btn_start.config(state=tk.NORMAL)
        self.btn_open.config(state=tk.NORMAL)
        self.btn_open_folder.config(state=tk.NORMAL)

        print(f"Ukupno vreme: {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoApp(root)
    root.mainloop()
