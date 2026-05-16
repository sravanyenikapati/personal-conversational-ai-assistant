"""
Desktop UI — Tkinter chat window.

Layout:
  ┌──────────────────────────────────────────┐
  │  🤖 Personal AI Assistant           [✕] │
  ├──────────────────────────────────────────┤
  │                                          │
  │   [chat history scrollable area]         │
  │                                          │
  ├──────────────────────────────────────────┤
  │  [text input field]       [🎤] [Send ➤] │
  ├──────────────────────────────────────────┤
  │  Status: Ready                [Clear]    │
  └──────────────────────────────────────────┘

Key design decisions:
  - All AI + audio work runs in daemon threads so the UI never freezes.
  - Input mode is tracked (voice vs text) and used to decide output mode.
  - Voice output runs in its own thread via TTS.speak().
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import scrolledtext

from assistant.audio.stt import SpeechToText
from assistant.audio.tts import TextToSpeech
from assistant.config import get_settings
from assistant.core.brain import Brain
from assistant.logger import get_logger

log = get_logger(__name__)

# ── Colour palette ─────────────────────────────────────────────────────────────
_BG = "#1e1e2e"  # main background (dark)
_BG_INPUT = "#2a2a3e"  # input area
_BG_MSG_USER = "#3a3a5c"  # user message bubble
_BG_MSG_AI = "#2a2a3e"  # assistant message bubble
_FG = "#cdd6f4"  # primary text
_FG_DIM = "#7f849c"  # secondary text
_ACCENT = "#89b4fa"  # blue accent
_ACCENT_MIC = "#f38ba8"  # red for mic active
_BTN_SEND = "#89b4fa"
_FONT_FAMILY = "Segoe UI"


class ChatApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        settings = get_settings()

        self.title(settings.app_name)
        self.geometry("700x600")
        self.minsize(500, 400)
        self.configure(bg=_BG)
        self.resizable(True, True)

        # ── Core services ─────────────────────────────────────────────────────
        self._brain = Brain()
        self._tts = TextToSpeech()
        self._stt = SpeechToText()

        # ── State ─────────────────────────────────────────────────────────────
        self._input_was_voice = False  # tracks mode for output routing
        self._is_recording = False
        self._is_thinking = False

        # ── Build UI ──────────────────────────────────────────────────────────
        self._build_fonts()
        self._build_header()
        self._build_chat_area()
        self._build_input_area()
        self._build_status_bar()

        # ── Welcome message ───────────────────────────────────────────────────
        self._append_message(
            "Assistant",
            "Hello! I'm your personal AI assistant. You can type a message or press 🎤 to speak.",
            is_user=False,
        )

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        log.info("Desktop UI initialised.")

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_fonts(self) -> None:
        self._font_msg = tkfont.Font(family=_FONT_FAMILY, size=11)
        self._font_sender = tkfont.Font(family=_FONT_FAMILY, size=9, weight="bold")
        self._font_status = tkfont.Font(family=_FONT_FAMILY, size=9)
        self._font_btn = tkfont.Font(family=_FONT_FAMILY, size=11, weight="bold")

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=_BG_INPUT, pady=10)
        header.pack(fill=tk.X, side=tk.TOP)

        tk.Label(
            header,
            text="🤖  Personal AI Assistant",
            bg=_BG_INPUT,
            fg=_ACCENT,
            font=tkfont.Font(family=_FONT_FAMILY, size=13, weight="bold"),
        ).pack(side=tk.LEFT, padx=16)

        tk.Button(
            header,
            text="Clear Chat",
            bg=_BG_INPUT,
            fg=_FG_DIM,
            relief=tk.FLAT,
            font=self._font_status,
            cursor="hand2",
            command=self._clear_chat,
        ).pack(side=tk.RIGHT, padx=12)

    def _build_chat_area(self) -> None:
        frame = tk.Frame(self, bg=_BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 0))

        self._chat_display = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg=_BG,
            fg=_FG,
            font=self._font_msg,
            relief=tk.FLAT,
            padx=10,
            pady=10,
            spacing3=8,
            cursor="arrow",
        )
        self._chat_display.pack(fill=tk.BOTH, expand=True)

        # Tag styles for sender labels and message bubbles
        self._chat_display.tag_config("user_label", foreground=_ACCENT, font=self._font_sender)
        self._chat_display.tag_config("ai_label", foreground=_FG_DIM, font=self._font_sender)
        self._chat_display.tag_config("user_msg", foreground=_FG)
        self._chat_display.tag_config("ai_msg", foreground=_FG)
        self._chat_display.tag_config("thinking", foreground=_FG_DIM, font=self._font_status)

    def _build_input_area(self) -> None:
        frame = tk.Frame(self, bg=_BG_INPUT, pady=10)
        frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 4))

        # Mic button
        self._mic_btn = tk.Button(
            frame,
            text="🎤",
            font=self._font_btn,
            bg=_BG_INPUT,
            fg=_FG,
            relief=tk.FLAT,
            cursor="hand2",
            width=2,
            command=self._toggle_mic,
        )
        self._mic_btn.pack(side=tk.LEFT, padx=(8, 4))

        # Text input field
        self._input_var = tk.StringVar()
        self._input_field = tk.Entry(
            frame,
            textvariable=self._input_var,
            bg=_BG,
            fg=_FG,
            insertbackground=_FG,
            relief=tk.FLAT,
            font=self._font_msg,
        )
        self._input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, ipady=8)
        self._input_field.bind("<Return>", lambda _: self._on_send())
        self._input_field.focus_set()

        # Send button
        self._send_btn = tk.Button(
            frame,
            text="Send ➤",
            font=self._font_btn,
            bg=_BTN_SEND,
            fg=_BG,
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=4,
            command=self._on_send,
        )
        self._send_btn.pack(side=tk.RIGHT, padx=8)

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self, bg=_BG, pady=3)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(
            bar,
            textvariable=self._status_var,
            bg=_BG,
            fg=_FG_DIM,
            font=self._font_status,
            anchor=tk.W,
        ).pack(side=tk.LEFT, padx=14)

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _on_send(self) -> None:
        """Handle text input submission."""
        text = self._input_var.get().strip()
        if not text or self._is_thinking:
            return

        self._input_var.set("")
        self._input_was_voice = False
        self._process_user_input(text)

    def _toggle_mic(self) -> None:
        """Start recording; stop TTS first if it is currently speaking."""
        # If already recording, ignore second press
        if self._is_recording:
            return
        # Stop any ongoing TTS speech before recording
        self._tts.stop()
        if self._is_thinking:
            return

        self._is_recording = True
        self._mic_btn.configure(fg=_ACCENT_MIC, text="⏹")
        self._set_status("🎤 Listening...")

        def record_and_process() -> None:
            try:
                text = self._stt.transcribe(
                    on_recording_start=lambda: self._set_status("🎤 Recording...")
                )
            finally:
                self._is_recording = False
                self.after(0, lambda: self._mic_btn.configure(fg=_FG, text="🎤"))

            if text:
                self._input_was_voice = True
                self.after(0, lambda: self._process_user_input(text))
            else:
                self.after(0, lambda: self._set_status("⚠️ Nothing heard. Try again."))

        threading.Thread(target=record_and_process, daemon=True, name="stt-thread").start()

    def _process_user_input(self, user_text: str) -> None:
        """Display user message, call the AI brain, display and optionally speak reply."""
        self._append_message("You", user_text, is_user=True)
        self._set_thinking(True)

        was_voice = self._input_was_voice  # capture before thread

        def think_and_respond() -> None:
            reply = self._brain.chat(user_text)
            self.after(0, lambda: self._on_reply(reply, was_voice))

        threading.Thread(target=think_and_respond, daemon=True, name="brain-thread").start()

    def _on_reply(self, reply: str, was_voice: bool) -> None:
        """Called on the main thread once the AI has responded."""
        self._set_thinking(False)
        self._append_message("Assistant", reply, is_user=False)

        # Output mode mirrors input mode
        if was_voice:
            self._tts.speak(reply)

    # ── Chat Display Helpers ──────────────────────────────────────────────────

    def _append_message(self, sender: str, message: str, *, is_user: bool) -> None:
        """Add a message to the chat display."""
        self._chat_display.configure(state=tk.NORMAL)
        label_tag = "user_label" if is_user else "ai_label"
        msg_tag = "user_msg" if is_user else "ai_msg"

        self._chat_display.insert(tk.END, f"\n{sender}\n", label_tag)
        self._chat_display.insert(tk.END, f"{message}\n", msg_tag)
        self._chat_display.configure(state=tk.DISABLED)
        self._chat_display.see(tk.END)

    def _show_thinking_indicator(self) -> None:
        self._chat_display.configure(state=tk.NORMAL)
        self._chat_display.insert(tk.END, "\nAssistant\n", "ai_label")
        self._chat_display.insert(tk.END, "Thinking...\n", "thinking")
        self._chat_display.configure(state=tk.DISABLED)
        self._chat_display.see(tk.END)

    def _remove_thinking_indicator(self) -> None:
        self._chat_display.configure(state=tk.NORMAL)
        content = self._chat_display.get("1.0", tk.END)
        thinking_marker = "\nAssistant\nThinking...\n"
        if content.endswith(thinking_marker):
            self._chat_display.delete(f"end - {len(thinking_marker)}c", tk.END)
        self._chat_display.configure(state=tk.DISABLED)

    def _set_thinking(self, thinking: bool) -> None:
        self._is_thinking = thinking
        if thinking:
            self._set_status("🧠 Thinking...")
            self._show_thinking_indicator()
            self._send_btn.configure(state=tk.DISABLED)
        else:
            self._remove_thinking_indicator()
            self._set_status("Ready")
            self._send_btn.configure(state=tk.NORMAL)

    def _clear_chat(self) -> None:
        self._brain.reset()
        self._chat_display.configure(state=tk.NORMAL)
        self._chat_display.delete("1.0", tk.END)
        self._chat_display.configure(state=tk.DISABLED)
        self._append_message(
            "Assistant",
            "Conversation cleared. How can I help you?",
            is_user=False,
        )
        self._set_status("Conversation cleared.")

    def _set_status(self, text: str) -> None:
        self._status_var.set(text)

    def _on_close(self) -> None:
        self._tts.stop()
        log.info("Shutting down.")
        self.destroy()


def main() -> None:
    """Entry point for the desktop UI."""
    from assistant.logger import configure_root_logger

    settings = get_settings()
    configure_root_logger(settings.log_level)
    app = ChatApp()
    app.mainloop()


if __name__ == "__main__":
    main()
