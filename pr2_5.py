import argparse # для чтения аргументов
import os # для работы с путями/папками
import re  # для проверки формата версии
import sys # для кода выхода
from urllib.parse import urlparse  # проверка на юрл
import xml.etree.ElementTree as ET  # для разбора pom.xml
from collections import deque  # очередь для BFS


# допустимые значения
SUPPORTED_FORMATS = {"ascii"} # формат вывода аски
SUPPORTED_MODES = {"test", "prod"}  # допустимые режимы. test prod

# проверка юрл или существующего пути
def is_url_or_path(value: str) -> bool:
    p = urlparse(value)
    if p.scheme and p.netloc: #http и домен
        return True                  # похоже на юрл
    return os.path.exists(value)   # иначе должен существовать путь






# поиск зависимостей
def read_pom(pom_path: str): # в мавен зависимости описаны в пом, открываем пом и достаем список <dependency>
    
    if not os.path.exists(pom_path):  # если файл нет
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







# пострроение графа зависимостей обходом в ширину

def build_dependency_graph_bfs(start_name: str, start_version: str, repo_path: str, packet_filter: str | None = None):
    graph: dict[str, list[str]] = {}
    visited: set[tuple[str, str]] = set() # множество посещенных пакетов

    # двусторонняя очередь для бфс, доб в конец извл из начала
    q = deque()

    # ддоб в пакет корень
    q.append((start_name, start_version))
    visited.add((start_name, start_version))

    while q:
        name, version = q.popleft() # сначала первый эл очереди
        node_key = f"{name}:{version}"

        # если вершинае сть в словаре ничего не меняем
        # для вершин без детей
        graph.setdefault(node_key, [])

        # путь к пом
        pom_path = os.path.join(repo_path, name, version, "pom.xml")
        deps = read_pom(pom_path)

        if deps is None: # если пом не найден 
            continue

        for dep in deps:
            dep_name = dep["artifactId"]
            dep_version = dep["version"]

            if not dep_name:# зависимость без имени
                continue

            # фильтр по подстроке
            if packet_filter and packet_filter in dep_name:
                continue

            # строка для соседа
            neighbor_key = f"{dep_name}:{dep_version}" if dep_version else dep_name
            graph[node_key].append(neighbor_key)

            state = (dep_name, dep_version)
            # защита от циклов
            if state not in visited:
                visited.add(state)
                if dep_version:
                    q.append(state)

    return graph


# порядок загрузки зависимостей
def compute_load_order(
    start_name: str,
    start_version: str,
    repo_path: str,
    packet_filter: str | None = None
) -> list[str]:


    visited: set[tuple[str, str]] = set()  # уже обработанные пакеты
    temp_mark: set[tuple[str, str]] = set()    # для циклов
    order: list[str] = [] 

    def dfs(name: str, version: str | None):
        state = (name, version) # вершина

        # обнаружение цикла
        if state in temp_mark:
            return

        # уже обработан
        if state in visited:
            return

        temp_mark.add(state)

        # путь к пом текущего пакета
        if version:
            pom_path = os.path.join(repo_path, name, version, "pom.xml")
        else:
            pom_path = ""

        deps = read_pom(pom_path) if pom_path and os.path.exists(pom_path) else None

        # если pom не найден, просто добавляем пакет в порядок (как "лист")
        if deps is not None:
            for dep in deps:
                dep_name = dep["artifactId"]
                dep_version = dep["version"]

                # фильтр по подстроке
                if packet_filter and packet_filter in dep_name:
                    continue

                # рекурсивный обход
                dfs(dep_name, dep_version if dep_version else None)

        temp_mark.remove(state)
        visited.add(state)

        # добавляем тек пакет в конец после всех завис
        if version:
            order.append(f"{name}:{version}")
        else:
            order.append(name)

    # старт с корневого пакета
    dfs(start_name, start_version)

    return order










# вывод графа в текстовом виде
def print_graph_ascii(graph: dict[str, list[str]]):
    print("\nграф зависимостей:")
    if not graph:
        print("граф пуст")
        return

    for node, neighbors in graph.items():
        deps_str = ", ".join(neighbors) if neighbors else ""
        print(f"{node} - {deps_str}")



# NEW
# формирование текстового представления графа на языке PlantUML
def graph_to_plantuml(graph: dict[str, list[str]]) -> str: # аргумент ключ зависимости
    lines: list[str] = ["@startuml"]

    edges: set[tuple[str, str]] = set() # ребра множестов пар строк
    nodes: set[str] = set() # вергины

    for node, neighbors in graph.items():
        nodes.add(node)
        for n in neighbors: # перебор соседец тек узла
            nodes.add(n)
            edges.add((node, n))

    # вершины без рёбер
    for node in sorted(nodes):
        lines.append(f'"{node}"')

    # рёбра
    for src, dst in sorted(edges): # узел источник узел приемник
        lines.append(f'"{src}" -> "{dst}"')

    lines.append("@enduml")
    return "\n".join(lines)




from collections import defaultdict # пустой список для несуществ ключей

# NEW — SVG с раскладкой по уровням (как GraphViz)
def save_graph_as_svg(graph: dict[str, list[str]], svg_path: str, root: str): # узел - дети, путь к файлу, корень

    level: dict[str, int] = {root: 0} # узел - номер уровня
    q: deque[str] = deque([root]) # очередь в шиирну

    while q:
        node = q.popleft()
        for n in graph.get(node, []): # дети тек
            if n not in level:
                level[n] = level[node] + 1
                q.append(n)

    levels: dict[int, list[str]] = defaultdict(list) # номер - список узлов
    for node, lvl in level.items():
        levels[lvl].append(node)

    node_width = 220 # ширина блока
    node_height = 40 # высота
    margin = 40 # отступ
    horiz_gap = 40  # расстояние между узлами по горизонтали
    vert_gap = 80    # расстояние между уровнями по вертикали

    max_nodes_in_level = max(len(nodes) for nodes in levels.values()) # макс колво узлов на одном уровне
    svg_width = max_nodes_in_level * node_width + (max_nodes_in_level - 1) * horiz_gap + margin * 2 # общ ширина
    num_levels = len(levels)
    svg_height = num_levels * node_height + (num_levels - 1) * vert_gap + margin * 2 # сумм высота

    svg_lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">'
    ]

    # для узла: левый верхний угол по x y и центр для стрелок
    positions: dict[str, tuple[float, float, float]] = {}  # node -> (x, y, x_center)

    for lvl in sorted(levels.keys()):
        nodes_on_level = levels[lvl] # узлов на уровне
        n = len(nodes_on_level)

        # ширина для всех на уровне
        row_width = n * node_width + (n - 1) * horiz_gap
        
        start_x = (svg_width - row_width) / 2

        y = margin + lvl * (node_height + vert_gap)

        for i, node in enumerate(nodes_on_level):
            x = start_x + i * (node_width + horiz_gap)

            # прямоугольник
            svg_lines.append(
                f'<rect x="{x}" y="{y}" width="{node_width}" height="{node_height}" '
                f'style="fill:#9C8B72;stroke:#5B7187;stroke-width:2"/>'
            )

            # текст
            text = (
                node.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
            )
            svg_lines.append(
                f'<text x="{x + 10}" y="{y + 25}" font-size="14" '
                f'style="font-family: monospace">{text}</text>'
            )

            x_center = x + node_width / 2
            positions[node] = (x, y, x_center)

    # стрелкт
    for src, neighbors in graph.items():
        if src not in positions:
            continue
        _, y_src, x_center_src = positions[src]
        y_src_bottom = y_src + node_height

        for dst in neighbors:
            if dst not in positions:
                continue
            _, y_dst, x_center_dst = positions[dst]
            y_dst_top = y_dst

            # линия от нижней границы src к верхней dst
            svg_lines.append(
                f'<line x1="{x_center_src}" y1="{y_src_bottom}" '
                f'x2="{x_center_dst}" y2="{y_dst_top}" '
                f'style="stroke:#5B7187;stroke-width:2"/>'
            )

            # маленький треугольник-стрелка возле dst
            arrow_y = y_dst_top
            arrow_size = 5
            svg_lines.append(
                f'<polygon points="'
                f'{x_center_dst - arrow_size},{arrow_y - arrow_size} '
                f'{x_center_dst + arrow_size},{arrow_y - arrow_size} '
                f'{x_center_dst},{arrow_y}'
                f'" style="fill:#5B7187"/>'
            )

    svg_lines.append("</svg>")

    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_lines))



# NEW
# вывод графа в виде аски 
def print_ascii_tree(graph: dict[str, list[str]], root: str): # пакет:версия корень
    visited: set[str] = set() # уже запис

    def _print(node: str, prefix: str, is_last: bool):
        # строка для текущего узла
        if prefix == "":
            line = node
        else:
            connector = "└─ " if is_last else "├─ " # последний нет ребенок
            line = prefix + connector + node
        print(line)

        if node in visited:
            return
        visited.add(node)

        children = graph.get(node, []) # дети тек
        for i, child in enumerate(children):
            last_child = (i == len(children) - 1)
            child_prefix = prefix + ("   " if is_last else "│  ")
            _print(child, child_prefix, last_child)

    print("\nзависимости в виде ASCII-дерева:")
    _print(root, "", True)


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

    parser.add_argument(
        "--show_direct_deps",
        action="store_true", # есои пользователь указал
        help="Вывести прямые зависимости пакета."
    )

    parser.add_argument(
        "--build_graph",
        action="store_true",
        help="Вывести граф зависимости."
    )


    parser.add_argument(
        "--load_order",
        action="store_true",
        help="Показать порядок загрузки зависимостей для пакета."
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


    if args.show_direct_deps: # если есть запрос
        if args.url_link_repo is None: # нет пути
            print("для --show_direct_deps требуется параметр --url_link_repo для нахождения pom.xml")
            sys.exit(2)
        show_direct_dependens(
            args.url_link_repo,
            args.packet_name,
            args.packet_version
        )



    # построение графа зависимостей
    if args.build_graph:
        if args.url_link_repo is None:
            print("для --build_graph требуется параметр --url_link_repo")
            sys.exit(2)

        graph = build_dependency_graph_bfs(
            start_name=args.packet_name,
            start_version=args.packet_version,
            repo_path=args.url_link_repo,
            packet_filter=args.packet_filter
        )

        plantuml_text = graph_to_plantuml(graph)

        if args.output_file:
            base, _ = os.path.splitext(args.output_file)
            puml_path = base + ".puml"

            try:
                with open(puml_path, "w", encoding="utf-8") as f:
                    f.write(plantuml_text)
            except OSError as e:
                print(f"ошибка записи PlantUML-файла: {e}")

            root_key = f"{args.packet_name}:{args.packet_version}"

            # свг
            try:
                save_graph_as_svg(graph, args.output_file, root_key)
            except OSError as e:
                print(f"ошибка записи SVG-файла: {e}")


        # дерево или списко
        if args.format == "ascii":
            # корень: имя:версия
            root_key = f"{args.packet_name}:{args.packet_version}"
            print_ascii_tree(graph, root_key)
        else:
            print_graph_ascii(graph)


    # вывод порядка загрузки зависимостей
    if args.load_order:
        if args.url_link_repo is None:
            print("для --load_order требуется параметр --url_link_repo")
            sys.exit(2)

        load_order = compute_load_order(
            start_name=args.packet_name,
            start_version=args.packet_version,
            repo_path=args.url_link_repo,
            packet_filter=args.packet_filter
        )

        print("\nпорядок загрузки зависимостей:")
        if not load_order:
            print("зависимости не найдены")
        else:
            for i in load_order:
                print(i)


    # вывод параметров
    # print("параметры, настраиваемые пользователем (ключ-значение):")
    # for key in ["packet_name", "url_link_repo", "repo_work_mode", "packet_version",
    #                                         "output_file", "format", "packet_filter"]:
    #     value = getattr(args, key)  # значение параметра по имени поля
    #     if value is None:  # если не задавали параметр
    #         value_str = ""
    #     else:
    #         value_str = str(value)
    #     print(f"{key} - {value_str}")

if __name__ == "__main__":
    main()

