import math
import random
import subprocess
import threading
import time
from pathlib import Path

import flet as ft

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover
    GPIO = None


TRIG_PIN = 23
ECHO_PIN = 24
SPEED_OF_SOUND = 34300.0
TTS_CACHE = {}


def speak(text: str):
    key = text.strip()
    if key in TTS_CACHE and TTS_CACHE[key]:
        return
    TTS_CACHE[key] = True

    try:
        if pyttsx3 is not None:
            engine = pyttsx3.init()
            engine.setProperty("rate", 170)
            engine.say(text)
            engine.runAndWait()
            return
    except Exception:
        pass

    for command in (
        ["espeak", text],
        ["espeak-ng", text],
        ["spd-say", text],
    ):
        try:
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return
        except FileNotFoundError:
            continue

    print(f"[VOICE] {text}")


def measure_distance_cm() -> float:
    if GPIO is not None:
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(TRIG_PIN, GPIO.OUT)
            GPIO.setup(ECHO_PIN, GPIO.IN)
            GPIO.output(TRIG_PIN, False)
            time.sleep(0.05)

            GPIO.output(TRIG_PIN, True)
            time.sleep(0.00001)
            GPIO.output(TRIG_PIN, False)

            start = time.time()
            stop = time.time()
            while GPIO.input(ECHO_PIN) == 0 and time.time() - start < 0.05:
                start = time.time()
            while GPIO.input(ECHO_PIN) == 1 and time.time() - stop < 0.05:
                stop = time.time()

            duration = stop - start
            if duration <= 0:
                return 0.0
            distance = (duration * SPEED_OF_SOUND) / 2
            return max(0.0, distance)
        except Exception:
            pass

    wave = math.sin(time.monotonic() / 2.0)
    return max(5.0, min(200.0, 30.0 + wave * 12.0 + random.uniform(0.0, 8.0)))


def main(page: ft.Page):
    page.title = "超音波で近い遠いを音声で知らせる"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F2F7F5"
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    distance_text = ft.Text("--.- cm", size=52, weight=ft.FontWeight.BOLD, color="#1F2C2A")
    state_text = ft.Text("待機中", size=18, color="#4A5C56")
    mode_text = ft.Text("接続状態: 未確認 / 擬似計測", size=12, color="#5E6A67")
    last_state = {"value": None}
    stop_event = threading.Event()

    def classify(distance: float) -> str:
        if distance < 30:
            return "近いです"
        if distance > 80:
            return "遠いです"
        return "少し離れています"

    def update_ui():
        while not stop_event.is_set():
            value = measure_distance_cm()
            distance_text.value = f"{value:.1f} cm"
            label = classify(value)
            state_text.value = label
            mode_text.value = "接続状態: 実機接続済み" if GPIO is not None else "接続状態: 未確認 / 擬似計測"
            if last_state["value"] != label:
                last_state["value"] = label
                speak(label)
            page.update()
            time.sleep(0.8)

    def start_monitoring(event):
        if not getattr(page, "_monitoring", False):
            page._monitoring = True
            threading.Thread(target=update_ui, daemon=True).start()

    card = ft.Container(
        content=ft.Column(
            [
                ft.Text("近い・遠い音声通知", size=28, weight=ft.FontWeight.BOLD, color="#1B2A27"),
                ft.Text("超音波センサーの距離を見て、音声で知らせます。", size=13, color="#586A66"),
                ft.Container(
                    content=ft.Column(
                        [distance_text, state_text],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    bgcolor="#E7F4EA",
                    padding=22,
                    border_radius=18,
                    width=420,
                ),
                mode_text,
                ft.ElevatedButton("開始", on_click=start_monitoring, bgcolor="#2E6654", color="white"),
            ],
            spacing=18,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=520,
        padding=24,
        border_radius=18,
        bgcolor="white",
        shadow=ft.BoxShadow(blur_radius=22, color="#D4E2D8", offset=ft.Offset(0, 8)),
    )

    page.add(card)
    start_monitoring(None)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
