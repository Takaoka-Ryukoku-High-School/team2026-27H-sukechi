import math
import random
import subprocess
import threading
import time

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


def speak(text: str):
    text = text.strip()
    if not text:
        return

    try:
        if pyttsx3 is not None:
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
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


def play_beep(freq: int = 880, duration: float = 0.18):
    for command in (
        ["bash", "-lc", f"play -q -n synth {duration} sine {freq} 2>/dev/null || true"],
        ["bash", "-lc", f"speaker-test -t sine -f {freq} -l 1 -s 1 >/dev/null 2>&1 || true"],
    ):
        try:
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return
        except FileNotFoundError:
            continue


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
    return max(8.0, min(180.0, 32.0 + wave * 14.0 + random.uniform(0.0, 12.0)))


def classify(distance: float):
    if distance < 30:
        return "近いです", "near"
    if distance > 80:
        return "遠いです", "far"
    return "少し離れています", "mid"


def main(page: ft.Page):
    page.title = "超音波音声通知 v2"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F3F7F5"
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    distance_text = ft.Text("--.- cm", size=52, weight=ft.FontWeight.BOLD, color="#1C2C2A")
    state_text = ft.Text("待機中", size=18, color="#4D5C58")
    mode_text = ft.Text("接続状態: 未確認 / 擬似計測", size=12, color="#5C6965")
    last_state = {"value": None}
    stop_event = threading.Event()

    def update_loop():
        while not stop_event.is_set():
            value = measure_distance_cm()
            label, mode = classify(value)
            distance_text.value = f"{value:.1f} cm"
            state_text.value = label
            mode_text.value = "接続状態: 実機接続済み" if GPIO is not None else "接続状態: 未確認 / 擬似計測"

            if last_state["value"] != mode:
                last_state["value"] = mode
                speak(label)
                if mode == "near":
                    play_beep(1100, 0.2)
                elif mode == "far":
                    play_beep(500, 0.25)

            page.update()
            time.sleep(0.8)

    def start_monitoring(event):
        if not getattr(page, "_monitoring", False):
            page._monitoring = True
            threading.Thread(target=update_loop, daemon=True).start()

    card = ft.Container(
        content=ft.Column(
            [
                ft.Text("超音波音声通知 v2", size=28, weight=ft.FontWeight.BOLD, color="#1B2B2A"),
                ft.Text("距離に応じて、音声と音で知らせます。", size=13, color="#586A66"),
                ft.Container(
                    content=ft.Column(
                        [distance_text, state_text],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    bgcolor="#EAF5EE",
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
        shadow=ft.BoxShadow(blur_radius=22, color="#D3E5D8", offset=ft.Offset(0, 8)),
    )

    page.add(card)
    start_monitoring(None)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
