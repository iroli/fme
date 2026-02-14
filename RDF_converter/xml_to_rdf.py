#!/usr/bin/env python3
"""
Convert encyclopedia XML articles into RDF Turtle (TTL) according to a semantic graph model.
Handles merging of existing data and produces statistics.
"""

import argparse
import glob
import os
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict
from tqdm.auto import tqdm

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from rdflib.plugins.serializers.turtle import TurtleSerializer

# ----------------------------------------------------------------------
# Namespaces
# ----------------------------------------------------------------------
SG = Namespace("https://scilib.ai/ontology/semantic-graph/")
DATA = Namespace("https://scilib.ai/id/")
LIBRARY = {
    "fme": Namespace("http://libmeta.ru/fme/"),
    "me": Namespace("http://libmeta.ru/me/"),
}

# UUID namespaces for deterministic generation
PERSON_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "https://scilib.ai/id/person")
PUBLICATION_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "https://scilib.ai/id/publication")
TERM_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "https://scilib.ai/id/term")


# ----------------------------------------------------------------------
# Converter Class
# ----------------------------------------------------------------------
class XMLToRDFConverter:
    """Main converter: loads XML, builds RDF graphs, writes TTL files."""

    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Statistics
        self.stats = {
            "articles": {"new": 0, "duplicate": 0, "total_before": 0, "total_after": 0},
            "terms": {"new": 0, "duplicate": 0, "total_before": 0, "total_after": 0},
            "persons": {"new": 0, "duplicate": 0, "total_before": 0, "total_after": 0},
            "publications": {"new": 0, "duplicate": 0, "total_before": 0, "total_after": 0},
            "formulas": {"new": 0, "duplicate": 0, "total_before": 0, "total_after": 0},
            "relations": {"new": 0, "duplicate": 0, "total_before": 0, "total_after": 0},
        }

        # RDF graphs for each entity class
        self.g_ontology = Graph()
        self.g_thesaurus = Graph()
        self.g_terms = Graph()
        self.g_articles = Graph()
        self.g_persons = Graph()
        self.g_publications = Graph()
        self.g_formulas = Graph()

        # Keep track of already processed article URIs in this run
        self.processed_articles = set()
        # Map article URI -> title for resolving hasRelation targets to Terms (XML + загруженные TTL)
        self.article_title_by_uri = {}

        self._bind_namespaces()
        self._create_ontology()          # static ontology triples
        self._create_thesaurus_individuals()

        # Load existing TTL files (if any) – merge previous runs
        self._load_existing_data()
        # Восстановить article_uri -> title из уже загруженных данных (корректный повторный запуск)
        self._build_article_title_map_from_loaded_data()

    # ------------------------------------------------------------------
    # Namespace binding
    # ------------------------------------------------------------------
    def _bind_namespaces(self):
        """Bind common prefixes to all graphs for cleaner Turtle output."""
        for g in [self.g_ontology, self.g_thesaurus, self.g_terms, self.g_articles,
                  self.g_persons, self.g_publications, self.g_formulas]:
            g.bind("sg", SG)
            g.bind("rdf", RDF)
            g.bind("rdfs", RDFS)
            g.bind("xsd", XSD)
            g.bind("fme", LIBRARY["fme"])
            g.bind("me", LIBRARY["me"])
            g.bind("data", DATA)

    # ------------------------------------------------------------------
    # Ontology definition
    # ------------------------------------------------------------------
    def _create_ontology(self):
        """Define classes and properties used in the semantic graph."""
        # Classes
        self.g_ontology.add((SG.Thesaurus, RDF.type, RDFS.Class))
        self.g_ontology.add((SG.Article, RDF.type, RDFS.Class))
        self.g_ontology.add((SG.Term, RDF.type, RDFS.Class))
        self.g_ontology.add((SG.Person, RDF.type, RDFS.Class))
        self.g_ontology.add((SG.Publication, RDF.type, RDFS.Class))
        self.g_ontology.add((SG.Formula, RDF.type, RDFS.Class))

        # Object properties
        self.g_ontology.add((SG.hasType, RDF.type, RDF.Property))
        self.g_ontology.add((SG.hasType, RDFS.domain, SG.Thesaurus))
        self.g_ontology.add((SG.hasType, RDFS.range, RDFS.Class))

        self.g_ontology.add((SG.hasClass, RDF.type, RDF.Property))
        self.g_ontology.add((SG.hasClass, RDFS.domain, SG.Thesaurus))
        self.g_ontology.add((SG.hasClass, RDFS.range, RDFS.Class))

        self.g_ontology.add((SG.hasThesaurus, RDF.type, RDF.Property))
        self.g_ontology.add((SG.hasThesaurus, RDFS.domain, SG.Article))
        self.g_ontology.add((SG.hasThesaurus, RDFS.range, SG.Thesaurus))

        self.g_ontology.add((SG.hasAuthor, RDF.type, RDF.Property))
        self.g_ontology.add((SG.hasAuthor, RDFS.domain, SG.Article))
        self.g_ontology.add((SG.hasAuthor, RDFS.range, SG.Person))
        self.g_ontology.add((SG.hasAuthor, RDFS.domain, SG.Publication))  # литература — автор(ы)
        # Inverse
        self.g_ontology.add((SG.hasArticle, RDF.type, RDF.Property))
        self.g_ontology.add((SG.hasArticle, RDFS.domain, SG.Person))
        self.g_ontology.add((SG.hasArticle, RDFS.range, SG.Article))
        self.g_ontology.add((SG.hasArticle, SG.inverseOf, SG.hasAuthor))

        self.g_ontology.add((SG.hasPublication, RDF.type, RDF.Property))
        self.g_ontology.add((SG.hasPublication, RDFS.domain, SG.Person))
        self.g_ontology.add((SG.hasPublication, RDFS.range, SG.Publication))
        # Связь литература–автор: Publication hasAuthor Person; Person hasPublication Publication

        self.g_ontology.add((SG.hasTerm, RDF.type, RDF.Property))
        self.g_ontology.add((SG.hasTerm, RDFS.domain, SG.Article))
        self.g_ontology.add((SG.hasTerm, RDFS.range, SG.Term))
        self.g_ontology.add((SG.denotesArticle, RDF.type, RDF.Property))
        self.g_ontology.add((SG.denotesArticle, RDFS.domain, SG.Term))
        self.g_ontology.add((SG.denotesArticle, RDFS.range, SG.Article))
        self.g_ontology.add((SG.denotesArticle, SG.inverseOf, SG.hasTerm))

        self.g_ontology.add((SG.refersTo, RDF.type, RDF.Property))
        self.g_ontology.add((SG.refersTo, RDFS.domain, SG.Article))
        self.g_ontology.add((SG.refersTo, RDFS.range, SG.Publication))
        # Inverse
        self.g_ontology.add((SG.referredIn, RDF.type, RDF.Property))
        self.g_ontology.add((SG.referredIn, RDFS.domain, SG.Publication))
        self.g_ontology.add((SG.referredIn, RDFS.range, SG.Article))
        self.g_ontology.add((SG.referredIn, SG.inverseOf, SG.refersTo))

        self.g_ontology.add((SG.hasFormula, RDF.type, RDF.Property))
        self.g_ontology.add((SG.hasFormula, RDFS.domain, SG.Article))
        self.g_ontology.add((SG.hasFormula, RDFS.range, SG.Formula))
        # Inverse
        self.g_ontology.add((SG.usedIn, RDF.type, RDF.Property))
        self.g_ontology.add((SG.usedIn, RDFS.domain, SG.Formula))
        self.g_ontology.add((SG.usedIn, RDFS.range, SG.Article))
        self.g_ontology.add((SG.usedIn, SG.inverseOf, SG.hasFormula))

        self.g_ontology.add((SG.hasRelation, RDF.type, RDF.Property))
        self.g_ontology.add((SG.hasRelation, RDFS.domain, SG.Article))
        self.g_ontology.add((SG.hasRelation, RDFS.range, SG.Term))  # ссылки ведут на термин (название), не на статью

        # Datatype properties
        self.g_ontology.add((SG.text, RDF.type, RDF.Property))
        self.g_ontology.add((SG.text, RDFS.domain, SG.Article))
        self.g_ontology.add((SG.text, RDFS.range, XSD.string))

        self.g_ontology.add((SG.pages_start, RDF.type, RDF.Property))
        self.g_ontology.add((SG.pages_start, RDFS.domain, SG.Article))
        self.g_ontology.add((SG.pages_start, RDFS.range, XSD.integer))

        self.g_ontology.add((SG.pages_end, RDF.type, RDF.Property))
        self.g_ontology.add((SG.pages_end, RDFS.domain, SG.Article))
        self.g_ontology.add((SG.pages_end, RDFS.range, XSD.integer))

        self.g_ontology.add((SG.year, RDF.type, RDF.Property))
        self.g_ontology.add((SG.year, RDFS.domain, SG.Publication))
        self.g_ontology.add((SG.year, RDFS.range, XSD.integer))

        self.g_ontology.add((SG.publication_details, RDF.type, RDF.Property))
        self.g_ontology.add((SG.publication_details, RDFS.domain, SG.Publication))
        self.g_ontology.add((SG.publication_details, RDFS.range, XSD.string))

        self.g_ontology.add((SG.other, RDF.type, RDF.Property))
        self.g_ontology.add((SG.other, RDFS.domain, SG.Publication))
        self.g_ontology.add((SG.other, RDFS.range, XSD.string))

        self.g_ontology.add((SG.latex, RDF.type, RDF.Property))
        self.g_ontology.add((SG.latex, RDFS.domain, SG.Formula))
        self.g_ontology.add((SG.latex, RDFS.range, XSD.string))

        self.g_ontology.add((SG.formula_type, RDF.type, RDF.Property))
        self.g_ontology.add((SG.formula_type, RDFS.domain, SG.Formula))
        self.g_ontology.add((SG.formula_type, RDFS.range, XSD.string))

    # ------------------------------------------------------------------
    # Thesaurus individuals (FME, ME)
    # ------------------------------------------------------------------
    def _create_thesaurus_individuals(self):
        """Add two thesaurus individuals if they do not exist."""
        fme_uri = LIBRARY["fme"][""]   # http://libmeta.ru/fme/
        me_uri = LIBRARY["me"][""]     # http://libmeta.ru/me/

        if (fme_uri, RDF.type, SG.Thesaurus) not in self.g_thesaurus:
            self.g_thesaurus.add((fme_uri, RDF.type, SG.Thesaurus))
            self.g_thesaurus.add((fme_uri, RDFS.label, Literal("Тезаурус Энциклопедии математической физики", lang="ru")))
            self.g_thesaurus.add((fme_uri, SG.hasType, SG.Object))
            self.g_thesaurus.add((fme_uri, SG.hasClass, SG.Thesaurus))

        if (me_uri, RDF.type, SG.Thesaurus) not in self.g_thesaurus:
            self.g_thesaurus.add((me_uri, RDF.type, SG.Thesaurus))
            self.g_thesaurus.add((me_uri, RDFS.label, Literal("Тезаурус Математической энциклопедии", lang="ru")))
            self.g_thesaurus.add((me_uri, SG.hasType, SG.Object))
            self.g_thesaurus.add((me_uri, SG.hasClass, SG.Thesaurus))

    # ------------------------------------------------------------------
    # Load existing TTL files (merge from previous runs)
    # ------------------------------------------------------------------
    def _load_existing_data(self):
        """If TTL files exist in output_dir, parse them into the graphs (повторный запуск — дополнение)."""
        file_map = {
            "semantic-graph.ttl": self.g_ontology,
            "thesaurus.ttl": self.g_thesaurus,
            "terms.ttl": self.g_terms,
            "articles.ttl": self.g_articles,
            "persons.ttl": self.g_persons,
            "publications.ttl": self.g_publications,
            "formulas.ttl": self.g_formulas,
        }
        for fname, graph in tqdm(file_map.items(), desc="Loading existing TTL files..."):
            path = os.path.join(self.output_dir, fname)
            if os.path.exists(path):
                graph.parse(path, format="turtle")

        # Update statistics "total_before" counts
        self.stats["articles"]["total_before"] = self._count_instances(self.g_articles, SG.Article)
        self.stats["terms"]["total_before"] = self._count_instances(self.g_terms, SG.Term)
        self.stats["persons"]["total_before"] = self._count_instances(self.g_persons, SG.Person)
        self.stats["publications"]["total_before"] = self._count_instances(self.g_publications, SG.Publication)
        self.stats["formulas"]["total_before"] = self._count_instances(self.g_formulas, SG.Formula)
        self.stats["relations"]["total_before"] = self._count_relation_triples()

    def _build_article_title_map_from_loaded_data(self):
        """По загруженным articles + terms восстановить article_uri -> title (для повторного запуска)."""
        for article_uri, _, term_uri in self.g_articles.triples((None, SG.hasTerm, None)):
            for p, o in self.g_terms.predicate_objects(term_uri):
                if p == RDFS.label and isinstance(o, Literal):
                    self.article_title_by_uri[article_uri] = str(o)
                    break

    @staticmethod
    def _count_instances(graph: Graph, class_uri: URIRef) -> int:
        """Number of distinct individuals of a given class in the graph."""
        subjects = set(graph.subjects(RDF.type, class_uri))
        return len(subjects)

    def _count_relation_triples(self) -> int:
        """Number of :hasRelation triples in articles graph."""
        return len(list(self.g_articles.triples((None, SG.hasRelation, None))))

    # ------------------------------------------------------------------
    # URI generators (deterministic UUIDs)
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_name(name: str) -> str:
        """Basic normalization for person names."""
        return " ".join(name.strip().lower().split())

    def generate_person_uri(self, name: str) -> URIRef:
        """Deterministic UUID5 URI for a person."""
        norm = self._normalize_name(name)
        uid = uuid.uuid5(PERSON_NS, norm)
        return DATA[f"person-{uid}"]

    def generate_publication_uri(self, authors: list, title: str, publication: str, year: str) -> URIRef:
        """Deterministic UUID5 URI for a publication (authors: list of author names)."""
        authors_key = "|".join(sorted(a.strip() for a in authors)) if authors else ""
        key = f"{authors_key}|{title}|{publication}|{year}"
        uid = uuid.uuid5(PUBLICATION_NS, key)
        return DATA[f"publication-{uid}"]

    def generate_term_uri(self, title: str) -> URIRef:
        """Deterministic URI for a Term by normalized title (same title => same Term)."""
        norm = " ".join(title.strip().lower().split()) if title else ""
        uid = uuid.uuid5(TERM_NS, norm)
        return DATA[f"term-{uid}"]

    # ------------------------------------------------------------------
    # Main processing
    # ------------------------------------------------------------------
    def process_all_xml(self):
        """Find all XML files in input_dir: first pass — collect uri→title, second — full processing."""
        pattern = os.path.join(self.input_dir, "*.xml")
        xml_files = list(glob.glob(pattern))
        # Первый проход: собрать для каждой статьи (uri, title) для подстановки Term в hasRelation
        for xml_path in tqdm(xml_files, desc="Pass 1: collecting article titles..."):
            self._collect_article_title(xml_path)
        # Второй проход: полная обработка (статьи, Term, связи на Term)
        for xml_path in tqdm(xml_files, desc="Processing XML files..."):
            self.process_xml_file(xml_path)
        self._update_final_stats()

    def _collect_article_title(self, xml_path: str):
        """Read XML and record article URI → title (for resolving relation targets to Terms)."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError:
            return
        article_uri = root.get("uri")
        if not article_uri:
            return
        title_elem = root.find("title")
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
        self.article_title_by_uri[URIRef(article_uri)] = title

    def process_xml_file(self, xml_path: str):
        """Parse a single XML file and add its content to the RDF graphs."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"Error parsing {xml_path}: {e}")
            return

        # ----- Article URI and Thesaurus -----
        article_uri = URIRef(root.get("uri"))
        if article_uri in self.processed_articles:
            print(f"Duplicate article in same run: {article_uri}, skipping")
            return
        self.processed_articles.add(article_uri)

        # Determine thesaurus from URI
        uri_str = str(article_uri)
        if "fme" in uri_str:
            thesaurus_uri = LIBRARY["fme"][""]
        elif "me" in uri_str:
            thesaurus_uri = LIBRARY["me"][""]
        else:
            thesaurus_uri = None

        # ----- Title -----
        title_elem = root.find("title")
        title = title_elem.text if title_elem is not None else ""

        # ----- Authors -----
        authors_elem = root.find("authors")
        author_names = []
        if authors_elem is not None:
            author_names = [a.text.strip() for a in authors_elem.findall("author") if a.text]

        # ----- Pages -----
        pages_start = None
        pages_end = None
        pages_elem = root.find("pages")
        if pages_elem is not None:
            start_elem = pages_elem.find("start")
            end_elem = pages_elem.find("end")
            if start_elem is not None and start_elem.text:
                pages_start = int(start_elem.text)
            if end_elem is not None and end_elem.text:
                pages_end = int(end_elem.text)

        # ----- Literature (Publications) -----
        literature_units = []
        lit_elem = root.find("literature")
        if lit_elem is not None:
            for unit in lit_elem.findall("unit"):
                author_elems = unit.findall("author")
                authors = [a.text.strip() for a in author_elems if a.text and a.text.strip()]
                if not authors:
                    author_e = unit.find("author")
                    authors = [author_e.text.strip() if author_e is not None and author_e.text else ""]
                title_e = unit.find("title")
                pub_e = unit.find("publication")
                year_e = unit.find("year")
                other_e = unit.find("other")
                if title_e is not None and title_e.text and pub_e is not None and pub_e.text:
                    literature_units.append({
                        "authors": authors,
                        "title": title_e.text.strip() if title_e.text else "",
                        "publication": pub_e.text.strip() if pub_e.text else "",
                        "year": year_e.text.strip() if year_e is not None and year_e.text else "",
                        "other": other_e.text.strip() if other_e is not None and other_e.text else "",
                    })

        # ----- Formulas -----
        formulas = []
        ##################################################################################
        # Обработка aux выключена для сокращения времени обработки графа
        # for ftype, parent in [("main", root.find("formulas_main")), ("aux", root.find("formulas_aux"))]:
        ##################################################################################
        for ftype, parent in [("main", root.find("formulas_main"))]:
            if parent is not None:
                for f in parent.findall("formula"):
                    uri_attr = f.get("uri")
                    if uri_attr:
                        formulas.append({
                            "uri": URIRef(uri_attr),
                            "latex": f.text.strip() if f.text else "",
                            "type": ftype,
                        })

        # ----- Relations (cross-references) -----
        relations = []
        rels_elem = root.find("relations")
        if rels_elem is not None:
            for rel in rels_elem.findall("relation"):
                target = rel.find("target")
                if target is not None and target.text:
                    relations.append(URIRef(target.text.strip()))

        # ----- Text -----
        text_elem = root.find("text")
        text = text_elem.text.strip() if text_elem is not None and text_elem.text else ""

        # ------------------------------------------------------------------
        # Add data to RDF graphs
        # ------------------------------------------------------------------
        # 1. Article individual (дубликаты статей не удаляем — каждая статья уникальна по URI)
        self._add_article(article_uri, title, text, pages_start, pages_end, thesaurus_uri)

        # 1b. Term с названием статьи; статьи с одинаковым названием разделяют один Term
        term_uri = self._add_term(title)
        self.g_articles.add((article_uri, SG.hasTerm, term_uri))
        self.g_terms.add((term_uri, SG.denotesArticle, article_uri))

        # 2. Authors and hasAuthor links
        for name in author_names:
            person_uri = self._add_person(name)
            self.g_articles.add((article_uri, SG.hasAuthor, person_uri))
            self.g_persons.add((person_uri, SG.hasArticle, article_uri))

        # 3. Publications and references
        for pub_data in literature_units:
            pub_uri = self._add_publication(pub_data)
            self.g_articles.add((article_uri, SG.refersTo, pub_uri))
            self.g_publications.add((pub_uri, SG.referredIn, article_uri))
            # Link publication to each author (Person) — у литературы может быть несколько авторов
            for author_name in pub_data["authors"]:
                if not author_name:
                    continue
                person_uri = self._add_person(author_name)
                self.g_publications.add((pub_uri, SG.hasAuthor, person_uri))
                self.g_persons.add((person_uri, SG.hasPublication, pub_uri))

        # 4. Formulas
        for fdata in formulas:
            self._add_formula(fdata["uri"], fdata["latex"], fdata["type"], article_uri)
            self.g_articles.add((article_uri, SG.hasFormula, fdata["uri"]))
            self.g_formulas.add((fdata["uri"], SG.usedIn, article_uri))

        # 5. Relations: ссылки ведут на Term (название), не на статью — граф чище
        for target_uri in relations:
            target_title = self.article_title_by_uri.get(target_uri)
            if target_title is not None:
                target_term_uri = self._add_term(target_title)
            else:
                # Целевая статья не из нашего корпуса — Term по URI
                target_term_uri = self._get_or_create_term_for_article_uri(target_uri)
            self.g_articles.add((article_uri, SG.hasRelation, target_term_uri))
            self.stats["relations"]["new"] += 1

    # ------------------------------------------------------------------
    # Individual adders with duplicate detection
    # ------------------------------------------------------------------
    def _add_article(self, uri: URIRef, title: str, text: str,
                     pages_start: int, pages_end: int, thesaurus_uri: URIRef):
        """Add an Article individual if not already present."""
        if (uri, RDF.type, SG.Article) not in self.g_articles:
            self.g_articles.add((uri, RDF.type, SG.Article))
            self.g_articles.add((uri, SG.hasType, SG.Object))
            self.g_articles.add((uri, SG.hasClass, SG.Article))
            self.stats["articles"]["new"] += 1
        else:
            self.stats["articles"]["duplicate"] += 1

        # Add or replace label, text, pages, thesaurus
        self.g_articles.add((uri, RDFS.label, Literal(title, lang="ru")))
        if text:
            self.g_articles.add((uri, SG.text, Literal(text, lang="ru")))
        if pages_start is not None:
            self.g_articles.add((uri, SG.pages_start, Literal(pages_start, datatype=XSD.integer)))
        if pages_end is not None:
            self.g_articles.add((uri, SG.pages_end, Literal(pages_end, datatype=XSD.integer)))
        if thesaurus_uri:
            self.g_articles.add((uri, SG.hasThesaurus, thesaurus_uri))

    def _add_person(self, name: str) -> URIRef:
        """Add a Person individual (or merge into existing); return URI."""
        uri = self.generate_person_uri(name)
        if (uri, RDF.type, SG.Person) not in self.g_persons:
            self.g_persons.add((uri, RDF.type, SG.Person))
            self.g_persons.add((uri, SG.hasType, SG.Object))
            self.g_persons.add((uri, SG.hasClass, SG.Person))
            self.stats["persons"]["new"] += 1
        else:
            self.stats["persons"]["duplicate"] += 1
        # Всегда добавляем/дополняем свойства при слиянии дубликатов
        self.g_persons.add((uri, RDFS.label, Literal(name, lang="ru")))
        return uri

    def _add_publication(self, data: dict) -> URIRef:
        """Add a Publication individual (or merge into existing); return URI."""
        uri = self.generate_publication_uri(data["authors"], data["title"],
                                            data["publication"], data["year"])
        is_new = (uri, RDF.type, SG.Publication) not in self.g_publications
        if is_new:
            self.g_publications.add((uri, RDF.type, SG.Publication))
            self.g_publications.add((uri, SG.hasType, SG.Object))
            self.g_publications.add((uri, SG.hasClass, SG.Publication))
            self.stats["publications"]["new"] += 1
        else:
            self.stats["publications"]["duplicate"] += 1
        # Всегда добавляем/дополняем свойства (слияние дубликатов с сохранением данных)
        self.g_publications.add((uri, RDFS.label, Literal(data["title"], lang="ru")))
        self.g_publications.add((uri, SG.publication_details, Literal(data["publication"], lang="ru")))
        if data.get("year"):
            self.g_publications.add((uri, SG.year, Literal(int(data["year"]), datatype=XSD.integer)))
        if data.get("other"):
            self.g_publications.add((uri, SG.other, Literal(data["other"], lang="ru")))
        return uri

    def _add_term(self, title: str) -> URIRef:
        """Создать или вернуть Term с заданным названием (одинаковое название — один Term)."""
        uri = self.generate_term_uri(title)
        if (uri, RDF.type, SG.Term) not in self.g_terms:
            self.g_terms.add((uri, RDF.type, SG.Term))
            self.g_terms.add((uri, SG.hasType, SG.Object))
            self.g_terms.add((uri, SG.hasClass, SG.Term))
            self.stats["terms"]["new"] += 1
        else:
            self.stats["terms"]["duplicate"] += 1
        self.g_terms.add((uri, RDFS.label, Literal(title, lang="ru")))
        return uri

    def _get_or_create_term_for_article_uri(self, article_uri: URIRef) -> URIRef:
        """Term для статьи вне корпуса (нет названия): URI по строке article_uri."""
        title = str(article_uri)
        uri = self.generate_term_uri(title)
        if (uri, RDF.type, SG.Term) not in self.g_terms:
            self.g_terms.add((uri, RDF.type, SG.Term))
            self.g_terms.add((uri, SG.hasType, SG.Object))
            self.g_terms.add((uri, SG.hasClass, SG.Term))
            self.g_terms.add((uri, RDFS.label, Literal(title, lang="ru")))
            self.stats["terms"]["new"] += 1
        return uri

    def _add_formula(self, uri: URIRef, latex: str, ftype: str, article_uri: URIRef):
        """Add a Formula individual (or merge into existing)."""
        if (uri, RDF.type, SG.Formula) not in self.g_formulas:
            self.g_formulas.add((uri, RDF.type, SG.Formula))
            self.g_formulas.add((uri, SG.hasType, SG.Object))
            self.g_formulas.add((uri, SG.hasClass, SG.Formula))
            self.stats["formulas"]["new"] += 1
        else:
            self.stats["formulas"]["duplicate"] += 1
        # Всегда добавляем/дополняем свойства при слиянии дубликатов
        self.g_formulas.add((uri, RDFS.label, Literal(latex, lang="ru")))
        self.g_formulas.add((uri, SG.latex, Literal(latex, lang="ru")))
        self.g_formulas.add((uri, SG.formula_type, Literal(ftype, lang="ru")))
        # usedIn is added by caller

    # ------------------------------------------------------------------
    # Final statistics update
    # ------------------------------------------------------------------
    def _update_final_stats(self):
        """Update total_after counters."""
        self.stats["articles"]["total_after"] = self._count_instances(self.g_articles, SG.Article)
        self.stats["terms"]["total_after"] = self._count_instances(self.g_terms, SG.Term)
        self.stats["persons"]["total_after"] = self._count_instances(self.g_persons, SG.Person)
        self.stats["publications"]["total_after"] = self._count_instances(self.g_publications, SG.Publication)
        self.stats["formulas"]["total_after"] = self._count_instances(self.g_formulas, SG.Formula)
        self.stats["relations"]["total_after"] = self._count_relation_triples()

    # ------------------------------------------------------------------
    # Write output files
    # ------------------------------------------------------------------
    def save_output(self):
        """Serialize each graph to its corresponding TTL file."""
        file_map = {
            "semantic-graph.ttl": self.g_ontology,
            "thesaurus.ttl": self.g_thesaurus,
            "terms.ttl": self.g_terms,
            "articles.ttl": self.g_articles,
            "persons.ttl": self.g_persons,
            "publications.ttl": self.g_publications,
            "formulas.ttl": self.g_formulas,
        }
        for fname, graph in tqdm(file_map.items(), desc="Saving TTL files..."):
            path = os.path.join(self.output_dir, fname)
            graph.serialize(path, format="turtle", encoding="utf-8")

    # ------------------------------------------------------------------
    # Print statistics
    # ------------------------------------------------------------------
    def print_statistics(self):
        """Display detailed statistics about the run."""
        print("\n" + "=" * 60)
        print("STATISTICS")
        print("=" * 60)

        def print_class_stats(name, stats):
            print(f"\n{name.upper()}:")
            print(f"  New objects added:       {stats['new']}")
            print(f"  Duplicate objects merged:{stats['duplicate']}")
            print(f"  Total before this run:   {stats['total_before']}")
            print(f"  Total after this run:    {stats['total_after']}")
            print(f"  Net change:              {stats['total_after'] - stats['total_before']}")

        print_class_stats("articles", self.stats["articles"])
        print_class_stats("terms", self.stats["terms"])
        print_class_stats("persons", self.stats["persons"])
        print_class_stats("publications", self.stats["publications"])
        print_class_stats("formulas", self.stats["formulas"])
        print("\nRELATIONS (hasRelation triples):")
        print(f"  New triples added:        {self.stats['relations']['new']}")
        print(f"  Total before this run:    {self.stats['relations']['total_before']}")
        print(f"  Total after this run:     {self.stats['relations']['total_after']}")
        print(f"  Net change:               {self.stats['relations']['total_after'] - self.stats['relations']['total_before']}")
        print("=" * 60 + "\n")


# ----------------------------------------------------------------------
# Command line entry point
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Convert encyclopedia XML articles to RDF Turtle.")
    parser.add_argument("input_dir", help="Directory containing XML files")
    parser.add_argument("output_dir", help="Directory where TTL files will be written")
    args = parser.parse_args()

    converter = XMLToRDFConverter(args.input_dir, args.output_dir)
    converter.process_all_xml()
    converter.save_output()
    converter.print_statistics()


if __name__ == "__main__":
    main()
