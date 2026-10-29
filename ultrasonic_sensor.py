import math
import random
import threading
import time
from typing import Optional

import flet as ft

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover
    GPIO = None


TRIG_PIN = 23
ECHO_PIN = 24
SPEED_OF_SOUND = 34300.0


def measure_distance_cm() -> float:
    """HC-SR04 で距離を測る。実機が無い場合は擬似値を返す。"""
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
    return max(5.0, min(200.0, 30.0 + wave * 18.0 + random.uniform(0.0, 10.0)))


def main(page: ft.Page):
    page.title = "超音波距離計"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F3F6F4"
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    status_text = ft.Text("超音波センサーを起動中...", size=14, color="#4A5C56")
    distance_text = ft.Text("--.- cm", size=52, weight=ft.FontWeight.BOLD, color="#1E3A35")
    mode_text = ft.Text("実機接続: 未確認 / 擬似計測モード", size=12, color="#62716A")
    stop_event = threading.Event()

    def update_panel():
        while not stop_event.is_set():
            value = measure_distance_cm()
            distance_text.value = f"{value:.1f} cm"
            status_text.value = "近づいています" if value < 30 else "距離が適切です" if value < 80 else "少し離れています"
            mode_text.value = "実機接続: あり" if GPIO is not None else "実機接続: 未確認 / 擬似計測モード"
            page.update()
            time.sleep(0.5)

    def start_monitoring(event):
        if not getattr(page, "_monitoring", False):
            page._monitoring = True
            threading.Thread(target=update_panel, daemon=True).start()

    card = ft.Container(
        content=ft.Column(
            [
                ft.Text("超音波距離計", size=28, weight=ft.FontWeight.BOLD, color="#1F2B2A"),
                ft.Text("距離を測って、物体との間隔を確認します。", size=13, color="#5D6864"),
                ft.Container(
                    content=ft.Column(
                        [
                            distance_text,
                            status_text,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    bgcolor="#EAF5EF",
                    padding=24,
                    border_radius=18,
                    width=420,
                ),
                mode_text,
                ft.ElevatedButton("計測を開始", on_click=start_monitoring, bgcolor="#2E6654", color="white"),
            ],
            spacing=18,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=520,
        padding=24,
        border_radius=18,
        bgcolor="white",
        shadow=ft.BoxShadow(blur_radius=20, color="#c9d4cf", offset=ft.Offset(0, 8)),
    )

    page.add(card)
    start_monitoring(None)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
