import os
import re
import xml.etree.ElementTree as ET
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD
import uuid
from tqdm.auto import tqdm

# Настройка пространств имен RDF
FME = Namespace("http://libmeta.ru/fme/")
PERSON_NS = Namespace("http://libmeta.ru/person/")
PUBLICATION_NS = Namespace("http://libmeta.ru/publication/")
FORMULA_NS = Namespace("http://libmeta.ru/fme/formula/")
SOURCE_NS = Namespace("http://libmeta.ru/source/")

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

def extract_uri_from_brackets(text):
    """Извлечение URI из формата URI[[...]]/URI"""
    if not text:
        return []
    uris = re.findall(r'URI\[\[(.*?)\]\]/URI', text)
    return uris

def process_article_xml(xml_path, graph, processed_articles=None):
    """Обработка одного XML файла статьи"""
    if processed_articles is None:
        processed_articles = set()
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # URI статьи
    article_uri = URIRef(root.get('uri'))
    
    # Пропуск, если статья уже обработана
    if article_uri in processed_articles:
        return graph, processed_articles
    
    processed_articles.add(article_uri)
    
    # Тип статьи
    graph.add((article_uri, RDF.type, Article_Ru))
    
    # Название статьи (Term)
    title = root.find('title').text
    graph.add((article_uri, has_title, Literal(title)))
    
    # Term содержится в статье
    term_uri = URIRef(f"{article_uri}#term")
    graph.add((term_uri, RDF.type, Term))
    graph.add((term_uri, has_title, Literal(title)))
    graph.add((article_uri, contained_in, term_uri))
    
    # Авторы статьи
    authors_elem = root.find('authors')
    if authors_elem is not None:
        for author_elem in authors_elem.findall('author'):
            author_name = author_elem.text.strip()
            author_uri = URIRef(PERSON_NS[author_name.replace(' ', '_')])
            
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
                pub_id = f"{author_elem.text.replace(' ', '_')}_{title_elem.text.replace(' ', '_')}"
                if year_elem is not None and year_elem.text:
                    pub_id += f"_{year_elem.text}"
                
                publication_uri = URIRef(PUBLICATION_NS[pub_id])
                graph.add((publication_uri, RDF.type, Publication))
                
                # Автор публикации
                if author_elem.text:
                    pub_author_name = author_elem.text.strip()
                    pub_author_uri = URIRef(PERSON_NS[pub_author_name.replace(' ', '_')])
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
            formula_uri = URIRef(formula_elem.get('uri'))
            graph.add((formula_uri, RDF.type, Formula))
            
            if formula_elem.text:
                graph.add((formula_uri, has_formula_text, Literal(formula_elem.text)))
            
            graph.add((article_uri, used_in_text, formula_uri))
    
    # Вспомогательные формулы
    #formulas_aux_elem = root.find('formulas_aux')
    #if formulas_aux_elem is not None:
    #    for formula_elem in formulas_aux_elem.findall('formula'):
    #        formula_uri = URIRef(formula_elem.get('uri'))
    #        graph.add((formula_uri, RDF.type, Formula))
    #        
    #        if formula_elem.text:
    #            graph.add((formula_uri, has_formula_text, Literal(formula_elem.text)))
    #        
    #        graph.add((article_uri, used_in_text, formula_uri))
    
    # Связи с другими статьями
    relations_elem = root.find('relations')
    if relations_elem is not None:
        for relation_elem in relations_elem.findall('relation'):
            rel_text_elem = relation_elem.find('rel_text')
            target_elem = relation_elem.find('target')
            
            if target_elem is not None and target_elem.text:
                target_uri = URIRef(target_elem.text)
                
                # Создаем связанную статью (если еще не существует)
                graph.add((target_uri, RDF.type, Article_Ru))
                
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
                graph.add((uri_ref, RDF.type, Formula))
                graph.add((article_uri, used_in_text, uri_ref))
            elif 'article' in uri:
                graph.add((uri_ref, RDF.type, Article_Ru))
                graph.add((article_uri, relevant_article, uri_ref))
    
    # Источник (предполагаем, что это физико-математическая энциклопедия)
    source_uri = URIRef(SOURCE_NS["fme"])
    graph.add((source_uri, RDF.type, Source))
    graph.add((source_uri, has_title, Literal("Физико-математическая энциклопедия")))
    graph.add((article_uri, taken_from, source_uri))
    
    return graph, processed_articles

def xml_to_rdf(input_dir, output_dir):
    """Преобразование всех XML файлов в RDF"""
    
    # Создаем выходную директорию, если не существует
    os.makedirs(output_dir, exist_ok=True)
    
    # Инициализация графа
    graph = Graph()
    
    # Загрузка существующего графа, если есть
    output_file = os.path.join(output_dir, "articles.rdf")
    if os.path.exists(output_file):
        graph.parse(output_file, format="turtle")
        print(f"Загружен существующий граф из {output_file}")
    
    # Множество обработанных статей (для избежания дублирования)
    processed_articles = set()
    
    # Находим все XML файлы
    xml_files = [f for f in os.listdir(input_dir) if f.endswith('.xml')]
    
    print(f"Найдено {len(xml_files)} XML файлов для обработки")
    
    # Обработка каждого файла
    for xml_file in tqdm(xml_files):
        xml_path = os.path.join(input_dir, xml_file)
        #print(f"Обработка файла: {xml_file}")
        
        try:
            graph, processed_articles = process_article_xml(xml_path, graph, processed_articles)
            #print(f"  ✓ Успешно обработан")
        except Exception as e:
            print(f"  ✗ Ошибка при обработке {xml_file}: {str(e)}")
    
    # Сохранение графа
    graph.bind("fme", FME)
    graph.bind("person", PERSON_NS)
    graph.bind("publication", PUBLICATION_NS)
    graph.bind("formula", FORMULA_NS)
    graph.bind("source", SOURCE_NS)
    graph.bind("ontology", class_ns)
    
    # Сохраняем в нескольких форматах для удобства
    graph.serialize(destination=output_file, format="turtle")
    print(f"Граф сохранен в {output_file}")
    
    # Также сохраняем в XML/RDF для совместимости
    xml_output = os.path.join(output_dir, "articles.xml")
    graph.serialize(destination=xml_output, format="xml")
    print(f"Граф также сохранен в {xml_output}")
    
    # Статистика
    print("\n=== СТАТИСТИКА ===")
    print(f"Всего статей: {len([s for s in graph.subjects(RDF.type, Article_Ru)])}")
    print(f"Всего авторов: {len([s for s in graph.subjects(RDF.type, Person)])}")
    print(f"Всего публикаций: {len([s for s in graph.subjects(RDF.type, Publication)])}")
    print(f"Всего формул: {len([s for s in graph.subjects(RDF.type, Formula)])}")
    print(f"Всего терминов: {len([s for s in graph.subjects(RDF.type, Term)])}")
    
    return graph

if __name__ == "__main__":
    # Настройка путей
    input_directory = "./xml_articles"  # Папка с XML файлами
    output_directory = "./rdf_output"   # Папка для RDF результатов
    
    # Преобразование
    rdf_graph = xml_to_rdf(input_directory, output_directory)
