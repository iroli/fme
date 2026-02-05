import os
import re
import xml.etree.ElementTree as ET
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD
import uuid
import hashlib
from tqdm.auto import tqdm

# Настройка пространств имен RDF
FME = Namespace("http://libmeta.ru/fme/")
PERSON_NS = Namespace("http://libmeta.ru/person/")
PUBLICATION_NS = Namespace("http://libmeta.ru/publication/")
FORMULA_NS = Namespace("http://libmeta.ru/fme/formula/")
SOURCE_NS = Namespace("http://libmeta.ru/source/")
ARTICLE_NS = Namespace("http://libmeta.ru/article/")
TERM_NS = Namespace("http://libmeta.ru/term/")

# Определение собственных классов и свойств
class_ns = Namespace("http://libmeta.ru/ontology/")
Article_Ru = class_ns.Article_Ru
Person = class_ns.Person
Publication = class_ns.Publication
Formula = class_ns.Formula
Source = class_ns.Source
Term = class_ns.Term

# Свойства
has_title = class_ns.has_title
has_author = class_ns.has_author
has_start_page = class_ns.has_start_page
has_end_page = class_ns.has_end_page
has_year = class_ns.has_year
has_publication_info = class_ns.has_publication_info
has_formula_text = class_ns.has_formula_text
has_other_info = class_ns.has_other_info
has_name = class_ns.has_name
relevant_article = class_ns.relevant_article
refers_to = class_ns.refers_to
used_in_text = class_ns.used_in_text
taken_from = class_ns.taken_from
contained_in = class_ns.contained_in
has_relation_text = class_ns.has_relation_text
has_original_uri = class_ns.has_original_uri
has_source = class_ns.has_source

def normalize_term_name(name):
    """Нормализация имени термина для URI"""
    # Удаляем лишние пробелы, приводим к нижнему регистру
    # и заменяем пробелы на подчеркивания
    if not name:
        return "untitled"
    
    # Удаляем специальные символы, оставляем только буквы, цифры и пробелы
    normalized = re.sub(r'[^\w\s]', '', name, flags=re.UNICODE)
    # Заменяем пробелы на подчеркивания и приводим к нижнему регистру
    normalized = normalized.strip().lower().replace(' ', '_')
    # Если после нормализации строка пустая, создаем хэш
    if not normalized:
        normalized = hashlib.md5(name.encode()).hexdigest()[:10]
    
    return normalized

def generate_article_uri(title, source_name):
    """Генерация уникального URI для статьи"""
    # Нормализуем название
    norm_title = normalize_term_name(title)
    # Создаем уникальный идентификатор
    unique_id = str(uuid.uuid4())[:8]
    
    # Создаем URI с учетом источника
    uri = f"{ARTICLE_NS}{source_name}/{norm_title}_{unique_id}"
    return URIRef(uri)

def generate_term_uri(term_name):
    """Генерация URI для термина"""
    norm_name = normalize_term_name(term_name)
    return URIRef(f"{TERM_NS}{norm_name}")

def extract_uri_from_brackets(text):
    """Извлечение URI из формата URI[[...]]/URI"""
    if not text:
        return []
    uris = re.findall(r'URI\[\[(.*?)\]\]/URI', text)
    return uris

def process_article_xml(xml_path, graph, source_uri, source_name):
    """Обработка одного XML файла статьи"""
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Оригинальный URI статьи
    original_uri = root.get('uri')
    
    # Название статьи
    title = root.find('title').text
    if not title:
        title = "Без названия"
    
    # Генерация нового URI для статьи
    article_uri = generate_article_uri(title, source_name)
    
    # Проверяем, не обрабатывали ли мы уже эту статью
    # (по оригинальному URI)
    existing_articles = list(graph.subjects(has_original_uri, URIRef(original_uri)))
    if existing_articles:
        # Статья уже существует, возвращаем её URI
        return graph, existing_articles[0]
    
    # Тип статьи
    graph.add((article_uri, RDF.type, Article_Ru))
    
    # Сохраняем оригинальный URI
    graph.add((article_uri, has_original_uri, URIRef(original_uri)))
    
    # Название статьи
    graph.add((article_uri, has_title, Literal(title)))
    
    # Термин (может быть связан с несколькими статьями)
    term_uri = generate_term_uri(title)
    graph.add((term_uri, RDF.type, Term))
    graph.add((term_uri, has_title, Literal(title)))
    graph.add((term_uri, contained_in, article_uri))
    
    # Авторы статьи
    authors_elem = root.find('authors')
    if authors_elem is not None:
        for author_elem in authors_elem.findall('author'):
            author_name = author_elem.text.strip()
            # Создаем уникальный идентификатор для автора
            author_id = hashlib.md5(author_name.encode()).hexdigest()[:10]
            author_uri = URIRef(f"{PERSON_NS}{author_id}")
            
            graph.add((author_uri, RDF.type, Person))
            graph.add((author_uri, has_name, Literal(author_name)))
            graph.add((article_uri, has_author, author_uri))
    
    # Страницы
    pages_elem = root.find('pages')
    if pages_elem is not None:
        start_page = pages_elem.find('start')
        end_page = pages_elem.find('end')
        
        if start_page is not None and start_page.text:
            graph.add((article_uri, has_start_page, Literal(start_page.text, datatype=XSD.integer)))
        if end_page is not None and end_page.text:
            graph.add((article_uri, has_end_page, Literal(end_page.text, datatype=XSD.integer)))
    
    # Литература (публикации)
    literature_elem = root.find('literature')
    if literature_elem is not None:
        # Обработка литературных источников
        for unit_elem in literature_elem.findall('unit'):
            # Генерация URI для публикации
            author_elem = unit_elem.find('author')
            title_elem = unit_elem.find('title')
            year_elem = unit_elem.find('year')
            
            if author_elem is not None and title_elem is not None:
                # Создаем уникальный ID для публикации
                pub_data = f"{author_elem.text}_{title_elem.text}"
                if year_elem is not None and year_elem.text:
                    pub_data += f"_{year_elem.text}"
                
                pub_id = hashlib.md5(pub_data.encode()).hexdigest()[:12]
                publication_uri = URIRef(f"{PUBLICATION_NS}{pub_id}")
                
                # Проверяем, существует ли уже эта публикация
                existing_pubs = list(graph.subjects(RDF.type, Publication))
                existing_titles = [str(graph.value(pub, has_title)) for pub in existing_pubs]
                
                if str(title_elem.text) not in existing_titles:
                    graph.add((publication_uri, RDF.type, Publication))
                    
                    # Автор публикации
                    if author_elem.text:
                        pub_author_name = author_elem.text.strip()
                        pub_author_id = hashlib.md5(pub_author_name.encode()).hexdigest()[:10]
                        pub_author_uri = URIRef(f"{PERSON_NS}{pub_author_id}")
                        
                        # Добавляем автора, если его еще нет
                        existing_authors = list(graph.subjects(has_name, Literal(pub_author_name)))
                        if not existing_authors:
                            graph.add((pub_author_uri, RDF.type, Person))
                            graph.add((pub_author_uri, has_name, Literal(pub_author_name)))
                        
                        graph.add((publication_uri, has_author, pub_author_uri))
                    
                    # Название публикации
                    if title_elem.text:
                        graph.add((publication_uri, has_title, Literal(title_elem.text)))
                    
                    # Информация о публикации
                    pub_info_elem = unit_elem.find('publication')
                    if pub_info_elem is not None and pub_info_elem.text:
                        graph.add((publication_uri, has_publication_info, Literal(pub_info_elem.text)))
                    
                    # Год
                    if year_elem is not None and year_elem.text:
                        graph.add((publication_uri, has_year, Literal(year_elem.text, datatype=XSD.integer)))
                    
                    # Другая информация
                    other_elem = unit_elem.find('other')
                    if other_elem is not None and other_elem.text:
                        graph.add((publication_uri, has_other_info, Literal(other_elem.text)))
                
                # Связь статьи с публикацией
                graph.add((article_uri, refers_to, publication_uri))
    
    # Основные формулы
    formulas_main_elem = root.find('formulas_main')
    if formulas_main_elem is not None:
        for formula_elem in formulas_main_elem.findall('formula'):
            formula_text = formula_elem.text
            if formula_text:
                # Создаем URI для формулы на основе её текста
                formula_id = hashlib.md5(formula_text.encode()).hexdigest()[:12]
                formula_uri = URIRef(f"{FORMULA_NS}{formula_id}")
                
                # Проверяем, существует ли уже такая формула
                existing_formulas = list(graph.subjects(has_formula_text, Literal(formula_text)))
                if not existing_formulas:
                    graph.add((formula_uri, RDF.type, Formula))
                    graph.add((formula_uri, has_formula_text, Literal(formula_text)))
                
                graph.add((article_uri, used_in_text, formula_uri))
    
    # Вспомогательные формулы - ЗАКОММЕНТИРОВАНО
    # formulas_aux_elem = root.find('formulas_aux')
    # if formulas_aux_elem is not None:
    #     for formula_elem in formulas_aux_elem.findall('formula'):
    #         formula_uri = URIRef(formula_elem.get('uri'))
    #         graph.add((formula_uri, RDF.type, Formula))
    #         
    #         if formula_elem.text:
    #             graph.add((formula_uri, has_formula_text, Literal(formula_elem.text)))
    #         
    #         graph.add((article_uri, used_in_text, formula_uri))
    
    # Связи с другими статьями
    relations_elem = root.find('relations')
    if relations_elem is not None:
        for relation_elem in relations_elem.findall('relation'):
            rel_text_elem = relation_elem.find('rel_text')
            target_elem = relation_elem.find('target')
            
            if target_elem is not None and target_elem.text:
                target_original_uri = target_elem.text
                
                # Ищем, есть ли уже статья с таким оригинальным URI
                existing_targets = list(graph.subjects(has_original_uri, URIRef(target_original_uri)))
                
                if existing_targets:
                    # Статья уже есть, используем её URI
                    target_uri = existing_targets[0]
                else:
                    # Создаем временный URI для будущей статьи
                    # (будет заменен при обработке той статьи)
                    target_id = hashlib.md5(target_original_uri.encode()).hexdigest()[:12]
                    target_uri = URIRef(f"{ARTICLE_NS}temporary_{target_id}")
                    graph.add((target_uri, RDF.type, Article_Ru))
                    graph.add((target_uri, has_original_uri, URIRef(target_original_uri)))
                
                # Добавляем связь
                graph.add((article_uri, relevant_article, target_uri))
                
                # Текст связи
                if rel_text_elem is not None and rel_text_elem.text:
                    graph.add((article_uri, has_relation_text, Literal(rel_text_elem.text)))
    
    # Текст статьи с извлечением URI
    text_elem = root.find('text')
    if text_elem is not None and text_elem.text:
        # Извлекаем все URI из текста
        uris_in_text = extract_uri_from_brackets(text_elem.text)
        
        for uri in uris_in_text:
            uri_ref = URIRef(uri)
            
            # Определяем тип URI
            if 'formula' in uri:
                # Для формул создаем объект Formula
                graph.add((uri_ref, RDF.type, Formula))
                graph.add((article_uri, used_in_text, uri_ref))
            elif 'article' in uri:
                # Для статей ищем или создаем Article_Ru
                existing_articles = list(graph.subjects(has_original_uri, uri_ref))
                if existing_articles:
                    target_article = existing_articles[0]
                else:
                    # Создаем временную статью
                    target_id = hashlib.md5(str(uri_ref).encode()).hexdigest()[:12]
                    target_article = URIRef(f"{ARTICLE_NS}temporary_{target_id}")
                    graph.add((target_article, RDF.type, Article_Ru))
                    graph.add((target_article, has_original_uri, uri_ref))
                
                graph.add((article_uri, relevant_article, target_article))
    
    # Источник
    graph.add((article_uri, has_source, source_uri))
    
    return graph, article_uri

def xml_to_rdf(input_dir, output_dir):
    """Преобразование всех XML файлов в RDF"""
    
    # Создаем выходную директорию, если не существует
    os.makedirs(output_dir, exist_ok=True)
    
    # Запрос информации об источнике у пользователя
    print("=" * 60)
    print("ПРЕОБРАЗОВАНИЕ XML В RDF")
    print("=" * 60)
    
    source_name = input("Введите название источника (например, 'fme'): ").strip()
    if not source_name:
        source_name = "unknown_source"
    
    source_title = input("Введите полное название источника (например, 'Физико-математическая энциклопедия'): ").strip()
    if not source_title:
        source_title = f"Источник: {source_name}"
    
    # Создаем URI для источника
    source_id = normalize_term_name(source_name)
    source_uri = URIRef(f"{SOURCE_NS}{source_id}")
    
    # Инициализация графа
    graph = Graph()
    
    # Загрузка существующего графа, если есть
    output_file = os.path.join(output_dir, "articles.rdf")
    if os.path.exists(output_file):
        graph.parse(output_file, format="turtle")
        print(f"\nЗагружен существующий граф из {output_file}")
    
    # Добавляем источник в граф
    graph.add((source_uri, RDF.type, Source))
    graph.add((source_uri, has_title, Literal(source_title)))
    
    # Находим все XML файлы
    xml_files = [f for f in os.listdir(input_dir) if f.endswith('.xml')]
    
    print(f"\nНайдено {len(xml_files)} XML файлов для обработки")
    print(f"Источник: {source_title} ({source_uri})")
    print("-" * 60)
    
    if not xml_files:
        print("Нет XML файлов для обработки.")
        return graph
    
    # Обработка каждого файла с прогресс-баром
    processed_count = 0
    skipped_count = 0
    
    for xml_file in tqdm(xml_files, desc="Обработка XML файлов"):
        xml_path = os.path.join(input_dir, xml_file)
        
        try:
            graph, article_uri = process_article_xml(xml_path, graph, source_uri, source_name)
            processed_count += 1
            # Закомментировано: print(f"  ✓ Успешно обработан: {xml_file}")
        except Exception as e:
            print(f"\n✗ Ошибка при обработке {xml_file}: {str(e)}")
            skipped_count += 1
    
    # Сохранение графа
    graph.bind("fme", FME)
    graph.bind("person", PERSON_NS)
    graph.bind("publication", PUBLICATION_NS)
    graph.bind("formula", FORMULA_NS)
    graph.bind("source", SOURCE_NS)
    graph.bind("article", ARTICLE_NS)
    graph.bind("term", TERM_NS)
    graph.bind("ontology", class_ns)
    
    # Сохраняем в нескольких форматах для удобства
    graph.serialize(destination=output_file, format="turtle")
    
    # Также сохраняем в XML/RDF для совместимости
    xml_output = os.path.join(output_dir, "articles.xml")
    graph.serialize(destination=xml_output, format="xml")
    
    # Статистика
    print("\n" + "=" * 60)
    print("ОБРАБОТКА ЗАВЕРШЕНА")
    print("=" * 60)
    print(f"Обработано файлов: {processed_count}")
    if skipped_count > 0:
        print(f"Пропущено файлов: {skipped_count}")
    
    # Получаем статистику из графа
    articles = list(graph.subjects(RDF.type, Article_Ru))
    persons = list(graph.subjects(RDF.type, Person))
    publications = list(graph.subjects(RDF.type, Publication))
    formulas = list(graph.subjects(RDF.type, Formula))
    terms = list(graph.subjects(RDF.type, Term))
    sources = list(graph.subjects(RDF.type, Source))
    
    print(f"\n=== СТАТИСТИКА ГРАФА ===")
    print(f"Всего статей: {len(articles)}")
    print(f"Всего авторов: {len(persons)}")
    print(f"Всего публикаций: {len(publications)}")
    print(f"Всего формул: {len(formulas)}")
    print(f"Всего терминов: {len(terms)}")
    print(f"Всего источников: {len(sources)}")
    
    # Информация о сохраненных файлах
    print(f"\nРезультаты сохранены:")
    print(f"  Turtle формат: {os.path.abspath(output_file)}")
    print(f"  XML/RDF формат: {os.path.abspath(xml_output)}")
    
    return graph

if __name__ == "__main__":
    # Настройка путей
    input_directory = "./xml_articles"  # Папка с XML файлами
    output_directory = "./rdf_output"   # Папка для RDF результатов
    
    # Преобразование
    rdf_graph = xml_to_rdf(input_directory, output_directory)