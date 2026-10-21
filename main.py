import json
from pathlib import Path
from uuid import uuid4

import flet as ft


DATA_FILE = Path.home() / ".daily_note_tasks.json"
GREEN = "#2E6654"
GREEN_LIGHT = "#E2EDE5"
PAPER = "#F6F5EF"
INK = "#202C2A"
MUTED = "#77807B"
CORAL = "#CF6048"


def load_tasks():
    try:
        tasks = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(tasks, list):
            return [
                task
                for task in tasks
                if isinstance(task, dict)
                and isinstance(task.get("id"), str)
                and isinstance(task.get("text"), str)
                and isinstance(task.get("done"), bool)
            ]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_tasks(tasks):
    DATA_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def main(page: ft.Page):
    page.title = "今日の段取り | ToDo"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = PAPER
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    tasks = load_tasks()
    current_filter = "all"

    task_input = ft.TextField(
        hint_text="次にやることは？",
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
            progress_label.value = f"{sum(task['done'] for task in tasks)} / {len(tasks)} 件 完了"
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
        set_filter("all")

    def toggle_task(task_id):
        for task in tasks:
            if task["id"] == task_id:
                task["done"] = not task["done"]
                break
        persist()
        render()

    def delete_task(task_id):
        tasks[:] = [task for task in tasks if task["id"] != task_id]
        persist()
        render()

    def clear_done(event):
        tasks[:] = [task for task in tasks if not task["done"]]
        persist()
        render()

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
            f"{completed} / {len(tasks)} 件 完了" if tasks else "タスクはまだありません"
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
                "未完了のタスクはありません。いい調子！"
                if current_filter == "active" and tasks
                else "完了したタスクはまだありません。"
                if current_filter == "done" and tasks
                else "まずは、やることをひとつ書いてみましょう。"
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
        filter_buttons[key] = ft.TextButton(
            label,
            on_click=lambda event, value=key: set_filter(value),
        )

    today = ft.Text(
        __import__("datetime").date.today().strftime("%Y年%m月%d日"),
        size=12,
        color=MUTED,
    )
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
                                content=ft.Text("日", color="white", size=15, weight=ft.FontWeight.BOLD),
                                width=28,
                                height=28,
                                bgcolor=GREEN,
                                border_radius=14,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Text("DAILY NOTE", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=10,
                    ),
                    today,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Column(
                [
                    ft.Text("今日の段取り", size=38, color=INK, weight=ft.FontWeight.W_600),
                    ft.Text("ひとつずつ、進めていこう。", size=13, color=MUTED),
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
    workspace_card = content.controls[2]

    def resize_page(event):
        viewport_width = page.width or 748
        page.padding = 12 if viewport_width < 520 else 24
        content_width = min(700, max(272, viewport_width - page.padding * 2))
        app_container.width = content_width
        content.width = content_width
        workspace_card.width = content_width
        page.update()

    page.on_resize = resize_page
    page.add(app_container)
    render()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)