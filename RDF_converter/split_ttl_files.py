import os
import math
from pathlib import Path

def split_large_ttl_files(input_dir, output_dir, max_size_kb=1000):
    """
    Разделяет TTL файлы на части не более max_size_kB
    
    Args:
        input_dir: Папка с исходными TTL файлами
        output_dir: Папка для разделенных файлов
        max_size_kb: Максимальный размер файла в КБ (по умолчанию 1000)
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    max_size_bytes = max_size_kb * 1024  # 1000 КБ в байтах
    
    # Список TTL файлов для обработки
    ttl_files = list(input_dir.glob("*.ttl"))
    
    print(f"Найдено {len(ttl_files)} TTL файлов в {input_dir}")
    
    for ttl_file in ttl_files:
        file_size = ttl_file.stat().st_size
        print(f"\nОбработка файла: {ttl_file.name} ({file_size / 1024:.1f} КБ)")
        
        # Если файл достаточно мал, просто копируем его
        if file_size <= max_size_bytes:
            destination = output_dir / ttl_file.name
            with open(ttl_file, 'r', encoding='utf-8') as src:
                content = src.read()
            with open(destination, 'w', encoding='utf-8') as dst:
                dst.write(content)
            print(f"  ✓ Файл скопирован как есть")
            continue
        
        # Разделяем большой файл
        print(f"  Разделение на части...")
        split_ttl_file(ttl_file, output_dir, max_size_bytes)
    
    print(f"\n✓ Все файлы обработаны и сохранены в {output_dir}")

def split_ttl_file(ttl_file, output_dir, max_size_bytes):
    """
    Разделяет один TTL файл на несколько частей
    """
    with open(ttl_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Находим секцию префиксов (она должна быть в начале каждого файла)
    prefixes = []
    data_lines = []
    in_prefix_section = True
    
    for line in lines:
        if in_prefix_section:
            prefixes.append(line)
            # Проверяем, закончилась ли секция префиксов
            if line.strip() == "" or line.startswith("#") or line.strip().endswith("."):
                # Пустая строка, комментарий или первая триплета - префиксы закончились
                if line.strip().endswith(".") and not line.startswith("@prefix"):
                    in_prefix_section = False
                    if line.strip().endswith("."):
                        data_lines.append(line)
        else:
            data_lines.append(line)
    
    # Удаляем пустые строки из конца префиксов
    while prefixes and prefixes[-1].strip() == "":
        prefixes.pop()
    
    # Определяем, сколько частей нам понадобится
    prefix_size = sum(len(p.encode('utf-8')) for p in prefixes)
    data_size = sum(len(l.encode('utf-8')) for l in data_lines)
    
    # Оцениваем необходимое количество частей
    estimated_parts = math.ceil((prefix_size + data_size) / max_size_bytes)
    
    # Разделяем data_lines на части
    parts = []
    current_part = []
    current_size = prefix_size
    
    for line in data_lines:
        line_size = len(line.encode('utf-8'))
        
        # Если добавление строки превысит лимит, начинаем новую часть
        if current_size + line_size > max_size_bytes and current_part:
            parts.append(current_part)
            current_part = [line]
            current_size = prefix_size + line_size
        else:
            current_part.append(line)
            current_size += line_size
    
    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part)
    
    # Если мы оценили неправильно и получили больше частей, чем ожидали,
    # мы все равно сохраняем то, что получилось
    actual_parts = len(parts)
    
    print(f"  Файл разделен на {actual_parts} частей")
    
    # Сохраняем каждую часть
    for i, part_lines in enumerate(parts, 1):
        part_filename = output_dir / f"{ttl_file.stem}_part{i}.ttl"
        
        with open(part_filename, 'w', encoding='utf-8') as f:
            # Записываем префиксы
            f.writelines(prefixes)
            f.write("\n")
            # Записываем данные
            f.writelines(part_lines)
        
        part_size = part_filename.stat().st_size
        print(f"  Часть {i}: {part_filename.name} ({part_size / 1024:.1f} КБ)")

def validate_split_files(output_dir):
    """
    Проверяет корректность разделенных файлов
    """
    print(f"\nПроверка корректности файлов в {output_dir}...")
    
    output_dir = Path(output_dir)
    split_files = list(output_dir.glob("*_part*.ttl"))
    
    for file in split_files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем основные синтаксические элементы
        has_prefix = "@prefix" in content or "PREFIX" in content
        has_triples = " .\n" in content or " ;\n" in content
        ends_properly = content.strip().endswith(".") or content.strip().endswith("}")
        
        if not has_prefix:
            print(f"  ⚠️  {file.name}: Возможно отсутствуют префиксы")
        elif not has_triples:
            print(f"  ⚠️  {file.name}: Нет триплетов (возможно пустой файл)")
        elif not ends_properly:
            print(f"  ⚠️  {file.name}: Не заканчивается точкой или фигурной скобкой")
        else:
            file_size = file.stat().st_size / 1024
            print(f"  ✓ {file.name}: OK ({file_size:.1f} КБ)")

def create_loading_script(output_dir):
    """
    Создает скрипт для загрузки всех частей в GraphDB
    """
    script_content = """#!/bin/bash
# Скрипт для загрузки разделенных TTL файлов в GraphDB
# Использование: ./load_to_graphdb.sh

GRAPHDB_URL="http://localhost:7200"
REPOSITORY="your-repository-name"

echo "Загрузка файлов в GraphDB..."

# Файлы без частей (обычные файлы)
for file in *.ttl; do
    if [[ $file != *_part*.ttl ]]; then
        echo "Загрузка $file..."
        curl -X POST -H "Content-Type: application/x-turtle" \\
             --data-binary "@$file" \\
             "$GRAPHDB_URL/repositories/$REPOSITORY/statements"
    fi
done

# Файлы с частями (загружаем в правильном порядке)
for part in 1 2 3 4 5 6 7 8 9 10; do
    for file in *_part${part}.ttl; do
        if [ -f "$file" ]; then
            echo "Загрузка $file (часть $part)..."
            curl -X POST -H "Content-Type: application/x-turtle" \\
                 --data-binary "@$file" \\
                 "$GRAPHDB_URL/repositories/$REPOSITORY/statements"
        fi
    done
done

echo "Загрузка завершена!"
"""
    
    script_path = Path(output_dir) / "load_to_graphdb.sh"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Делаем скрипт исполняемым (Unix/Linux)
    if os.name != 'nt':  # не Windows
        os.chmod(script_path, 0o755)
    
    print(f"✓ Создан скрипт загрузки: {script_path}")

def split_with_rdf_parsing(input_dir, output_dir, max_size_kb=1000):
    """
    Альтернативная версия с использованием RDFlib для точного разделения
    (требует установки rdflib)
    """
    try:
        from rdflib import Graph
        from rdflib.util import guess_format
    except ImportError:
        print("RDFlib не установлен. Установите: pip install rdflib")
        return
    
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    max_size_bytes = max_size_kb * 1024
    
    ttl_files = list(input_dir.glob("*.ttl"))
    
    print(f"Разделение файлов с использованием RDFlib...")
    
    for ttl_file in ttl_files:
        file_size = ttl_file.stat().st_size
        
        if file_size <= max_size_bytes:
            # Копируем маленькие файлы как есть
            destination = output_dir / ttl_file.name
            with open(ttl_file, 'r', encoding='utf-8') as src:
                content = src.read()
            with open(destination, 'w', encoding='utf-8') as dst:
                dst.write(content)
            continue
        
        print(f"Обработка {ttl_file.name}...")
        
        # Загружаем граф
        g = Graph()
        g.parse(str(ttl_file), format=guess_format(str(ttl_file)))
        
        # Получаем все триплы
        triples = list(g)
        
        if not triples:
            print(f"  ⚠️  Файл пуст или не содержит триплов")
            continue
        
        # Разделяем триплы на части
        triples_per_part = len(triples) // (file_size // max_size_bytes + 1)
        parts = []
        
        for i in range(0, len(triples), triples_per_part):
            part_triples = triples[i:i + triples_per_part]
            part_graph = Graph()
            
            # Копируем namespace из исходного графа
            for prefix, namespace in g.namespaces():
                part_graph.bind(prefix, namespace)
            
            # Добавляем триплы
            for triple in part_triples:
                part_graph.add(triple)
            
            parts.append(part_graph)
        
        # Сохраняем части
        for i, part_graph in enumerate(parts, 1):
            part_filename = output_dir / f"{ttl_file.stem}_part{i}.ttl"
            part_graph.serialize(destination=str(part_filename), format='turtle')
            
            part_size = part_filename.stat().st_size
            print(f"  Часть {i}: {part_filename.name} ({len(list(part_graph))} триплов, {part_size/1024:.1f} КБ)")

def main():
    """
    Основная функция
    """
    # Конфигурация
    INPUT_DIR = "output"  # Папка с TTL файлами из предыдущего скрипта
    OUTPUT_DIR = "output_split"  # Папка для разделенных файлов
    MAX_SIZE_KB = 500  # Максимальный размер файла в КБ
    
    print("=" * 60)
    print("Разделение TTL файлов на части до 1000 КБ")
    print("=" * 60)
    
    # Вариант 1: Простое разделение по размеру (быстрее)
    # print("\n[Вариант 1] Простое разделение по размеру файла...")
    # split_large_ttl_files(INPUT_DIR, OUTPUT_DIR, MAX_SIZE_KB)
    
    # Вариант 2: Точное разделение с использованием RDFlib (медленнее, но точнее)
    print("\n[Вариант 2] Точное разделение с использованием RDFlib...")
    split_with_rdf_parsing(INPUT_DIR, OUTPUT_DIR, MAX_SIZE_KB)
    
    # Проверяем корректность
    validate_split_files(OUTPUT_DIR)
    
    # Создаем скрипт для загрузки
    create_loading_script(OUTPUT_DIR)
    
    # Выводим инструкции
    print("\n" + "=" * 60)
    print("ИНСТРУКЦИЯ ПО ЗАГРУЗКЕ В GraphDB:")
    print("=" * 60)
    print("1. Все файлы сохранены в папке:", OUTPUT_DIR)
    print("2. Для загрузки выполните команды:")
    print("   cd", OUTPUT_DIR)
    print("   # Настройте URL и имя репозитория в load_to_graphdb.sh")
    print("   ./load_to_graphdb.sh")
    print("\n3. Или загрузите файлы вручную через интерфейс GraphDB:")
    print("   - Откройте GraphDB Workbench")
    print("   - Выберите репозиторий")
    print("   - Import → RDF files")
    print("   - Загружайте файлы в порядке: сначала основные, затем части по порядку")
    print("=" * 60)

if __name__ == "__main__":
    main()
