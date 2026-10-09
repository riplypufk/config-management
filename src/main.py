import os
import shlex
import argparse

VFS_NAME = "user"

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


def command_ls(args):
    if args:
        print(f"ls: неверные аргументы: {' '.join(args)}")
        return "error"
    print("ls")
    return "ok"

def command_cd(args):
    if len(args) > 1:
        print("cd: неверное количество аргументов")
        return "error"

    print("cd", *args)
    return "ok"

def execute_command(command, args):
    if command == "ls":
        return command_ls(args)

    if command == "cd":
        return command_cd(args)

    if command == "exit":
        if args:
            print("exit: неверное количество аргументов")
            return "error"

        return "exit"

    print(f"{command}: неизвестная команда")
    return "error"

def run_line(line, show_input=False):
    if show_input:
        print(f"{VFS_NAME}> {line}")

    command, args, parsed = parse_command(line)

    if not parsed:
        return "error"

    if command is None:
        return "ok"

    return execute_command(command, args)


def run_script(script_path):
    try:
        with open(script_path, "r", encoding="utf-8") as script:
            for line_number, line in enumerate(script, start=1):
                line = line.rstrip("\r\n")

                if not line.strip() or line.lstrip().startswith("#"):
                    continue

                result = run_line(line, show_input=True)

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


def run_interactive():
    while True:
        try:
            line = input(f"{VFS_NAME}> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        result = run_line(line)

        if result == "exit":
            break

    print("Эмулятор завершён.")


def main():
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

    args = parser.parse_args()

    print("=== Параметры запуска ===")
    print(f"Имя VFS: {VFS_NAME}")
    print(f"Путь к VFS: {args.vfs}")
    print(f"Путь к стартовому скрипту: {args.script}")
    print("=========================")

    if args.vfs is not None:
        if not os.path.isfile(args.vfs):
            print(f"Ошибка: файл VFS не найден: {args.vfs}")
            return 1

    print(f"Эмулятор оболочки запущен. VFS: {VFS_NAME}")

    if args.script is not None:
        return run_script(args.script)

    print("Для выхода введите 'exit'.")
    run_interactive()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())