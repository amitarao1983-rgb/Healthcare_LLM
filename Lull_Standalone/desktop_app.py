#!/usr/bin/env python3
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext
from typing import Optional

from lull_agent import AGENT_NAME, GREETING, LullAgent

try:
    import cv2
    from PIL import Image, ImageTk

    CV2_AVAILABLE = True
except Exception:
    cv2 = None
    Image = None
    ImageTk = None
    CV2_AVAILABLE = False


class DesktopApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Lull - Desktop Voice Agent")
        self.root.geometry("860x720")

        self.agent = LullAgent(
            use_text_input=False,
            allow_text_fallback=False,
            allow_cloud_fallback=True,
        )

        self.listening = False
        self.queue: "queue.Queue[tuple[str, str]]" = queue.Queue()

        self.status_var = tk.StringVar(value="Idle")
        self.camera_status_var = tk.StringVar(value="Camera: Off")
        self.camera_running = False
        self.camera_cap: Optional["cv2.VideoCapture"] = None
        self.latest_frame = None
        self.preview_image = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(200, self._process_queue)

    def _build_ui(self) -> None:
        header = tk.Label(
            self.root,
            text="Lull - Live Screen + Voice Desktop App",
            font=("Arial", 16, "bold"),
        )
        header.pack(pady=10)

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=12)
        tk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        tk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=6)

        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=12, pady=8)

        tk.Button(
            button_frame,
            text="Start Voice",
            command=self.start_listening,
            width=15,
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            button_frame,
            text="Stop Voice",
            command=self.stop_listening,
            width=15,
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            button_frame,
            text="Stop Speaking",
            command=self.agent.speaker.stop,
            width=15,
        ).pack(side=tk.LEFT, padx=4)

        camera_frame = tk.Frame(self.root)
        camera_frame.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(camera_frame, textvariable=self.camera_status_var).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        tk.Label(camera_frame, text="Camera index:").pack(side=tk.LEFT)
        self.camera_index = tk.IntVar(value=0)
        tk.Spinbox(
            camera_frame,
            from_=0,
            to=4,
            width=4,
            textvariable=self.camera_index,
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            camera_frame,
            text="Start Camera",
            command=self.start_camera,
            width=15,
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            camera_frame,
            text="Stop Camera",
            command=self.stop_camera,
            width=15,
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            camera_frame,
            text="Detect Objects",
            command=self.detect_objects_now,
            width=15,
        ).pack(side=tk.LEFT, padx=4)

        tk.Label(
            self.root,
            text=(
                "Say \"Hi Lull\" or ask about your screen or hand-held objects. "
                "If no Vosk model is set, Google Web Speech is used."
            ),
            wraplength=780,
            justify=tk.LEFT,
        ).pack(fill=tk.X, padx=12)

        self.preview_label = tk.Label(
            self.root,
            text="Camera preview will appear here.",
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
            width=80,
            height=10,
        )
        self.preview_label.pack(fill=tk.BOTH, expand=False, padx=12, pady=6)

        entry_frame = tk.Frame(self.root)
        entry_frame.pack(fill=tk.X, padx=12, pady=8)
        self.command_entry = tk.Entry(entry_frame)
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.command_entry.bind("<Return>", self._on_send)
        tk.Button(
            entry_frame,
            text="Send",
            command=self._handle_text_command,
            width=12,
        ).pack(side=tk.LEFT)

        self.chat_box = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=24)
        self.chat_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.chat_box.configure(state=tk.DISABLED)

        self._append_message(AGENT_NAME, f"{AGENT_NAME} is ready.")
        self._append_message(AGENT_NAME, GREETING)

    def _append_message(self, role: str, message: str) -> None:
        self.chat_box.configure(state=tk.NORMAL)
        self.chat_box.insert(tk.END, f"{role}: {message}\n")
        self.chat_box.configure(state=tk.DISABLED)
        self.chat_box.see(tk.END)

    def _process_queue(self) -> None:
        while True:
            try:
                role, message = self.queue.get_nowait()
            except queue.Empty:
                break
            self._append_message(role, message)
        self.root.after(200, self._process_queue)

    def _handle_text_command(self) -> None:
        command = self.command_entry.get().strip()
        if not command:
            return
        self.command_entry.delete(0, tk.END)
        self._handle_command(command)

    def _on_send(self, _event) -> None:
        self._handle_text_command()

    def _handle_command(self, command: str) -> None:
        self._append_message("You", command)
        if command.strip().lower() == "stop":
            self.agent.speaker.stop()
            self._append_message(AGENT_NAME, "Stopped.")
            return

        if self._is_object_request(command):
            response = self._handle_object_request()
        else:
            response = self.agent.handle_command(command)
        if response:
            self._append_message(AGENT_NAME, response)
            self.agent.speaker.speak_async(response)

    def start_listening(self) -> None:
        if self.listening:
            return
        self.listening = True
        self.status_var.set("Listening")
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

    def stop_listening(self) -> None:
        self.listening = False
        self.status_var.set("Idle")

    def _listen_loop(self) -> None:
        while self.listening:
            command = self.agent.listener.listen()
            if not command:
                continue
            self.queue.put(("You", command))
            if command.strip().lower() == "stop":
                self.agent.speaker.stop()
                self.queue.put((AGENT_NAME, "Stopped."))
                continue
            if self._is_object_request(command):
                response = self._handle_object_request()
            else:
                response = self.agent.handle_command(command)
            if response:
                self.queue.put((AGENT_NAME, response))
                self.agent.speaker.speak_async(response)

    def _is_object_request(self, command: str) -> bool:
        return self.agent._is_object_request(command)

    def _handle_object_request(self) -> str:
        if self.latest_frame is not None:
            labels, error = self.agent.vision.detect_objects_in_frame(self.latest_frame)
        else:
            labels, error = self.agent.vision.detect_objects()

        if error:
            if not self.camera_running:
                return f"{error} Start Camera to preview and try again."
            return error
        if not labels:
            return (
                "I could not identify any objects. Try brighter light, move the "
                "object closer, or use a common object like a phone, bottle, or cup."
            )
        details = self._format_detections()
        if details:
            return f"I see: {', '.join(labels)}. ({details})"
        return f"I see: {', '.join(labels)}."

    def _format_detections(self) -> str:
        detections = self.agent.vision.last_detections
        if not detections:
            return ""
        top = detections[:3]
        return ", ".join(f"{label} {conf:.2f}" for label, conf in top)

    def detect_objects_now(self) -> None:
        response = self._handle_object_request()
        self._append_message(AGENT_NAME, response)
        self.agent.speaker.speak_async(response)

    def start_camera(self) -> None:
        if self.camera_running:
            return
        if not CV2_AVAILABLE:
            self._append_message(
                AGENT_NAME, "OpenCV is not available. Camera preview is disabled."
            )
            return
        index = int(self.camera_index.get())
        self.camera_cap = cv2.VideoCapture(index)
        if not self.camera_cap.isOpened():
            self.camera_cap.release()
            self.camera_cap = None
            self._append_message(AGENT_NAME, "Camera is not available.")
            return
        self.camera_running = True
        self.camera_status_var.set("Camera: On")
        self._update_camera_preview()

    def stop_camera(self) -> None:
        self.camera_running = False
        self.camera_status_var.set("Camera: Off")
        if self.camera_cap is not None:
            self.camera_cap.release()
            self.camera_cap = None
        self.preview_label.configure(image="", text="Camera preview will appear here.")

    def _update_camera_preview(self) -> None:
        if not self.camera_running or self.camera_cap is None:
            return
        success, frame = self.camera_cap.read()
        if success:
            self.latest_frame = frame
            if Image is not None and ImageTk is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb)
                max_width = 640
                max_height = 360
                width, height = image.size
                scale = min(max_width / width, max_height / height, 1.0)
                if scale < 1.0:
                    image = image.resize(
                        (int(width * scale), int(height * scale)),
                        Image.BILINEAR,
                    )
                self.preview_image = ImageTk.PhotoImage(image)
                self.preview_label.configure(image=self.preview_image, text="")
        self.root.after(30, self._update_camera_preview)

    def on_close(self) -> None:
        self.listening = False
        self.stop_camera()
        self.agent.speaker.stop()
        self.root.destroy()


def main() -> None:
    app = DesktopApp()
    app.root.mainloop()


if __name__ == "__main__":
    main()
