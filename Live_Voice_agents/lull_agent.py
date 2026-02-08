#!/usr/bin/env python3
import argparse
import os
import re
import threading
from typing import List, Optional, Tuple

import requests

AGENT_NAME = "Lull"
USER_NAME = "Amita"
GREETING = "Hi Amita , How may I help you?"

SUPPORTED_LANGS = {
    "hindi": "hi",
    "marathi": "mr",
    "french": "fr",
}

DEFAULT_TRANSLATE_ENDPOINT = "https://libretranslate.de/translate"


def normalize_whitespace(text: str) -> str:
    cleaned = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return "\n".join(lines)


def dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    unique = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


class Speaker:
    def __init__(self) -> None:
        self._engine = None
        self._thread: Optional[threading.Thread] = None
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
        except Exception:
            self._engine = None

    def speak(self, text: str) -> None:
        if not text:
            return
        if self._engine is None:
            print(text)
            return
        self._engine.say(text)
        self._engine.runAndWait()

    def speak_async(self, text: str) -> None:
        if self._engine is None:
            print(text)
            return
        if self._thread and self._thread.is_alive():
            self.stop()
        self._thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._engine is None:
            return
        try:
            self._engine.stop()
        except Exception:
            pass


class Listener:
    def __init__(self, use_text_input: bool = False) -> None:
        self.use_text_input = use_text_input
        self._sr = None
        self._recognizer = None
        self._vosk_model = None
        self._warned_no_vosk = False

        if not self.use_text_input:
            try:
                import speech_recognition as sr

                self._sr = sr
                self._recognizer = sr.Recognizer()
            except Exception:
                self.use_text_input = True

        if not self.use_text_input:
            self._load_vosk_model()

    def _load_vosk_model(self) -> None:
        model_path = os.getenv("VOSK_MODEL_PATH", "").strip()
        if not model_path:
            return
        try:
            import vosk

            self._vosk_model = vosk.Model(model_path)
        except Exception:
            self._vosk_model = None

    def listen(self) -> str:
        if self.use_text_input or self._recognizer is None or self._sr is None:
            try:
                return input("You: ").strip()
            except EOFError:
                return ""

        if self._vosk_model is None:
            if not self._warned_no_vosk:
                print("Vosk model not set. Use --text or set VOSK_MODEL_PATH.")
                self._warned_no_vosk = True
            try:
                return input("You: ").strip()
            except EOFError:
                return ""

        with self._sr.Microphone() as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=10)

        try:
            text = self._recognizer.recognize_vosk(audio, self._vosk_model)
        except Exception:
            return ""
        return text.strip()


class ScreenReader:
    def __init__(self) -> None:
        self._available = False
        self._mss = None
        self._pytesseract = None
        self._image_cls = None
        try:
            import mss
            import pytesseract
            from PIL import Image

            self._mss = mss
            self._pytesseract = pytesseract
            self._image_cls = Image
            self._available = True
        except Exception:
            self._available = False

    def capture_text(self) -> Tuple[str, Optional[str]]:
        if not self._available:
            return "", "Screen OCR dependencies are not available."
        try:
            with self._mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                image = self._image_cls.frombytes(
                    "RGB",
                    screenshot.size,
                    screenshot.rgb,
                )
            text = self._pytesseract.image_to_string(image)
            return normalize_whitespace(text), None
        except Exception as exc:
            return "", f"Screen capture failed: {exc}"


class ScreenQnA:
    def __init__(self) -> None:
        self._qa_pipeline = None

    def answer(self, question: str, context: str) -> str:
        if not context:
            return "I could not read any text on the screen."

        transformer_answer = self._try_transformer_qa(question, context)
        if transformer_answer:
            return transformer_answer

        return self._heuristic_answer(question, context)

    def _try_transformer_qa(self, question: str, context: str) -> Optional[str]:
        if self._qa_pipeline is False:
            return None
        if self._qa_pipeline is None:
            model_name = os.getenv(
                "QA_MODEL_NAME",
                "distilbert-base-cased-distilled-squad",
            )
            try:
                from transformers import pipeline

                self._qa_pipeline = pipeline("question-answering", model=model_name)
            except Exception:
                self._qa_pipeline = False
                return None
        try:
            result = self._qa_pipeline(question=question, context=context)
            answer = result.get("answer", "").strip()
            if answer:
                return answer
        except Exception:
            return None
        return None

    def _heuristic_answer(self, question: str, context: str) -> str:
        lower = question.lower()
        context_lower = context.lower()

        if any(
            phrase in lower
            for phrase in (
                "what is on my screen",
                "what's on my screen",
                "read my screen",
                "read the screen",
                "what is on the screen",
                "what is on screen",
            )
        ):
            return self._summarize(context)

        keyword = self._extract_keyword(lower)
        if keyword:
            if keyword in context_lower:
                return f"Yes, I can see {keyword} on the screen."
            return f"I do not see {keyword} on the screen."

        return self._summarize(context)

    def _extract_keyword(self, lower_question: str) -> str:
        patterns = [
            r"do you see\s+(?:a|an|the)?\s*(.+)",
            r"is there\s+(?:a|an|the)?\s*(.+)",
            r"does it contain\s+(?:a|an|the)?\s*(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, lower_question)
            if match:
                phrase = match.group(1).strip(" .?!")
                if phrase:
                    return phrase
        return ""

    def _summarize(self, context: str) -> str:
        lines = context.splitlines()
        snippet = "\n".join(lines[:6])
        if len(snippet) > 600:
            snippet = snippet[:600].rstrip() + "..."
        return f"Here is what I can read from the screen:\n{snippet}"


class Translator:
    def __init__(self) -> None:
        self.endpoint = os.getenv("LIBRETRANSLATE_ENDPOINT", DEFAULT_TRANSLATE_ENDPOINT)
        self.api_key = os.getenv("LIBRETRANSLATE_API_KEY", "").strip()

    def translate(self, text: str, target_language: str) -> str:
        if not text:
            return "Please provide a sentence to translate."
        target_code = SUPPORTED_LANGS.get(target_language.lower())
        if not target_code:
            return "I can translate to Hindi, Marathi, or French."

        payload = {
            "q": text,
            "source": "en",
            "target": target_code,
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        try:
            response = requests.post(self.endpoint, json=payload, timeout=10)
            response.raise_for_status()
            translated = response.json().get("translatedText")
            if translated:
                return translated
        except Exception as exc:
            return f"Translation failed: {exc}"
        return "Translation failed."


class Vision:
    def __init__(self) -> None:
        self._cv2 = None
        self._model = None
        try:
            import cv2

            self._cv2 = cv2
        except Exception:
            self._cv2 = None

    def detect_objects(self) -> Tuple[List[str], Optional[str]]:
        if self._cv2 is None:
            return [], "OpenCV is not available."

        camera = self._cv2.VideoCapture(0)
        if not camera.isOpened():
            return [], "Camera is not available."

        success, frame = camera.read()
        camera.release()
        if not success:
            return [], "Unable to read from the camera."

        try:
            labels = self._detect_with_yolo(frame)
            return labels, None
        except Exception as exc:
            return [], f"Object detection failed: {exc}"

    def _detect_with_yolo(self, frame) -> List[str]:
        if self._model is None:
            from ultralytics import YOLO

            model_name = os.getenv("YOLO_MODEL_NAME", "yolov8n.pt")
            self._model = YOLO(model_name)

        results = self._model(frame, verbose=False)
        if not results:
            return []

        result = results[0]
        names = result.names or {}
        labels = []

        if hasattr(result, "boxes") and result.boxes is not None:
            for cls_id in result.boxes.cls.tolist():
                idx = int(cls_id)
                if isinstance(names, dict):
                    label = names.get(idx, str(idx))
                else:
                    label = names[idx] if idx < len(names) else str(idx)
                labels.append(label)

        return dedupe_preserve_order(labels)


class LullAgent:
    def __init__(self, use_text_input: bool = False) -> None:
        self.speaker = Speaker()
        self.listener = Listener(use_text_input=use_text_input)
        self.screen_reader = ScreenReader()
        self.screen_qa = ScreenQnA()
        self.translator = Translator()
        self.vision = Vision()

    def run(self) -> None:
        self.speaker.speak_async(f"{AGENT_NAME} is ready. Say 'Hi {AGENT_NAME}'.")
        while True:
            command = self.listener.listen()
            if not command:
                continue
            if self._is_stop(command):
                self.speaker.stop()
                continue

            response = self.handle_command(command)
            if response:
                self.speaker.speak_async(response)

    def handle_command(self, command: str) -> str:
        if self._is_greeting(command):
            return GREETING

        if self._is_translation_request(command):
            sentence, target = self._parse_translation(command)
            if not target:
                return "Please specify a target language: Hindi, Marathi, or French."
            return self.translator.translate(sentence, target)

        if self._is_screen_request(command):
            return self._handle_screen_question(command)

        if self._is_object_request(command):
            return self._handle_object_question()

        return (
            "I can help with screen reading, object detection, "
            "or translations to Hindi, Marathi, and French."
        )

    def _is_greeting(self, command: str) -> bool:
        return "hi lull" in command.lower()

    def _is_stop(self, command: str) -> bool:
        return command.strip().lower() == "stop"

    def _is_translation_request(self, command: str) -> bool:
        return "translate" in command.lower()

    def _is_screen_request(self, command: str) -> bool:
        lower = command.lower()
        return "screen" in lower or "on my screen" in lower

    def _is_object_request(self, command: str) -> bool:
        lower = command.lower()
        return any(
            phrase in lower
            for phrase in (
                "hand",
                "holding",
                "object",
                "camera",
                "see what i have",
            )
        )

    def _handle_screen_question(self, question: str) -> str:
        text, error = self.screen_reader.capture_text()
        if error:
            return error
        return self.screen_qa.answer(question, text)

    def _handle_object_question(self) -> str:
        labels, error = self.vision.detect_objects()
        if error:
            return error
        if not labels:
            return "I could not identify any objects in your hand."
        return f"I see: {', '.join(labels)}."

    def _parse_translation(self, command: str) -> Tuple[str, Optional[str]]:
        lower = command.lower()
        target = None
        for language in SUPPORTED_LANGS:
            if re.search(rf"\b{language}\b", lower):
                target = language
                break

        quoted = re.search(r"\"([^\"]+)\"", command)
        if quoted:
            sentence = quoted.group(1)
        else:
            sentence = re.sub(r"\btranslate\b", "", command, flags=re.IGNORECASE)
            if target:
                sentence = re.sub(
                    rf"\bto\s+{target}\b", "", sentence, flags=re.IGNORECASE
                )
                sentence = re.sub(
                    rf"\bin\s+{target}\b", "", sentence, flags=re.IGNORECASE
                )
            sentence = sentence.replace(":", " ")
        sentence = sentence.strip(" -")
        return sentence, target


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Lull voice agent.")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Use text input instead of microphone.",
    )
    args = parser.parse_args()

    agent = LullAgent(use_text_input=args.text)
    agent.run()


if __name__ == "__main__":
    main()
