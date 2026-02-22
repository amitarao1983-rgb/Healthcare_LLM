import re
from typing import Optional, Tuple

import numpy as np
import pytesseract
import streamlit as st
from PIL import Image

from lull_agent import (
    AGENT_NAME,
    GREETING,
    SUPPORTED_LANGS,
    ScreenQnA,
    Translator,
    Vision,
    normalize_whitespace,
)


OBJECT_TRIGGERS = (
    "hand",
    "holding",
    "object",
    "camera",
    "see what i have",
)


def parse_translation(command: str) -> Tuple[str, Optional[str]]:
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
            sentence = re.sub(rf"\bto\s+{target}\b", "", sentence, flags=re.IGNORECASE)
            sentence = re.sub(rf"\bin\s+{target}\b", "", sentence, flags=re.IGNORECASE)
        sentence = sentence.replace(":", " ")
    sentence = sentence.strip(" -")
    return sentence, target


@st.cache_resource(show_spinner=False)
def get_screen_qa() -> ScreenQnA:
    return ScreenQnA()


@st.cache_resource(show_spinner=False)
def get_translator() -> Translator:
    return Translator()


@st.cache_resource(show_spinner=False)
def get_vision() -> Vision:
    return Vision()


def extract_text_from_image(image: Image.Image) -> str:
    text = pytesseract.image_to_string(image)
    return normalize_whitespace(text)


def to_frame(image: Image.Image) -> np.ndarray:
    frame = np.array(image)
    if frame.ndim == 3 and frame.shape[2] == 3:
        return frame[:, :, ::-1]
    return frame


def handle_command(
    command: str,
    screen_text: str,
    camera_image: Optional[Image.Image],
) -> str:
    lower = command.strip().lower()
    if not lower:
        return ""

    if lower == "stop":
        return "Stopped."

    if f"hi {AGENT_NAME.lower()}" in lower:
        return GREETING

    if "translate" in lower:
        sentence, target = parse_translation(command)
        if not target:
            return "Please specify a target language: Hindi, Marathi, or French."
        return get_translator().translate(sentence, target)

    if "screen" in lower or "on my screen" in lower:
        if not screen_text:
            return "Upload a screenshot and extract text first."
        return get_screen_qa().answer(command, screen_text)

    if any(trigger in lower for trigger in OBJECT_TRIGGERS):
        if camera_image is None:
            return "Capture or upload an image first."
        labels, error = get_vision().detect_objects_in_frame(to_frame(camera_image))
        if error:
            return error
        if not labels:
            return "I could not identify any objects."
        return f"I see: {', '.join(labels)}."

    return (
        "I can help with screen OCR, object detection, or translations to Hindi, "
        "Marathi, and French."
    )


def main() -> None:
    st.set_page_config(
        page_title="Lull - Live Voice Agent",
        page_icon="L",
        layout="wide",
    )

    st.title("Lull - Live Voice Agent (Web)")
    st.write(
        "This web deployment supports screen OCR, object detection, and translation "
        "without API keys."
    )
    st.info(
        "Live screen capture and voice features are available only in the local app."
    )

    if "ocr_text" not in st.session_state:
        st.session_state.ocr_text = ""
    if "camera_image" not in st.session_state:
        st.session_state.camera_image = None
    if "last_response" not in st.session_state:
        st.session_state.last_response = ""
    if "translation_result" not in st.session_state:
        st.session_state.translation_result = ""

    command_tab, screen_tab, object_tab, translate_tab = st.tabs(
        ["Command", "Screen OCR", "Object detection", "Translation"]
    )

    with command_tab:
        st.subheader("Command mode")
        command = st.text_input(
            "Type a command",
            placeholder='Examples: "Hi Lull", "Read my screen", "Translate Hello to Hindi"',
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            send = st.button("Send", key="command_send")
        with col2:
            stop = st.button("Stop", key="command_stop")
        if stop:
            st.session_state.last_response = "Stopped."
        if send:
            response = handle_command(
                command,
                st.session_state.ocr_text,
                st.session_state.camera_image,
            )
            if response:
                st.session_state.last_response = response
        if st.session_state.last_response:
            st.text_area(
                "Response",
                st.session_state.last_response,
                height=120,
            )

    with screen_tab:
        st.subheader("Screen OCR")
        screen_file = st.file_uploader(
            "Upload a screenshot", type=["png", "jpg", "jpeg"], key="screen_upload"
        )
        if screen_file:
            screen_image = Image.open(screen_file).convert("RGB")
            st.image(screen_image, use_container_width=True)
            if st.button("Extract screen text", key="screen_extract"):
                try:
                    st.session_state.ocr_text = extract_text_from_image(screen_image)
                except Exception as exc:
                    st.error(f"OCR failed: {exc}")

        if st.session_state.ocr_text:
            st.text_area(
                "Extracted screen text",
                st.session_state.ocr_text,
                height=200,
            )

    with object_tab:
        st.subheader("Object detection")
        camera_input = st.camera_input("Capture an image", key="camera_input")
        upload_input = st.file_uploader(
            "Or upload an image", type=["png", "jpg", "jpeg"], key="object_upload"
        )
        image = None
        if camera_input is not None:
            image = Image.open(camera_input).convert("RGB")
        elif upload_input is not None:
            image = Image.open(upload_input).convert("RGB")

        if image is not None:
            st.image(image, use_container_width=True)
            st.session_state.camera_image = image
            if st.button("Identify objects", key="object_detect"):
                labels, error = get_vision().detect_objects_in_frame(to_frame(image))
                if error:
                    st.error(error)
                elif not labels:
                    st.warning("No objects detected.")
                else:
                    st.success(f"Detected: {', '.join(labels)}")

    with translate_tab:
        st.subheader("Translation")
        text = st.text_area(
            "English text to translate",
            height=120,
            key="translate_text",
        )
        target = st.selectbox("Target language", ["Hindi", "Marathi", "French"])
        if st.button("Translate", key="translate_button"):
            st.session_state.translation_result = get_translator().translate(
                text, target
            )
        if st.session_state.translation_result:
            st.text_area(
                "Translation result",
                st.session_state.translation_result,
                height=120,
            )


if __name__ == "__main__":
    main()
