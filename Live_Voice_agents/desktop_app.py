#!/usr/bin/env python3
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext

from lull_agent import AGENT_NAME, GREETING, LullAgent


class DesktopApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Lull - Desktop Voice Agent")
        self.root.geometry("820x640")

        self.agent = LullAgent(
            use_text_input=False,
            allow_text_fallback=False,
            allow_cloud_fallback=True,
        )

        self.listening = False
        self.queue: "queue.Queue[tuple[str, str]]" = queue.Queue()

        self.status_var = tk.StringVar(value="Idle")

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

        tk.Label(
            self.root,
            text=(
                "Say \"Hi Lull\" or ask about your screen or hand-held objects. "
                "If no Vosk model is set, Google Web Speech is used."
            ),
            wraplength=780,
            justify=tk.LEFT,
        ).pack(fill=tk.X, padx=12)

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
            response = self.agent.handle_command(command)
            if response:
                self.queue.put((AGENT_NAME, response))
                self.agent.speaker.speak_async(response)

    def on_close(self) -> None:
        self.listening = False
        self.agent.speaker.stop()
        self.root.destroy()


def main() -> None:
    app = DesktopApp()
    app.root.mainloop()


if __name__ == "__main__":
    main()
