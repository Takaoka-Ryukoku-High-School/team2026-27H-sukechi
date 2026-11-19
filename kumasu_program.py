import asyncio
import json
import math
import random
import subprocess
import time
from datetime import date
from pathlib import Path
from uuid import uuid4

import flet as ft
from flet_audio import Audio
from flet_audio_recorder import AudioRecorder
from flet_audio_recorder.types import AudioEncoder, AudioRecorderConfiguration

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover
    GPIO = None


DATA_FILE = Path.home() / ".kumasu_program_tasks.json"
TRIG_PIN = 23
ECHO_PIN = 24
SPEED_OF_SOUND = 34300.0
GREEN = "#2E6654"
GREEN_LIGHT = "#E2EDE5"
PAPER = "#F6F5EF"
INK = "#202C2A"
MUTED = "#77807B"
CORAL = "#CF6048"


def measure_distance_cm():
    if GPIO is None:
        wave = math.sin(time.monotonic() / 2.0)
        value = max(5.0, min(200.0, 30.0 + wave * 18.0 + random.uniform(0.0, 10.0)))
        return value, "擬似計測モード（GPIO未導入）"

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(TRIG_PIN, GPIO.OUT)
        GPIO.setup(ECHO_PIN, GPIO.IN)
        GPIO.output(TRIG_PIN, False)
        time.sleep(0.05)

        GPIO.output(TRIG_PIN, True)
        time.sleep(0.00001)
        GPIO.output(TRIG_PIN, False)

        deadline = time.monotonic() + 0.05
        while GPIO.input(ECHO_PIN) == 0:
            if time.monotonic() >= deadline:
                return None, "センサーから応答がありません"
        pulse_start = time.monotonic()

        deadline = time.monotonic() + 0.05
        while GPIO.input(ECHO_PIN) == 1:
            if time.monotonic() >= deadline:
                return None, "センサーから応答がありません"
        pulse_end = time.monotonic()
        distance = (pulse_end - pulse_start) * SPEED_OF_SOUND / 2
        return max(0.0, distance), "実機で計測中"
    except Exception as error:
        return None, f"センサーエラー: {error}"


def classify_distance(distance):
    if distance < 30:
        return "近いです", "near"
    if distance > 80:
        return "遠いです", "far"
    return "ちょうどいいです", "ok"


def speak(text):
    text = text.strip()
    if not text:
        return

    if pyttsx3 is not None:
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 170)
            engine.say(text)
            engine.runAndWait()
            return
        except Exception:
            pass

    for command in (["espeak", text], ["espeak-ng", text], ["spd-say", text]):
        try:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return
        except FileNotFoundError:
            continue

    print(f"[VOICE] {text}")


def play_beep(frequency, duration):
    commands = [
        ["play", "-q", "-n", "synth", str(duration), "sine", str(frequency)],
        ["speaker-test", "-t", "sine", "-f", str(frequency), "-l", "1", "-s", "1"],
    ]
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0:
                return
        except FileNotFoundError:
            continue


def play_sos_alarm():
    for frequency, duration in (
        (1200, 0.18),
        (900, 0.18),
        (1200, 0.18),
        (900, 0.18),
        (1400, 0.28),
        (200, 0.38),
    ):
        play_beep(frequency, duration)
        time.sleep(0.06)


def load_tasks():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            tasks = []
            for item in data:
                if isinstance(item, dict):
                    task_id = item.get("id")
                    text = item.get("text")
                    done = item.get("done")
                    if isinstance(task_id, str) and isinstance(text, str) and isinstance(done, bool):
                        tasks.append({"id": task_id, "text": text, "done": done})
            return tasks
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_tasks(tasks):
    DATA_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def main(page: ft.Page):
    page.title = "くますずのプログラム"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = PAPER
    page.padding = 12
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    tasks = load_tasks()
    current_filter = "all"
    effect_audio = Audio(
        src=Path(__file__).with_name("bear-bell.wav").read_bytes(),
        volume=0.5,
    )
    recorder_status = ft.Text("録音の準備ができました", size=14, color=MUTED)
    recorded_audio = Audio(volume=1.0)
    recorder = AudioRecorder(
        configuration=AudioRecorderConfiguration(
            encoder=AudioEncoder.WAV,
            channels=1,
            sample_rate=44100,
        )
    )
    page.services.extend([effect_audio, recorded_audio, recorder])

    async def play_effect():
        await effect_audio.play()

    task_input = ft.TextField(
        hint_text="今日の目標は？",
        expand=True,
        autofocus=True,
        border_radius=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor="#FFFEFA",
        text_size=15,
        on_submit=lambda event: add_task(event),
    )
    task_list = ft.Column(spacing=0)
    task_count = ft.Text(color=MUTED, size=12)
    progress_label = ft.Text(color=MUTED, size=11)
    clear_done_button = ft.TextButton(
        "完了した項目を削除",
        icon=ft.Icons.DELETE_OUTLINE,
        style=ft.ButtonStyle(color=CORAL),
        on_click=lambda event: clear_done(event),
    )
    filter_buttons = {}

    def persist():
        try:
            save_tasks(tasks)
            total = len(tasks)
            done_count = sum(task["done"] for task in tasks)
            progress_label.value = f"{done_count} / {total} 件 完了"
        except OSError:
            progress_label.value = "保存できませんでした。書き込み権限をご確認ください。"

    def set_filter(value):
        nonlocal current_filter
        current_filter = value
        render()

    def add_task(event):
        text = task_input.value.strip()
        if not text:
            return
        tasks.insert(0, {"id": str(uuid4()), "text": text, "done": False})
        task_input.value = ""
        persist()
        page.run_task(play_effect)
        set_filter("all")

    def toggle_task(task_id):
        for task in tasks:
            if task["id"] == task_id:
                was_done = task["done"]
                task["done"] = not task["done"]
                if not was_done:
                    page.run_task(play_effect)
                break
        persist()
        render()

    def delete_task(task_id):
        task_exists = any(task["id"] == task_id for task in tasks)
        tasks[:] = [task for task in tasks if task["id"] != task_id]
        if task_exists:
            page.run_task(play_effect)
        persist()
        render()

    def clear_done(event):
        had_completed_tasks = any(task["done"] for task in tasks)
        tasks[:] = [task for task in tasks if not task["done"]]
        if had_completed_tasks:
            page.run_task(play_effect)
        persist()
        render()

    recording_path = None
    record_directory = Path.home() / "KumasuRecordings"

    async def start_recording(event):
        nonlocal recording_path
        try:
            if page.web:
                recording_path = None
                started = await recorder.start_recording()
            else:
                record_directory.mkdir(parents=True, exist_ok=True)
                recording_path = str(record_directory / f"recording_{time.strftime('%Y%m%d_%H%M%S')}.wav")
                started = await recorder.start_recording(recording_path)
            if not started:
                recording_path = None
                recorder_status.value = "録音を開始できませんでした。マイクの許可を確認してください。"
            else:
                recorder_status.value = "録音中..."
        except Exception as error:
            recording_path = None
            recorder_status.value = f"録音を開始できませんでした: {error}"
        finally:
            page.update()

    async def stop_recording(event):
        nonlocal recording_path
        try:
            stopped_path = await recorder.stop_recording()
            if stopped_path:
                recording_path = stopped_path
                recorder_status.value = (
                    "録音を保存しました"
                    if str(stopped_path).startswith(("blob:", "http:", "https:"))
                    else f"録音を保存しました: {Path(stopped_path).name}"
                )
            else:
                recorder_status.value = "録音を停止しました"
        except Exception as error:
            recorder_status.value = f"録音を停止できませんでした: {error}"
        finally:
            page.update()

    async def play_recording(event):
        nonlocal recording_path
        if not recording_path:
            recorder_status.value = "再生する録音がありません"
            page.update()
            return
        try:
            if not str(recording_path).startswith(("blob:", "http:", "https:", "/")):
                recording_path = str(Path(recording_path).resolve())
            recorded_audio.src = recording_path
            recorded_audio.update()
            await recorded_audio.play()
            recorder_status.value = "録音を再生しています"
        except Exception as error:
            recorder_status.value = f"録音を再生できませんでした: {error}"
        finally:
            page.update()

    sensor_distance = ft.Text("--.- cm", size=52, weight=ft.FontWeight.BOLD, color=INK)
    sensor_state = ft.Text("計測を開始しています", size=18, color=MUTED)
    sensor_mode = ft.Text("", size=12, color=MUTED)
    manual_distance = ft.Text("50.0 cm", size=42, weight=ft.FontWeight.BOLD, color=INK)
    manual_state = ft.Text("距離を調整してください", size=18, color=MUTED)
    manual_slider = ft.Slider(
        min=0,
        max=200,
        value=50,
        divisions=200,
        label="{value:.1f} cm",
        on_change=lambda event: update_manual_distance(event),
    )
    current_view = "tasks"
    last_sensor_state = None
    sensor_monitor_started = False

    def update_manual_distance(event):
        distance = float(event.control.value)
        label, _ = classify_distance(distance)
        manual_distance.value = f"{distance:.1f} cm"
        manual_state.value = label
        manual_state.color = CORAL if label == "近いです" else GREEN
        page.update()

    async def monitor_sensor():
        nonlocal last_sensor_state
        while True:
            if current_view == "sensor":
                value, mode = await asyncio.to_thread(measure_distance_cm)
                sensor_mode.value = mode
                if value is None:
                    sensor_distance.value = "--.- cm"
                    sensor_state.value = mode
                    last_sensor_state = None
                else:
                    label, state = classify_distance(value)
                    sensor_distance.value = f"{value:.1f} cm"
                    sensor_state.value = label
                    sensor_state.color = CORAL if state == "near" else GREEN
                    if last_sensor_state != state:
                        last_sensor_state = state
                        await asyncio.to_thread(speak, label)
                        if state == "near":
                            await asyncio.to_thread(play_beep, 1200, 0.15)
                        elif state == "far":
                            await asyncio.to_thread(play_beep, 400, 0.20)
                        else:
                            await asyncio.to_thread(play_beep, 700, 0.10)
                page.update()
            await asyncio.sleep(0.7)

    async def announce_manual_distance(event):
        distance = float(manual_slider.value)
        label, _ = classify_distance(distance)
        await asyncio.to_thread(speak, label)

    async def trigger_sos(event):
        sos_status.value = "SOS通知中..."
        page.update()
        try:
            await asyncio.to_thread(speak, "SOS")
            await asyncio.to_thread(speak, "助けてください")
            await asyncio.to_thread(play_sos_alarm)
            sos_status.value = "SOS通知が完了しました"
        except Exception as error:
            sos_status.value = f"通知に失敗しました: {error}"
        page.update()

    def render():
        visible_tasks = [
            task
            for task in tasks
            if current_filter == "all"
            or (current_filter == "active" and not task["done"])
            or (current_filter == "done" and task["done"])
        ]
        remaining = sum(not task["done"] for task in tasks)
        completed = len(tasks) - remaining
        task_count.value = f"未完了 {remaining} 件"
        progress_label.value = (
            f"{completed} / {len(tasks)} 件 完了" if tasks else "まだ予定はありません"
        )
        clear_done_button.visible = completed > 0

        for key, button in filter_buttons.items():
            selected = key == current_filter
            button.style = ft.ButtonStyle(
                color=GREEN if selected else MUTED,
                bgcolor=GREEN_LIGHT if selected else "transparent",
                shape=ft.RoundedRectangleBorder(radius=4),
            )

        rows = []
        for task in visible_tasks:
            checkbox = ft.Checkbox(
                value=task["done"],
                label=task["text"],
                expand=True,
                active_color=GREEN,
                label_style=ft.TextStyle(
                    color="#929992" if task["done"] else INK,
                    decoration=ft.TextDecoration.LINE_THROUGH if task["done"] else None,
                    size=14,
                ),
                on_change=lambda event, task_id=task["id"]: toggle_task(task_id),
            )
            delete_button = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=MUTED,
                tooltip=f"「{task['text']}」を削除",
                on_click=lambda event, task_id=task["id"]: delete_task(task_id),
            )
            rows.extend(
                [
                    ft.Row([checkbox, delete_button], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Divider(height=1, thickness=1, color="#DEDFD5"),
                ]
            )

        if not visible_tasks:
            empty_text = (
                "未完了の目標はありません。いい調子です！"
                if current_filter == "active" and tasks
                else "完了した目標はまだありません。"
                if current_filter == "done" and tasks
                else "まずは、今日やることを1つ書いてみましょう。"
            )
            rows = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("○", size=24, color="#9A7629", text_align=ft.TextAlign.CENTER),
                            ft.Text(empty_text, size=13, color=MUTED, text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=32,
                    alignment=ft.Alignment.CENTER,
                )
            ]

        task_list.controls = rows
        page.update()

    for key, label in (("all", "すべて"), ("active", "未完了"), ("done", "完了")):
        filter_buttons[key] = ft.TextButton(label, on_click=lambda event, value=key: set_filter(value))

    today = ft.Text(date.today().strftime("%Y年%m月%d日"), size=12, color=MUTED)
    composer = ft.Row(
        [
            task_input,
            ft.Button(
                "追加  ＋",
                on_click=add_task,
                bgcolor=GREEN,
                color="white",
                height=48,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
            ),
        ],
        spacing=10,
    )

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text("く", color="white", size=15, weight=ft.FontWeight.BOLD),
                                width=28,
                                height=28,
                                bgcolor=GREEN,
                                border_radius=14,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Text("KUMASU PROGRAM", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=10,
                    ),
                    today,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Column(
                [
                    ft.Text("くますずのプログラム", size=38, color=INK, weight=ft.FontWeight.W_600),
                    ft.Text("今日を、ちゃんと前に進めよう。", size=13, color=MUTED),
                ],
                spacing=4,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(content=composer, padding=18, bgcolor=GREEN_LIGHT),
                        ft.Container(
                            content=ft.Row(
                                [ft.Row(list(filter_buttons.values()), spacing=0), task_count],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            padding=ft.Padding(left=18, right=18, top=8, bottom=8),
                            border=ft.Border.only(bottom=ft.BorderSide(1, "#DEDFD5")),
                        ),
                        ft.Container(content=task_list, padding=ft.Padding.symmetric(horizontal=18)),
                        ft.Container(
                            content=ft.Row(
                                [progress_label, clear_done_button],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            padding=ft.Padding(left=18, right=18, top=8, bottom=8),
                            border=ft.Border.only(top=ft.BorderSide(1, "#DEDFD5")),
                        ),
                    ],
                    spacing=0,
                ),
                width=700,
                bgcolor="#FFFEFA",
                border=ft.Border.all(1, "#E3E3D9"),
                border_radius=8,
                shadow=ft.BoxShadow(blur_radius=28, color="#182D2314", offset=ft.Offset(0, 10)),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
        ],
        width=700,
        spacing=28,
    )

    app_container = ft.Container(content=content, width=700, padding=ft.Padding.only(top=18, bottom=32))

    sensor_container = ft.Container(
        content=ft.Column(
            [
                ft.Text("距離・音声通知", size=30, color=INK, weight=ft.FontWeight.BOLD),
                ft.Text("センサー計測と、手動での距離判定を使えます。", size=13, color=MUTED),
                ft.Container(
                    content=ft.Column(
                        [sensor_distance, sensor_state, sensor_mode],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    padding=24,
                    bgcolor=GREEN_LIGHT,
                    border_radius=8,
                ),
                ft.Divider(color="#DEDFD5"),
                ft.Text("手動で距離を確認", size=18, color=INK, weight=ft.FontWeight.BOLD),
                ft.Text("スマホなど、センサーがない場合はこちらで試せます。", size=13, color=MUTED),
                ft.Container(
                    content=ft.Column(
                        [
                            manual_distance,
                            manual_state,
                            manual_slider,
                            ft.Button(
                                "判定を音声で聞く",
                                icon=ft.Icons.VOLUME_UP,
                                on_click=announce_manual_distance,
                                bgcolor=GREEN,
                                color="white",
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                    ),
                    padding=20,
                    bgcolor="#FFFEFA",
                    border=ft.Border.all(1, "#E3E3D9"),
                    border_radius=8,
                ),
            ],
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=700,
        padding=24,
        bgcolor="#FFFEFA",
        border=ft.Border.all(1, "#E3E3D9"),
        border_radius=8,
    )
    recording_container = ft.Container(
        content=ft.Column(
            [
                ft.Text("録音", size=30, color=INK, weight=ft.FontWeight.BOLD),
                ft.Text("マイクから音声を録音して保存・再生できます。", size=13, color=MUTED),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("マイク録音", size=18, color=INK, weight=ft.FontWeight.BOLD),
                            recorder_status,
                            ft.Row(
                                [
                                    ft.Button(
                                        "録音開始",
                                        icon=ft.Icons.FIBER_MANUAL_RECORD,
                                        on_click=start_recording,
                                        bgcolor=CORAL,
                                        color="white",
                                    ),
                                    ft.Button(
                                        "録音停止",
                                        icon=ft.Icons.STOP,
                                        on_click=stop_recording,
                                        bgcolor=GREEN,
                                        color="white",
                                    ),
                                    ft.Button(
                                        "再生",
                                        icon=ft.Icons.PLAY_ARROW,
                                        on_click=play_recording,
                                        bgcolor="#FFFEFA",
                                        color=GREEN,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                wrap=True,
                                spacing=8,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=14,
                    ),
                    padding=24,
                    bgcolor=GREEN_LIGHT,
                    border_radius=8,
                ),
            ],
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=700,
        padding=24,
        bgcolor="#FFFEFA",
        border=ft.Border.all(1, "#E3E3D9"),
        border_radius=8,
    )
    sos_status = ft.Text("ボタンを押すと、SOSと警告音を再生します。", size=14, color=MUTED)
    sos_container = ft.Container(
        content=ft.Column(
            [
                ft.Text("緊急 SOS", size=30, color=INK, weight=ft.FontWeight.BOLD),
                ft.Text("緊急時に音声と警告音で周囲に知らせます。", size=13, color=MUTED),
                ft.Button(
                    ft.Text("SOS", size=42, weight=ft.FontWeight.BOLD, color="white"),
                    on_click=trigger_sos,
                    width=220,
                    height=220,
                    bgcolor="#D63A32",
                    color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=110)),
                ),
                sos_status,
            ],
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=700,
        padding=28,
        bgcolor="#FFFEFA",
        border=ft.Border.all(1, "#E3E3D9"),
        border_radius=8,
    )
    sensor_container.visible = False
    recording_container.visible = False
    sos_container.visible = False

    def select_view(view):
        nonlocal current_view, sensor_monitor_started
        if current_view == view:
            return
        current_view = view
        app_container.visible = view == "tasks"
        sensor_container.visible = view == "sensor"
        recording_container.visible = view == "recording"
        sos_container.visible = view == "sos"
        mobile_navigation.selected_index = ("tasks", "sensor", "recording", "sos").index(view)
        if view == "sensor" and not sensor_monitor_started:
            sensor_monitor_started = True
            page.run_task(monitor_sensor)
        page.update()

    mobile_navigation = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.CHECKLIST_OUTLINED,
                selected_icon=ft.Icons.CHECKLIST,
                label="段取り",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SENSORS_OUTLINED,
                selected_icon=ft.Icons.SENSORS,
                label="距離・音声",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.MIC_OUTLINED,
                selected_icon=ft.Icons.MIC,
                label="録音",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.EMERGENCY_OUTLINED,
                selected_icon=ft.Icons.EMERGENCY,
                label="SOS",
            ),
        ],
        selected_index=0,
        bgcolor="#FFFEFA",
        indicator_color=GREEN_LIGHT,
        on_change=lambda event: select_view(("tasks", "sensor", "recording", "sos")[event.control.selected_index]),
    )
    page.navigation_bar = mobile_navigation
    app_shell = ft.Column(
        [app_container, sensor_container, recording_container, sos_container],
        width=700,
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    def resize_page(event):
        viewport_width = page.width or 748
        page.padding = 12 if viewport_width < 520 else 24
        content_width = min(700, max(272, viewport_width - page.padding * 2))
        app_shell.width = content_width
        app_container.width = content_width
        content.width = content_width
        workspace_card.width = content_width
        sensor_container.width = content_width
        recording_container.width = content_width
        sos_container.width = content_width
        page.update()

    page.on_resize = resize_page
    workspace_card = content.controls[2]
    page.add(app_shell)
    render()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
