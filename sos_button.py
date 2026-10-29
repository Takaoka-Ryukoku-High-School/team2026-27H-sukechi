import subprocess
import threading
import time

import flet as ft

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None


def speak(text: str):
    text = text.strip()
    if not text:
        return
    try:
        if pyttsx3 is not None:
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
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

    print(f"[SOS] {text}")


def beep_sequence():
    pattern = [
        (1200, 0.18),
        (900, 0.18),
        (1200, 0.18),
        (900, 0.18),
        (1400, 0.25),
        (200, 0.35),
    ]
    for freq, duration in pattern:
        command = [
            "bash",
            "-lc",
            f"play -q -n synth {duration} sine {freq} 2>/dev/null || speaker-test -t sine -f {freq} -l 1 -s 1 >/dev/null 2>&1 || true",
        ]
        try:
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except Exception:
            pass
        time.sleep(0.06)


def main(page: ft.Page):
    page.title = "SOSボタン"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F5F2F0"
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    status_text = ft.Text("緊急時はボタンを押してください", size=18, color="#5E534F")
    subtitle = ft.Text("SOS通知を再生します", size=13, color="#7A706C")

    def trigger_sos(event):
        status_text.value = "SOS発信中..."
        page.update()

        def run_alert():
            speak("SOS")
            speak("助けてください")
            beep_sequence()
            status_text.value = "発信完了"
            page.update()

        threading.Thread(target=run_alert, daemon=True).start()

    sos_button = ft.ElevatedButton(
        "SOS",
        width=220,
        height=220,
        on_click=trigger_sos,
        style=ft.ButtonStyle(
            bgcolor="#D63A32",
            color="white",
            shape=ft.RoundedRectangleBorder(radius=110),
        ),
        text_style=ft.TextStyle(size=42, weight=ft.FontWeight.BOLD),
    )

    card = ft.Container(
        content=ft.Column(
            [
                ft.Text("緊急 SOS", size=30, weight=ft.FontWeight.BOLD, color="#2B2A2A"),
                subtitle,
                sos_button,
                status_text,
            ],
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=440,
        padding=28,
        border_radius=24,
        bgcolor="#FFFDFD",
        shadow=ft.BoxShadow(blur_radius=26, color="#E7D2CF", offset=ft.Offset(0, 8)),
    )

    page.add(card)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
