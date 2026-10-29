import subprocess

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


def classify(distance: float):
    if distance < 30:
        return "近いです", "near"
    if distance > 80:
        return "遠いです", "far"
    return "ちょうどいいです", "ok"


def main(page: ft.Page):
    page.title = "スマホ用 超音波通知"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F2F7F5"
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    distance_value = ft.Text("50.0 cm", size=42, weight=ft.FontWeight.BOLD, color="#1E2C2A")
    state_text = ft.Text("待機中", size=22, color="#4C5B58")
    slider = ft.Slider(min=0, max=200, value=50, divisions=200, label="{value:.1f} cm", width=320)

    def update_status(event):
        distance = float(slider.value)
        label, _ = classify(distance)
        distance_value.value = f"{distance:.1f} cm"
        state_text.value = label
        state_text.color = "#C85D43" if label == "近いです" else "#4C7D6F" if label == "遠いです" else "#4A5C56"
        speak(label)
        page.update()

    card = ft.Container(
        content=ft.Column(
            [
                ft.Text("超音波距離通知", size=28, weight=ft.FontWeight.BOLD, color="#1B2C2A"),
                ft.Text("スマホで簡単に見て、音声で確認できます。", size=13, color="#5B6A67"),
                ft.Container(
                    content=ft.Column(
                        [distance_value, state_text],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    bgcolor="#EAF5EF",
                    padding=22,
                    border_radius=18,
                    width=360,
                ),
                ft.Text("距離を調整してください", size=12, color="#65726E"),
                slider,
                ft.ElevatedButton("判定して音声を出す", on_click=update_status, bgcolor="#2E6654", color="white"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=18,
        ),
        width=420,
        padding=24,
        border_radius=22,
        bgcolor="white",
        shadow=ft.BoxShadow(blur_radius=22, color="#D7E9DF", offset=ft.Offset(0, 8)),
    )

    page.add(card)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
