import os
import numpy as np
from PIL import Image, ImageDraw
import imageio
import tkinter as tk
from tkinter import filedialog
import threading
import datetime
import webbrowser

# === PODEŠAVANJA ===
video_width = 1920
video_height = 1080
padding = 2                # razmak između slika (u px)
pad_color = (255, 255, 255)  # boja razmaka
bg_color = (0, 0, 0)       # pozadina (crno)
fps = 30
pixels_per_frame = 3       # brzina horiz. skrola (u px po frame‑u)
intro_duration = 0         # crni ekran na početku (s)
end_duration = 10          # crni ekran na kraju (s)
entry_duration = 45        # trajanje animacije ulaska (u frame‑ovima)
output_folder_name = "video"


class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Generator")

        tk.Label(root, text="Folder sa slikama:").pack()
        self.entry_folder = tk.Entry(root, width=60)
        self.entry_folder.pack()
        tk.Button(root, text="Izaberi folder", command=self.choose_folder).pack()

        # START dugme – zeleno, beo tekst, veliko
        self.btn_start = tk.Button(
            root,
            text="START",
            bg="green",
            fg="white",
            font=("Arial", 14, "bold"),
            command=self.start,
        )
        self.btn_start.pack(pady=10)

        self.btn_open = tk.Button(root, text="Otvori video", command=self.open_video, state=tk.DISABLED)
        self.btn_open.pack()

        self.status = tk.Label(root, text="", fg="blue")
        self.status.pack()

        self.generated_video_path = None

    # -------------- GUI pomoćne funkcije --------------
    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry_folder.delete(0, tk.END)
            self.entry_folder.insert(0, folder)

    def start(self):
        self.status.config(text="⏳ Generisanje u toku…")
        self.btn_start.config(state=tk.DISABLED)
        threading.Thread(target=self.generate_video, daemon=True).start()

    def open_video(self):
        if self.generated_video_path:
            webbrowser.open(self.generated_video_path)

    def log(self, msg):
        print(msg)
        self.status.config(text=msg)
        self.root.update()

    # -------------- Glavna logika --------------
    def generate_video(self):
        import moviepy.editor as mpy  # lokalni import da GUI ostane responsivan ako nema biblioteke

        folder = self.entry_folder.get()
        if not folder:
            self.log("⚠️ Niste izabrali folder.")
            self.btn_start.config(state=tk.NORMAL)
            return

        # Učitaj sve slike i skaliraj ih na 1080p visinu
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
            """Širina slike + padding"""
            return w + padding

        # ----- priprema output putanje -----
        output_folder = os.path.join(folder, output_folder_name)
        os.makedirs(output_folder, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = os.path.join(output_folder, f"output_{timestamp}.mp4")

        writer = imageio.get_writer(output_path, fps=fps)

        # ----- crni intro ako je definisan -----
        if intro_duration:
            black = np.zeros((video_height, video_width, 3), dtype=np.uint8)
            for _ in range(intro_duration * fps):
                writer.append_data(black)

        # ----- animacija ulaska prvih 3 slike -----
        self.log("🗳️ Animiram prve 3 slike…")
        directions = ["bottom", "top", "bottom"]

        # Statični frame u koji postepeno lijepimo prve tri slike
        static_frame = Image.new("RGB", (video_width, video_height), bg_color)
        x_base = video_width // 2 - sum(get_padded_width(widths[i]) for i in range(3)) // 2

        for idx in range(3):
            img = images[idx]
            w = widths[idx]
            x_pos = x_base + sum(get_padded_width(widths[i]) for i in range(idx))
            for f in range(entry_duration):
                frame = static_frame.copy()
                # ulaz odozdo ili odozgo
                if directions[idx] == "bottom":
                    y_pos = video_height - int((f / entry_duration) * video_height)
                else:
                    y_pos = -img.height + int((f / entry_duration) * video_height)
                frame.paste(img, (int(x_pos), int(y_pos)))
                writer.append_data(np.array(frame))
            # nakon animacije slika ostaje "zalijepljena" u static_frame
            static_frame.paste(img, (int(x_pos), 0))
            draw = ImageDraw.Draw(static_frame)
            draw.rectangle([int(x_pos) + w, 0, int(x_pos) + w + padding, video_height], fill=pad_color)

        # ----- horizontalni skrol svih slika -----
        self.log("🔁 Scroll…")

        total_strip_width = sum(get_padded_width(w) for w in widths) - padding  # ukupna širina panorame
        total_scroll_pixels = x_base + total_strip_width  # koliko mora da se pomeri ulevo da zadnja slika "izađe"
        scroll_frames = (total_scroll_pixels + pixels_per_frame - 1) // pixels_per_frame

        for i in range(scroll_frames + 1):
            frame = Image.new("RGB", (video_width, video_height), bg_color)
            offset = x_base - i * pixels_per_frame  # pomeraj ulevo u odnosu na početni raspored
            x_cursor = offset
            for img, w in zip(images, widths):
                # Potpuno levo izvan kadra
                if x_cursor + w < 0:
                    x_cursor += get_padded_width(w)
                    continue
                # Potpuno desno izvan kadra – još se nije pojavila
                if x_cursor > video_width:
                    x_cursor += get_padded_width(w)
                    continue
                frame.paste(img, (int(x_cursor), 0))
                draw = ImageDraw.Draw(frame)
                draw.rectangle([int(x_cursor) + w, 0, int(x_cursor) + w + padding, video_height], fill=pad_color)
                x_cursor += get_padded_width(w)
            writer.append_data(np.array(frame))

        # ----- crni ekran na kraju -----
        self.log("⏸️ Pauza na kraju…")
        black = np.zeros((video_height, video_width, 3), dtype=np.uint8)
        for _ in range(end_duration * fps):
            writer.append_data(black)

        writer.close()
        self.generated_video_path = output_path
        self.log("✅ Video gotov!")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_open.config(state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoApp(root)
    root.mainloop()
