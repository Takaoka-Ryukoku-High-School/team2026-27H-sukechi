import math
import random
import subprocess
import threading
import time
from urllib.parse import quote

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
THRESHOLD_NEAR = 30.0
THRESHOLD_FAR = 80.0


def speak(text: str):
    text = text.strip()
    if not text:
        return

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


def beep(freq: int, duration: float = 0.18):
    command = [
        "bash",
        "-lc",
        f"play -q -n synth {duration} sine {freq} 2>/dev/null || speaker-test -t sine -f {freq} -l 1 -s 1 >/dev/null 2>&1 || true",
    ]
    try:
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        pass


def sos_alert():
    for message in ("SOS", "助けてください"):
        speak(message)
    for freq, duration in ((1200, 0.18), (900, 0.18), (1200, 0.18), (900, 0.18), (1400, 0.28), (200, 0.38)):
        beep(freq, duration)
        time.sleep(0.06)


def build_mailto(email: str, name: str) -> str:
    subject = quote("緊急連絡 - SOS")
    body = quote(f"{name} 様\n\n緊急事態です。すぐに連絡をお願いします。\n\n---\n自動送信")
    return f"mailto:{email}?subject={subject}&body={body}"


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
    return max(5.0, min(200.0, 32.0 + wave * 10.0 + random.uniform(0.0, 12.0)))


def classify(distance: float):
    if distance < THRESHOLD_NEAR:
        return "近いです", "near"
    if distance > THRESHOLD_FAR:
        return "遠いです", "far"
    return "ちょうどいいです", "ok"


def main(page: ft.Page):
    page.title = "超音波音声通知 v3"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F3F8F5"
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    distance_text = ft.Text("--.- cm", size=52, weight=ft.FontWeight.BOLD, color="#1F2C2A")
    state_text = ft.Text("待機中", size=18, color="#4D5B58")
    mode_text = ft.Text("接続状態: 未確認 / 擬似計測", size=12, color="#5F6C69")
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
                    beep(1200, 0.15)
                elif mode == "far":
                    beep(400, 0.20)
                elif mode == "ok":
                    beep(700, 0.10)

            page.update()
            time.sleep(0.7)

    def start_monitoring(event):
        if not getattr(page, "_monitoring", False):
            page._monitoring = True
            threading.Thread(target=update_loop, daemon=True).start()

    def trigger_sos(event):
        threading.Thread(target=sos_alert, daemon=True).start()
        state_text.value = "SOS発信中"
        page.update()

    contacts = [
        {"name": "母", "phone": "+81-90-0000-0000", "email": "mother@example.com"},
        {"name": "父", "phone": "+81-90-1111-1111", "email": "father@example.com"},
    ]

    contact_cards = []
    for contact in contacts:
        contact_cards.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(contact["name"], weight=ft.FontWeight.BOLD, size=16, color="#1F2C2A"),
                        ft.Text(contact["phone"], size=12, color="#586A66"),
                        ft.Row(
                            [
                                ft.TextButton(
                                    "電話",
                                    on_click=lambda e, number=contact["phone"]: page.launch_url(f"tel:{number}"),
                                ),
                                ft.TextButton(
                                    "メール",
                                    on_click=lambda e, email=contact["email"], name=contact["name"]: page.launch_url(
                                        build_mailto(email, name)
                                    ),
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=6,
                    tight=True,
                ),
                bgcolor="#F7FAF8",
                border_radius=12,
                padding=12,
                border=ft.Border.all(1, "#DDE7E0"),
            )
        )

    sos_button = ft.Button(
        "SOS",
        on_click=trigger_sos,
        width=260,
        height=260,
        bgcolor="#D33B2E",
        color="white",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=130)),
    )

    card = ft.Container(
        content=ft.Column(
            [
                ft.Text("超音波音声通知 v3", size=28, weight=ft.FontWeight.BOLD, color="#1B2A27"),
                ft.Text("距離で状態を判定し、音声と音で知らせます。", size=13, color="#5A6965"),
                ft.Container(
                    content=ft.Column(
                        [distance_text, state_text],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    bgcolor="#E7F5ED",
                    padding=22,
                    border_radius=18,
                    width=420,
                ),
                mode_text,
                ft.Button("開始", on_click=start_monitoring, bgcolor="#2E6654", color="white"),
                sos_button,
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("緊急連絡先", size=18, weight=ft.FontWeight.BOLD, color="#1F2C2A"),
                            *contact_cards,
                        ],
                        spacing=12,
                        tight=True,
                    ),
                    width=420,
                    padding=12,
                    border_radius=16,
                    bgcolor="#FAFDFB",
                    border=ft.Border.all(1, "#E1E8E3"),
                ),
            ],
            spacing=18,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=560,
        padding=24,
        border_radius=18,
        bgcolor="white",
        shadow=ft.BoxShadow(blur_radius=22, color="#D1E3D7", offset=ft.Offset(0, 8)),
    )

    page.add(card)
    start_monitoring(None)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
