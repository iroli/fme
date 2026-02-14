# ont_analysis/graph_loader.py
"""
Загрузка графа из TTL-файлов или через SPARQL (GraphDB).
Используется в ноутбуках анализа.
"""
import os
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

# Префиксы онтологии (как в RDF_converter)
SG = Namespace("https://scilib.ai/ontology/semantic-graph/")
DATA = Namespace("https://scilib.ai/id/")
FME = Namespace("http://libmeta.ru/fme/")
ME = Namespace("http://libmeta.ru/me/")

# Папка с TTL по умолчанию (относительно корня ont_analysis)
DEFAULT_GRAPH_DIR = Path(__file__).resolve().parent / "graph"


def load_graph_from_ttl(graph_dir: os.PathLike = None) -> Graph:
    """
    Загрузить полный RDF-граф из всех TTL в указанной папке.
    Возвращает один объединённый граф (только данные, без ontology).
    """
    graph_dir = Path(graph_dir or DEFAULT_GRAPH_DIR)
    g = Graph()
    g.bind("sg", SG)
    g.bind("rdfs", RDFS)
    g.bind("data", DATA)
    g.bind("fme", FME)
    g.bind("me", ME)

    data_files = [
        "thesaurus.ttl",
        "terms.ttl",
        "articles.ttl",
        "persons.ttl",
        "publications.ttl",
        "formulas.ttl",
    ]
    for fname in data_files:
        path = graph_dir / fname
        if path.exists():
            g.parse(path, format="turtle")
    return g


def get_sparql_endpoint():
    """
    URL эндпоинта GraphDB для SPARQL-запросов.
    Задайте через переменную окружения GRAPHDB_ENDPOINT или здесь по умолчанию.
    """
    return os.environ.get(
        "GRAPHDB_ENDPOINT",
        "http://localhost:7200/repositories/your_repo",
    )


def run_sparql(query: str, endpoint: str = None) -> list:
    """
    Выполнить SPARQL SELECT и вернуть список строк (каждая строка — словарь по именам переменных).
    Требует: pip install sparqlwrapper
    """
    try:
        from SPARQLWrapper import SPARQLWrapper, JSON
    except ImportError:
        raise ImportError("Установите SPARQLWrapper: pip install sparqlwrapper")

    endpoint = endpoint or get_sparql_endpoint()
    wrapper = SPARQLWrapper(endpoint)
    wrapper.setQuery(query)
    wrapper.setReturnFormat(JSON)
    results = wrapper.query().convert()
    rows = []
    for binding in results.get("results", {}).get("bindings", []):
        row = {}
        for k, v in binding.items():
            row[k] = v.get("value")
            if v.get("type") == "literal" and "xml:lang" in v:
                row[f"{k}_lang"] = v.get("xml:lang")
        rows.append(row)
    return rows
