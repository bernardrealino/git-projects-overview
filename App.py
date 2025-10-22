import flet as ft
import os
import subprocess
import threading
import platform


# ─────────────────────────────
# Git Info Helper
# ─────────────────────────────
def get_git_info(path):
    if not os.path.exists(os.path.join(path, ".git")):
        return {"path": path, "is_git": False}

    def git(cmd):
        try:
            return subprocess.check_output(
                ["git", "-C", path] + cmd.split(), stderr=subprocess.DEVNULL
            ).decode().strip()
        except:
            return None

    branch = git("rev-parse --abbrev-ref HEAD")
    remote = git("remote get-url origin")
    status = git("status --porcelain")
    log = git("log -1 --format=%cd")
    dirty = "Clean" if not status else "Dirty"
    return {
        "path": path,
        "is_git": True,
        "branch": branch or "—",
        "remote": remote or "—",
        "dirty": dirty,
    }


# ─────────────────────────────
# OS Utilities
# ─────────────────────────────
def open_in_explorer(path):
    system = platform.system()
    if system == "Windows":
        os.startfile(path)
    elif system == "Darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])

def open_in_vscode(path):
    try:
        subprocess.Popen(["code", path])
    except FileNotFoundError:
        print("VS Code not found in PATH.")


# ─────────────────────────────
# Folder Row (Table Row)
# ─────────────────────────────
class FolderRow(ft.DataRow):
    def __init__(self, info, level, rescan_callback):
        self.info = info
        self.level = level
        self.rescan_callback = rescan_callback

        indent = " " * (level * 4)
        name = os.path.basename(info["path"])

        cells = [
            ft.DataCell(ft.Row([
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_ARROW_RIGHT,
                    icon_color="grey",
                    visible=info.get("has_subfolders", True),
                    on_click=lambda e: self.rescan_callback(info, self),
                ),
                ft.Text(indent + name, weight=ft.FontWeight.BOLD),
            ])),
            ft.DataCell(ft.Text("✅" if info["is_git"] else "❌")),
            ft.DataCell(ft.Text(info.get("branch", ""))),
            ft.DataCell(ft.Text(info.get("remote", ""), color="grey")),
            ft.DataCell(ft.Text(
                info.get("dirty", ""),
                color="green" if info.get("dirty") == "Clean" else "red",
            )),
            ft.DataCell(
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="Rescan",
                            on_click=lambda e: self.rescan_callback(info, self),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.FOLDER,
                            tooltip="Open in Explorer",
                            on_click=lambda e: open_in_explorer(info["path"]),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CODE,
                            tooltip="Open in VS Code",
                            on_click=lambda e: open_in_vscode(info["path"]),
                        ),
                    ]
                )
            ),
        ]
        super().__init__(cells=cells)


# ─────────────────────────────
# Main App
# ─────────────────────────────
def main(page: ft.Page):
    page.title = "Git Project Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = "auto"

    root_input = ft.TextField(label="Root Folder", width=500, value="D:\\Projects")
    pick_button = ft.IconButton(icon=ft.Icons.FOLDER_OPEN)
    scan_button = ft.ElevatedButton("Scan Projects", icon=ft.Icons.SEARCH)
    progress = ft.ProgressBar(width=400, visible=False)
    status = ft.Text("")

    # ───────────── File Picker ─────────────
    def pick_folder(e):
        def on_result(res: ft.FilePickerResultEvent):
            if res.path:
                root_input.value = res.path
                page.update()

        picker = ft.FilePicker(on_result=on_result)
        page.overlay.append(picker)
        page.update()
        picker.get_directory_path()

    pick_button.on_click = pick_folder

    # ───────────── Table Setup ─────────────
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Folder")),
            ft.DataColumn(ft.Text("Git")),
            ft.DataColumn(ft.Text("Branch")),
            ft.DataColumn(ft.Text("Remote")),
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Actions")),
        ],
        rows=[],
        heading_row_color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        column_spacing=30,
        data_row_min_height=40,
    )

    # ───────────── Folder Scanning ─────────────
    def scan_top_level(path):
        return [
            {"path": os.path.join(path, f), **get_git_info(os.path.join(path, f))}
            for f in os.listdir(path)
            if os.path.isdir(os.path.join(path, f))
        ]

    def rescan_folder(info, row_obj):
        def task():
            progress.visible = True
            status.value = f"Rescanning: {os.path.basename(info['path'])}..."
            page.update()

            subfolders = scan_top_level(info["path"])
            insert_index = data_table.rows.index(row_obj) + 1

            for sub_info in subfolders:
                new_row = FolderRow(sub_info, 1, rescan_folder)
                data_table.rows.insert(insert_index, new_row)
                insert_index += 1

            progress.visible = False
            status.value = f"✅ Finished {os.path.basename(info['path'])}"
            page.update()

        threading.Thread(target=task).start()

    def scan_projects(e):
        data_table.rows.clear()
        root = root_input.value.strip()
        if not os.path.exists(root):
            status.value = "❌ Path not found"
            page.update()
            return

        def task():
            progress.visible = True
            status.value = "Scanning top-level projects..."
            page.update()

            folders = scan_top_level(root)
            for info in folders:
                data_table.rows.append(FolderRow(info, 0, rescan_folder))

            progress.visible = False
            status.value = "✅ Scan complete"
            page.update()

        threading.Thread(target=task).start()

    scan_button.on_click = scan_projects

    # ───────────── Layout ─────────────
    page.add(
        ft.Row([root_input, pick_button, scan_button]),
        ft.Row([progress]),
        status,
        ft.Divider(),
        data_table,
    )


ft.app(target=main)
