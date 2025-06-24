import os
import numpy as np
from PIL import Image, ImageDraw
import imageio
import tkinter as tk
from tkinter import filedialog
import threading
import datetime
import webbrowser

# Podešavanja
video_width = 1920
video_height = 1080
padding = 2
pad_color = (255, 255, 255)
bg_color = (0, 0, 0)
fps = 30
pixels_per_frame = 3
intro_duration = 0            # Crni ekran na početku u sekundama
end_duration = 5              # Crni ekran na kraju u sekundama
entry_duration = 45           # Broj frejmova za animaciju prve tri slike
output_folder_name = "video"

class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Generator")

        tk.Label(root, text="Folder sa slikama:").pack()
        self.entry_folder = tk.Entry(root, width=60)
        self.entry_folder.pack()
        tk.Button(root, text="Izaberi folder", command=self.choose_folder).pack()

        self.btn_start = tk.Button(root, text="START", bg="green", fg="white", font=("Arial", 14, "bold"), command=self.start)
        self.btn_start.pack(pady=10)

        self.btn_open = tk.Button(root, text="Otvori video", command=self.open_video, state=tk.DISABLED)
        self.btn_open.pack()

        self.status = tk.Label(root, text="", fg="blue")
        self.status.pack()

        self.generated_video_path = None

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry_folder.delete(0, tk.END)
            self.entry_folder.insert(0, folder)

    def start(self):
        self.status.config(text="⏳ Generisanje u toku...")
        self.btn_start.config(state=tk.DISABLED)
        threading.Thread(target=self.generate_video).start()

    def open_video(self):
        if self.generated_video_path:
            webbrowser.open(self.generated_video_path)

    def log(self, msg):
        print(msg)
        self.status.config(text=msg)
        self.root.update()

    def generate_video(self):
        import moviepy.editor as mpy

        folder = self.entry_folder.get()
        if not folder:
            self.log("⚠️ Niste izabrali folder.")
            self.btn_start.config(state=tk.NORMAL)
            return

        image_files = sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith((".jpg", ".png", ".jpeg"))
        ])

        images = []
        widths = []

        for file in image_files:
            img = Image.open(os.path.join(folder, file)).convert("RGB")
            scale = video_height / img.height
            new_width = int(img.width * scale)
            img = img.resize((new_width, video_height))
            images.append(img)
            widths.append(new_width)

        def get_padded_width(w):
            return w + padding

        output_folder = os.path.join(folder, output_folder_name)
        os.makedirs(output_folder, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = os.path.join(output_folder, f"panorama_output_{timestamp}.mp4")

        writer = imageio.get_writer(output_path, fps=fps)

        if intro_duration > 0:
            black = np.zeros((video_height, video_width, 3), dtype=np.uint8)
            for _ in range(intro_duration * fps):
                writer.append_data(black)

        self.log("🗳️ Animiram prve 3 slike...")

        directions = ["bottom", "top", "bottom"]
        static_frame = Image.new("RGB", (video_width, video_height), bg_color)
        x_base = video_width // 2 - sum(get_padded_width(widths[i]) for i in range(3)) // 2

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
            static_frame.paste(img, (int(x_pos), 0))
            draw = ImageDraw.Draw(static_frame)
            draw.rectangle([int(x_pos) + w, 0, int(x_pos) + w + padding, video_height], fill=pad_color)

        self.log("🔁 Scroll...")

        scroll_images = images
        scroll_widths = widths
        total_scroll_width = sum(get_padded_width(w) for w in scroll_widths)
        scroll_frames = (total_scroll_width + video_width) // pixels_per_frame

        for i in range(scroll_frames + 1):
            frame = Image.new("RGB", (video_width, video_height), bg_color)
            x = video_width - i * pixels_per_frame
            for img, width in zip(scroll_images, scroll_widths):
                if x + width < 0:
                    x += get_padded_width(width)
                    continue
                if x > video_width:
                    x += get_padded_width(width)
                    continue
                frame.paste(img, (int(x), 0))
                draw = ImageDraw.Draw(frame)
                draw.rectangle([int(x) + width, 0, int(x) + width + padding, video_height], fill=pad_color)
                x += get_padded_width(width)
            writer.append_data(np.array(frame))

        self.log("⏸️ Pauza na kraju...")
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
