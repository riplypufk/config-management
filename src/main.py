import os
import shlex
import argparse
import base64
import zipfile
from pathlib import PurePosixPath

VFS_NAME = "user"

class VirtualFileSystem:
    def __init__(self):
        self.nodes = {
            "/": {"type": "dir"}
        }
        self.current_dir = "/"
        self.history = []

    def normalize_path(self, path):
        if not path.startswith("/"):
            path = "/" + path

        parts = []

        for part in path.split("/"):
            if part in ("", "."):
                continue

            if part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)

        return "/" + "/".join(parts)

    def add_directory(self, path):
        path = self.normalize_path(path)

        if path == "/":
            return

        parent = str(PurePosixPath(path).parent)
        self.add_directory(parent)

        if path in self.nodes:
            if self.nodes[path]["type"] != "dir":
                raise ValueError(
                    f"Путь уже занят файлом: {path}"
                )
            return

        self.nodes[path] = {"type": "dir"}

    def add_file(self, path, content):
        path = self.normalize_path(path)

        if path == "/":
            raise ValueError("Нельзя создать файл в корне")

        parent = str(PurePosixPath(path).parent)
        self.add_directory(parent)

        if path in self.nodes:
            raise ValueError(
                f"Путь уже существует: {path}"
            )

        self.nodes[path] = {
            "type": "file",
            "data": base64.b64encode(content).decode("ascii")
        }

    def load_zip(self, archive_path):
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                for item in archive.infolist():
                    raw_path = item.filename

                    if raw_path.startswith("/"):
                        raise ValueError(
                            f"Недопустимый путь в ZIP: {raw_path}"
                        )

                    parts = raw_path.rstrip("/").split("/")

                    if ".." in parts:
                        raise ValueError(
                            f"Недопустимый путь в ZIP: {raw_path}"
                        )

                    if raw_path in ("", "."):
                        continue

                    path = "/" + raw_path.rstrip("/")

                    if item.is_dir():
                        self.add_directory(path)
                    else:
                        content = archive.read(item)
                        self.add_file(path, content)

        except zipfile.BadZipFile as error:
            raise ValueError("Файл не является корректным ZIP") from error

    def save_zip(self, archive_path):
        with zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for path in sorted(self.nodes):
                if path == "/":
                    continue

                node = self.nodes[path]
                zip_path = path.lstrip("/")

                if node["type"] == "dir":
                    archive.writestr(zip_path.rstrip("/") + "/", "")
                else:
                    content = base64.b64decode(node["data"])
                    archive.writestr(zip_path, content)
    def resolve_path(self, path):
        if path.startswith("/"):
            return self.normalize_path(path)
        return self.normalize_path(
            self.current_dir + "/" + path
        )


    def _validate_directory(self, path):
        path = self.resolve_path(path)
        if path not in self.nodes:
            raise ValueError(f"Каталог не найден: {path}")
        if self.nodes[path]["type"] != "dir":
            raise ValueError(f"Это не каталог: {path}")
        return path

    @staticmethod
    def _format_directory_entry(name, node, long_format):
        is_dir = node["type"] == "dir"
        display_name = name + "/" if is_dir else name
        if not long_format:
            return display_name

        size = "-" if is_dir else len(base64.b64decode(node["data"]))
        node_type = "dir" if is_dir else "file"
        return f"{node_type:4} {str(size):>8} {display_name}"

    def list_directory(self, path, show_all=False, long_format=False):
        path = self._validate_directory(path)
        entries = (
            self._format_directory_entry(
                PurePosixPath(node_path).name, node, long_format
            )
            for node_path, node in self.nodes.items()
            if self._is_listable_entry(node_path, node, path, show_all)
        )
        return sorted(entries)

    @staticmethod
    def _is_listable_entry(node_path, node, path, show_all):
        is_child = (
            node_path not in (path, "/")
            and str(PurePosixPath(node_path).parent) == path
        )
        is_visible = (
            show_all or not PurePosixPath(node_path).name.startswith(".")
        )
        return is_child and is_visible

def expand_variables(text):
    return os.path.expandvars(text)

def parse_command(line):
    line = expand_variables(line)
    try:
        parts = shlex.split(line)
    except ValueError as error:
        print(f"Ошибка: {error}")
        return None, None, False
    if not parts:
        return None, None, True
    return parts[0], parts[1:], True

def _parse_ls_args(args):
    show_all = False
    long_format = False
    paths = []
    for arg in args:
        if not arg.startswith("-") or arg == "-":
            paths.append(arg)
            continue
        options = {"--all": "a", "--long": "l"}
        if arg.startswith("--"):
            if arg not in options:
                print(f"ls: неизвестный ключ: {arg}")
                return None
            arg = "-" + options[arg]
        for option in arg[1:]:
            if option not in ("a", "l"):
                print(f"ls: неизвестный ключ: -{option}")
                return None
            show_all |= option == "a"
            long_format |= option == "l"
    if len(paths) > 1:
        print("ls: укажите не более одного пути")
        return None
    return (paths[0] if paths else "."), show_all, long_format

def command_ls(args, vfs):
    parsed_args = _parse_ls_args(args)
    if parsed_args is None:
        return "error"
    path, show_all, long_format = parsed_args
    try:
        entries = vfs.list_directory(path, show_all, long_format)
    except ValueError as error:
        print(f"ls: {error}")
        return "error"
    for entry in entries:
        print(entry)
    return "ok"



def command_cd(args, vfs):
    if len(args) > 1:
        print("cd: укажите не более одного пути")
        return "error"
    path = args[0] if args else "/"
    target = vfs.resolve_path(path)
    if target not in vfs.nodes:
        print(f"cd: каталог не найден: {target}")
        return "error"
    if vfs.nodes[target]["type"] != "dir":
        print(f"cd: это не каталог: {target}")
        return "error"
    vfs.current_dir = target
    return "ok"


def command_pwd(args, vfs):
    if args:
        print("pwd: аргументы не допускаются")
        return "error"
    print(vfs.current_dir)
    return "ok"


def command_history(args, vfs):
    if args:
        print("history: аргументы не допускаются")
        return "error"
    for number, line in enumerate(vfs.history, start=1):
        print(f"{number}  {line}")
    return "ok"


def command_vfs_save(args, vfs):
    if len(args) != 1:
        print("vfs-save: укажите один путь для сохранения ZIP")
        return "error"
    try:
        vfs.save_zip(args[0])
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"vfs-save: ошибка сохранения: {error}")
        return "error"
    print(f"VFS сохранена в архив: {args[0]}")
    return "ok"


def execute_command(command, args, vfs):
    commands = {
        "ls": command_ls,
        "cd": command_cd,
        "pwd": command_pwd,
        "history": command_history,
        "vfs-save": command_vfs_save,
    }

    if command == "exit":
        if args:
            print("exit: неверное количество аргументов")
            return "error"
        return "exit"

    handler = commands.get(command)
    if handler is None:
        print(f"{command}: неизвестная команда")
        return "error"
    if command == "vfs-save":
        return handler(args, vfs)
    return handler(args, vfs)


def run_line(line, vfs, show_input=False):
    if show_input:
        print(f"{VFS_NAME}> {line}")
    if line.strip():
        vfs.history.append(line.strip())
    command, args, parsed = parse_command(line)
    if not parsed:
        return "error"
    if command is None:
        return "ok"
    return execute_command(command, args, vfs)


def run_script(script_path, vfs):
    try:
        with open(script_path, "r", encoding="utf-8") as script:
            for line_number, line in enumerate(script, start=1):
                line = line.rstrip("\r\n")

                if not line.strip() or line.lstrip().startswith("#"):
                    continue

                result = run_line(line, vfs, show_input=True)

                if result == "error":
                    print(
                        f"Скрипт остановлен: ошибка "
                        f"в строке {line_number}."
                    )
                    return 1

                if result == "exit":
                    print("Скрипт завершён командой exit.")
                    return 0

    except OSError as error:
        print(f"Ошибка чтения скрипта: {error}")
        return 1

    print("Скрипт выполнен успешно.")
    return 0


def run_interactive(vfs):
    while True:
        try:
            line = input(f"{VFS_NAME}> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        result = run_line(line, vfs)

        if result == "exit":
            break

    print("Эмулятор завершён.")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Эмулятор командной оболочки"
    )
    parser.add_argument(
        "--vfs",
        type=str,
        default=None,
        help="Путь к ZIP-архиву виртуальной файловой системы"
    )
    parser.add_argument(
        "--script",
        type=str,
        default=None,
        help="Путь к стартовому скрипту"
    )
    return parser.parse_args()


def load_vfs(archive_path):
    vfs = VirtualFileSystem()

    if archive_path is None:
        return vfs

    if not os.path.isfile(archive_path):
        raise FileNotFoundError(
            f"Файл VFS не найден: {archive_path}"
        )

    vfs.load_zip(archive_path)
    return vfs

def main():
    args = parse_arguments()

    print("=== Параметры запуска ===")
    print(f"Имя VFS: {VFS_NAME}")
    print(f"Путь к VFS: {args.vfs}")
    print(f"Путь к стартовому скрипту: {args.script}")
    print("=========================")

    try:
        vfs = load_vfs(args.vfs)
    except (
        OSError,
        ValueError,
        zipfile.BadZipFile,
        RuntimeError
    ) as error:
        print(f"Ошибка загрузки VFS: {error}")
        return 1

    print(f"Эмулятор оболочки запущен. VFS: {VFS_NAME}")

    if args.script is not None:
        return run_script(args.script, vfs)

    print("Для выхода введите 'exit'.")
    run_interactive(vfs)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())