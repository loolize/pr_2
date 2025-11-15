import argparse # для чтения аргументов
import os # для работы с путями/папками
import re  # для проверки формата версии
import sys # для кода выхода
from urllib.parse import urlparse  # проверка на юрл
import subprocess # чтобы запускать построчно из .emu

# допустимые значения
SUPPORTED_FORMATS = {"ascii"} # формат вывода аски
SUPPORTED_MODES = {"test", "prod"}  # допустимые режимы. test - , prod - 

# проверка юрл или существующего пути
def is_url_or_path(value: str) -> bool:
    p = urlparse(value)
    if p.scheme and p.netloc:
        return True                  # похоже на юрл
    return os.path.exists(value)     # иначе должен существовать путь

def main():
    # парсер командной строки
    parser = argparse.ArgumentParser(
        description="Этап 1: Минимальный прототип с конфигурацией."
    )
    # параметры, которые можно указать
    parser.add_argument('-n', '--packet_name',    type=str, help="Имя анализируемого пакета.")
    parser.add_argument('-u', '--url_link_repo',  type=str, help="URL-адрес репозитория или путь к файлу тестового репозитория.")
    parser.add_argument('-m', '--repo_work_mode', type=str, help="Режим работы с тестовым репозиторием.")
    parser.add_argument('-v', '--packet_version', type=str, help="Версия пакета.")
    parser.add_argument('-o', '--output_file',    type=str, help="Имя сгенерированного файла с изображением графа.")
    parser.add_argument('-F', '--format',         type=str, help="Режим вывода зависимостей в формате ASCII-дерева.")
    parser.add_argument('-f', '--packet_filter',  type=str, help="Подстрока для фильтрации пакетов.")
    # запуск сценария .emu
    parser.add_argument('--script', type=str, help="Путь к .emu-файлу со сценариями запусков этой программы.")

    args = parser.parse_args()
    
    # если передан --script, читаем .emu и построчно запускаем команды
    if args.script:
        script_path = args.script
        if not os.path.exists(script_path):
            print(f"Файл сценария не найден: {script_path}")
            sys.exit(1)

        with open(script_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                print(f"\n$ {line}")
                # если строка уже начинается с python/python3 — запускаем как есть
                if line.startswith("python ") or line.startswith("python3 "):
                    cmd = line
                else:
                    # иначе считаем, что это только аргументы — подставляем текущий скрипт
                    cmd = f"{sys.executable} {__file__} {line}"
                proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
                if proc.stdout:
                    print(proc.stdout, end="")
                if proc.stderr:
                    print(proc.stderr, end="")
                print(f"[exit-code: {proc.returncode}]")

        sys.exit(0)


    errors = []

    # валидация параметров
    if args.packet_name is None or not args.packet_name.strip():
        errors.append("укажите --packet_name")

    if args.url_link_repo is not None and not is_url_or_path(args.url_link_repo):
        errors.append("--url_link_repo должен быть url или существующим путем")

    if args.repo_work_mode is not None and args.repo_work_mode not in SUPPORTED_MODES:
        errors.append("--repo_work_mode должен быть 'test' или 'prod'")

    if args.packet_version is not None:
        if not re.fullmatch(r"[0-9]+(\.[0-9]+){0,2}", args.packet_version.strip()):
            errors.append("--packet_version должен быть вида 1 или 1.2 или 1.2.3")

    if args.output_file is not None:
        d = os.path.dirname(args.output_file)
        if d and not os.path.isdir(d):
            errors.append("папка для --output_file не существует")

    if args.format is not None and args.format not in SUPPORTED_FORMATS:
        errors.append("--format поддерживает только 'ascii'")

    if args.packet_filter is not None and not args.packet_filter.strip():
        errors.append("--packet_filter не должен быть пустой строкой")

    if errors:
        print("проблемы с параметрами:")
        for i, e in enumerate(errors, 1):
            print(f"{i}) {e}")
        sys.exit(2)

    # вывод параметров ключ=значение
    print("Запуск минимального прототипа (Этап 1)")
    def show(label, value):
        print(f"• {label}: {value if value is not None else '(не задано)'}")

    show("Имя анализируемого пакета", args.packet_name)
    show("URL-адрес репозитория или путь к файлу тестового репозитория", args.url_link_repo)
    show("Режим работы с тестовым репозиторием", args.repo_work_mode)
    show("Версия пакета", args.packet_version)
    show("Имя сгенерированного файла с изображением графа", args.output_file)
    show("Режим вывода зависимостей в формате ASCII-дерева", args.format)
    show("Подстрока для фильтрации пакетов", args.packet_filter)
if __name__ == "__main__":
    main()

