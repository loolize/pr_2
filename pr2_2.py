import argparse # для чтения аргументов
import os # для работы с путями/папками
import re  # для проверки формата версии
import sys # для кода выхода
from urllib.parse import urlparse  # проверка на юрл
import xml.etree.ElementTree as ET  # для разбора pom.xml

# допустимые значения
SUPPORTED_FORMATS = {"ascii"} # формат вывода аски
SUPPORTED_MODES = {"test", "prod"}  # допустимые режимы. test prod

# проверка юрл или существующего пути
def is_url_or_path(value: str) -> bool:
    p = urlparse(value)
    if p.scheme and p.netloc: #http и домен
        return True                  # похоже на юрл
    return os.path.exists(value)   # иначе должен существовать путь













#NEW
# поиск зависимостей
def read_pom(pom_path: str): # в мавен зависимости описаны в пом, открываем пом и достаем список <dependency>
    
    if not os.path.exists(pom_path):  # если файл нет
        print(f"файл pom не найден: {pom_path}")
        return None

    tree = ET.parse(pom_path) # разобрать пом в дерева элементов
    root = tree.getroot()  # корневой
    

    # пространство имён Maven
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}

    deps = []  # зависимости

    # ищем раздел <dependencies>
    for dep in root.findall("m:dependencies/m:dependency", ns):
        # достаём значения полей dependency
        group_id = dep.find("m:groupId", ns) # дочерний элемент
        artifact_id = dep.find("m:artifactId", ns) # имя папки с пом
        version = dep.find("m:version", ns) # папка версии

        # приводим к строкам (или пустой строке если нет)
        deps.append({
            "groupId": group_id.text if group_id is not None else "",
            "artifactId": artifact_id.text if artifact_id is not None else "",
            "version": version.text if version is not None else ""
        })

    return deps  # возвращаем список зависимостей

#NEW
# поиск прямых завис
def show_direct_dependens(path: str, name: str, version: str):
    # конструируем путь к пом
    pom_path = os.path.join( 
        path,
        name,
        version,
        "pom.xml"
    )
    deps = read_pom(pom_path)  # результат чтения пом

    if deps is None:  # списка нет
        print("невозможно загрузить зависимости")
        return


    print("\nпрямые зависимости пакета:")

    # вывод зависимостей
    for i in deps:
        print(f"- {i['groupId']}:{i['artifactId']}:{i['version']}")













def main():
    # парсер командной строки
    parser = argparse.ArgumentParser()
    # параметры, которые можно указать
    parser.add_argument(
        '-n', 
        '--packet_name',    
        type=str, 
        help="Имя анализируемого пакета."
    )

    parser.add_argument(
        '-u', 
        '--url_link_repo',  
        type=str, 
        help="URL-адрес репозитория или путь к файлу тестового репозитория."
    )

    parser.add_argument(
        '-m', 
        '--repo_work_mode', 
        type=str, 
        help="Режим работы с тестовым репозиторием."
    )

    parser.add_argument(
        '-v', 
        '--packet_version', 
        type=str, 
        help="Версия пакета."
    )

    parser.add_argument(
        '-o', 
        '--output_file',    
        type=str, 
        help="Имя сгенерированного файла с изображением графа."
    )

    parser.add_argument(
        '-F', 
        '--format',         
        type=str, 
        help="Режим вывода зависимостей в формате ASCII-дерева."
    )

    parser.add_argument(
        '-f', 
        '--packet_filter',  
        type=str, 
        help="Подстрока для фильтрации пакетов."
    )

    #NEW
    parser.add_argument(
        "--show_direct_deps",
        action="store_true", # есои пользователь указал
        help="Вывести прямые зависимости пакета."
)



    args = parser.parse_args() # арг строки в объект
    
    errors = [] # сюда текст найденных пробллек


    # проверка 
    # если имя не указано или там пустая строка
    if args.packet_name is None or not args.packet_name.strip():
        errors.append("укажите --packet_name")

    # если адрес указан и не сущесвтут 
    if args.url_link_repo is not None and not is_url_or_path(args.url_link_repo):
        errors.append("--url_link_repo должен быть url или существующим путем")

    # режим работы указан и не из списка допустимых
    if args.repo_work_mode is not None and args.repo_work_mode not in SUPPORTED_MODES:
        errors.append("--repo_work_mode должен быть 'test' или 'prod'")


    # версия пакета не указана или там пусто
    if args.packet_version is None or not args.packet_version.strip():
        errors.append("--packet_version не должна быть пустой")

    # путь к вых файлц существует
    if args.output_file is not None:
        d = os.path.dirname(args.output_file) # директория из пути
        if d and not os.path.isdir(d):
            errors.append("папка для --output_file не существует")

    # формат вывода не пуст и не в списке допустимых
    if args.format is not None and args.format not in SUPPORTED_FORMATS:
        errors.append("--format поддерживает только 'ascii'")

    # фильтр пакетов указан но пустой
    if args.packet_filter is not None and not args.packet_filter.strip():
        errors.append("--packet_filter не должен быть пустой строкой")


    if errors:
        print("проблемы с параметрами:")
        for i, k in enumerate(errors, 1): # перебираем все ошибкис с номером
            print(f"{k}")
        sys.exit(2)


    #NEW
    if args.show_direct_deps: # если есть запрос
        if args.url_link_repo is None: # нет пути
            print("для --show_direct_deps требуется параметр --url_link_repo для нахождения pom.xml")
            sys.exit(2)
        show_direct_dependens(
            args.url_link_repo,
            args.packet_name,
            args.packet_version
        )

    # вывод параметров
    print("параметры, настраиваемые пользователем (ключ-значение):")
    for key in ["packet_name", "url_link_repo", "repo_work_mode", "packet_version",
                                            "output_file", "format", "packet_filter"]:
        value = getattr(args, key)  # значение параметра по имени поля
        if value is None:  # если не задавали параметр
            value_str = ""
        else:
            value_str = str(value)
        print(f"{key} - {value_str}")

if __name__ == "__main__":
    main()

