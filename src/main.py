import os
import shlex


VFS_NAME = "user"


def expand_variables(text):
    return os.path.expandvars(text)


def parse_command(line):
    line = expand_variables(line)

    try:
        parts = shlex.split(line)
    except ValueError as error:
        print(f"Ошибка: {error}")
        return None, None

    if not parts:
        return None, None

    return parts[0], parts[1:]


def command_ls(args):
    if args:
        print(f"ls: неверные аргументы: {' '.join(args)}")
        return True

    print("ls")
    return True


def command_cd(args):
    if len(args) > 1:
        print("cd: неверное количество аргументов")
        return True

    print("cd", *args)
    return True


def execute_command(command, args):
    if command == "ls":
        return command_ls(args)

    if command == "cd":
        return command_cd(args)

    if command == "exit":
        if args:
            print("exit: неверное количество аргументов")
            return True

        return False

    print(f"{command}: неизвестная команда")
    return True


def main():
    print(f"Эмулятор оболочки запущен. VFS: {VFS_NAME}")
    print("Для выхода введите 'exit'.")

    while True:
        try:
            line = input(f"{VFS_NAME}> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        command, args = parse_command(line)

        if command is None:
            continue

        result = execute_command(command, args)

        if command == "exit" and result is False:
            break

    print("Эмулятор завершён.")


if __name__ == "__main__":
    main()