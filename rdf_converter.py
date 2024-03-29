from lib import *

# -------------------------- VARS --------------------------------
ARTICLES_DIR = "./results/FMEarticles/"
EXIT_DIR = "./results/FMErdf/"
# Resources links
RESOURCE_CONCEPT = "http://libmeta.ru/thesaurus/528624"
RESOURCE_PERSON = "http://libmeta.ru/resource/person"
RESOURCE_PUBLICATION = "http://libmeta.ru/resource/publication"
RESOURCE_FORMULA = "http://libmeta.ru/resource/Formula"
# Uri prefixes
CORE_URL = "http://libmeta.ru/concept/show/"
CONCEPTS_URI_POSTPREFIX = "fme_"
CONCEPTS_URI_PREFIX = "http://libmeta.ru/thesaurus/concept/"
PERSONS_URI_PREFIX = "http://libmeta.ru/io/Person#"
PUBLICATIONS_URI_PREFIX = "http://libmeta.ru/io/Publication#"
FORMULAS_URI_PREFIX = "http://libmeta.ru/thesaurus/Formula_"
# Filename and uri ranges
CONCEPTS_NUM_RANGE = (1, 99999)
OBJECTS_NUM_RANGE = (1, 99999)
# Option that adds ".xml" file type for automatic highlighting in text editors, `False` by default
XML_FILETYPE = False
# ----------------------------------------------------------------


class Node:
    attrib = {}
    type = ''
    text = ''
    file = ''
    link = ''

    def __init__(self):
        self.contents = []
        self.attrib = {}
        self.type = ''
        self.text = ''
        self.file = ''
        self.link = ''


def add_person(name: str, src_type: str) -> str:
    global objects
    global objects_index
    global doubles_person
    # Split name into parts
    last = ''
    first = ''
    middle = ''
    num = len(name.split(' '))
    if src_type == "art":
        last = name.split(' ')[-1] if num >= 1 else ''
        first = name.split(' ')[0] if num >= 2 else ''
        middle = name.split(' ')[1] if num >= 3 else ''
    if src_type == "lit":
        last = name.split(' ')[0] if num >= 1 else ''
        first = name.split(' ')[1] if num >= 2 else ''
        middle = name.split(' ')[2] if num >= 3 else ''
    # Try to find an existing one
    for index in objects.keys():
        if objects[index].type == "person":
            match = 0
            match += 1 if objects[index].attrib["last"] == last else 0
            match += 1 if objects[index].attrib["first"] == first else 0
            match += 1 if objects[index].attrib["middle"] == middle else 0
            if match >= num:
                doubles_person += 1
                return objects[index].link
    # If not found create a new one
    index = str(objects_index)
    objects_index += 1
    objects[index] = Node()
    objects[index].type = 'person'
    objects[index].attrib["last"] = last
    objects[index].attrib["first"] = first
    objects[index].attrib["middle"] = middle
    objects[index].link = PERSONS_URI_PREFIX + index
    return objects[index].link


def add_publication(node: Node) -> Node:
    global objects
    global objects_index
    global doubles_publication
    # Try to find an existing one
    for index in objects.keys():
        if objects[index].type == "publication":
            match = True
            for author_in in node.attrib["authors"]:
                exist = False
                for author_ref in objects[index].attrib["authors"]:
                    exist = True if author_in.link == author_ref.link else exist
                match = match and exist
            match = False if node.attrib['title'] != objects[index].attrib['title'] else match
            match = False if node.attrib['publication'] != objects[index].attrib['publication'] else match
            match = False if node.attrib['year'] != objects[index].attrib['year'] else match
            match = False if node.attrib['other'] != objects[index].attrib['other'] else match
            if match:
                doubles_publication += 1
                return objects[index]
    # If not found create a new one
    index = str(objects_index)
    objects_index += 1
    node.type = 'publication'
    node.link = PUBLICATIONS_URI_PREFIX + index
    objects[index] = node
    return objects[index]


def add_formula(node: Node) -> Node:
    global objects
    global objects_index
    global doubles_formula
    # Try to find an existing one
    for index in objects.keys():
        if objects[index].type == "formula":
            if node.text == objects[index].text:
                doubles_formula += 1
                return objects[index]
    # If not found create a new one
    index = str(objects_index)
    objects_index += 1
    node.type = "formula"
    node.link = FORMULAS_URI_PREFIX + index
    objects[index] = node
    return objects[index]


def get_ct() -> str:
    ct = datetime.datetime.now(datetime.timezone.utc)
    return f' {ct.day}-{ct.month}-{ct.year} {ct.hour}:{ct.minute} '


def make_person(node: Node) -> ElementTree.Element:
    person_root = ElementTree.Element('rdf:RDF', {'xmlns:rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                                      'xmlns:lbm': 'http://libmeta.ru/'})
    subroot = ElementTree.SubElement(person_root, 'lbm:InformationObject', {'rdf:about': node.link})
    ElementTree.SubElement(subroot, 'lbm:type', {'rdf:resource': RESOURCE_PERSON})
    ElementTree.SubElement(subroot, 'lbm:description')
    person_elem = ElementTree.SubElement(subroot, 'lbm:dateCreated')
    person_elem.text = get_ct()
    person_elem = ElementTree.SubElement(subroot, 'lbm:dateUpdated')
    person_elem.text = get_ct()

    subroot = ElementTree.SubElement(subroot, 'lbm:properties')

    subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute#first'})
    person_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    person_elem.text = node.attrib['first']

    subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute#last'})
    person_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    person_elem.text = node.attrib['last']

    subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute#middle'})
    person_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    person_elem.text = node.attrib['middle']

    """subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    elem = ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource':'http://libmeta.ru/attribute#email'})
    elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    elem.text = ''"""

    return person_root


def make_publication(node: Node) -> ElementTree.Element:
    publication_root = ElementTree.Element('rdf:RDF', {'xmlns:rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                                           'xmlns:lbm': 'http://libmeta.ru/'})
    subroot = ElementTree.SubElement(publication_root, 'lbm:InformationObject', {'rdf:about': node.link})
    ElementTree.SubElement(subroot, 'lbm:type', {'rdf:resource': RESOURCE_PUBLICATION})
    ElementTree.SubElement(subroot, 'lbm:description')
    publication_elem = ElementTree.SubElement(subroot, 'lbm:dateCreated')
    publication_elem.text = get_ct()
    publication_elem = ElementTree.SubElement(subroot, 'lbm:dateUpdated')
    publication_elem.text = get_ct()

    subroot = ElementTree.SubElement(subroot, 'lbm:properties')

    for auth in node.attrib['authors']:
        subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
        ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute#auth'})
        ElementTree.SubElement(subsubroot, 'lbm:value', {'rdf:resource': auth.link})

    """subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute/doi'})
    pub_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    pub_elem.text = ''"""

    """subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute#keywords'})
    pub_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    pub_elem.text = ''"""

    """subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute#lang'})
    pub_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    pub_elem.text = ''"""

    subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute#originalTitle'})
    pub_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    pub_elem.text = node.attrib['title']

    """subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute#udc'})
    pub_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    pub_elem.text = ''"""

    return publication_root


def make_formula(node: Node) -> (ElementTree.Element, str):
    formula_root = ElementTree.Element('rdf:RDF', {'xmlns:rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                                       'xmlns:lbm': 'http://libmeta.ru/'})
    subroot = ElementTree.SubElement(formula_root, 'lbm:InformationObject', {'rdf:about': node.link})
    ElementTree.SubElement(subroot, 'lbm:type', {'rdf:resource': RESOURCE_FORMULA})
    ElementTree.SubElement(subroot, 'lbm:description')
    formula_elem = ElementTree.SubElement(subroot, 'lbm:dateCreated')
    formula_elem.text = get_ct()
    formula_elem = ElementTree.SubElement(subroot, 'lbm:dateUpdated')
    formula_elem.text = get_ct()

    subroot = ElementTree.SubElement(subroot, 'lbm:properties')

    """subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute/simplemathml'})
    formula_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    formula_elem.text = ''"""

    subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute/mathml'})
    ElementTree.SubElement(subsubroot, 'lbm:value')

    subsubroot = ElementTree.SubElement(subroot, 'lbm:property')
    ElementTree.SubElement(subsubroot, 'lbm:type', {'rdf:resource': 'http://libmeta.ru/attribute/tex'})
    formula_elem = ElementTree.SubElement(subsubroot, 'lbm:value')
    formula_elem.text = '$$' + (node.text if node.text is not None else '') + '$$'

    converted2mathml = ''
    # noinspection PyBroadException
    try:
        converted2mathml = tex2mml(node.text)
    except:
        pass
    if converted2mathml is None:
        converted2mathml = ''
    return formula_root, converted2mathml


def make_concept(node: Node, index) -> ElementTree.Element:
    concept_root = ElementTree.Element('rdf:RDF', {'xmlns:rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                                       'xmlns:lbm': 'http://libmeta.ru/', 'xmlns:core': 'http://libmeta.ru/core'})
    subroot = ElementTree.SubElement(concept_root, 'lbm:Concept', {'rdf:about': node.link})
    ElementTree.SubElement(subroot, 'lbm:thesaurus', {'rdf:resource': RESOURCE_CONCEPT})
    concept_elem = ElementTree.SubElement(subroot, 'lbm:code')
    concept_elem.text = node.link[len(CONCEPTS_URI_PREFIX):]
    concept_elem = ElementTree.SubElement(subroot, 'core:url')
    concept_elem.text = CORE_URL + index
    ElementTree.SubElement(subroot, 'lbm:descriptor')
    ElementTree.SubElement(subroot, 'lbm:comment')

    properties_root = ElementTree.SubElement(subroot, 'lbm:properties')

    for auth in node.attrib["authors"]:
        property_elem = ElementTree.SubElement(properties_root, 'lbm:property',
                                               {'rdf:resource':
                                                    'http://libmeta.ru/thesaurus/attribute/author_of_the_article'})
        ElementTree.SubElement(property_elem, 'lbm:value', {'rdf:resource': auth.link})

    """property_elem = ElementTree.SubElement(properties_root, 'lbm:property',
                                           {'rdf:resource': 'http://libmeta.ru/thesaurus/attribute/msc'})
    ElementTree.SubElement(property_elem, 'lbm:value', {'rdf:resource': ''})"""

    """property_elem = ElementTree.SubElement(properties_root, 'lbm:property',
                                           {'rdf:resource': 'http://libmeta.ru/thesaurus/attribute/theme_odu'})
    ElementTree.SubElement(property_elem, 'lbm:value', {'rdf:resource': ''})"""

    for pub in node.attrib["lit"]:
        property_elem = ElementTree.SubElement(properties_root, 'lbm:property',
                                               {'rdf:resource': 'http://libmeta.ru/thesaurus/attribute/lit'})
        ElementTree.SubElement(property_elem, 'lbm:value', {'rdf:resource': pub.link})

    formulas_added = []
    for form in node.attrib["f_main"]:
        if form.link not in formulas_added:
            formulas_added.append(form.link)
            property_elem = ElementTree.SubElement(properties_root, 'lbm:property',
                                                   {'rdf:resource':
                                                        'http://libmeta.ru/thesaurus/attribute/mainFormula'})
            ElementTree.SubElement(property_elem, 'lbm:value', {'rdf:resource': form.link})
    for form in node.attrib["f_aux"]:
        if form.link not in formulas_added:
            formulas_added.append(form.link)
            property_elem = ElementTree.SubElement(properties_root, 'lbm:property',
                                                   {'rdf:resource':
                                                        'http://libmeta.ru/thesaurus/attribute/additonalFormula'})
            ElementTree.SubElement(property_elem, 'lbm:value', {'rdf:resource': form.link})

    property_elem = ElementTree.SubElement(properties_root, 'lbm:property',
                                           {'rdf:resource': 'http://libmeta.ru/thesaurus/attribute/article'})
    ElementTree.SubElement(property_elem, 'lbm:value')

    property_elem = ElementTree.SubElement(properties_root, 'lbm:property',
                                           {'rdf:resource': 'http://libmeta.ru/thesaurus/attribute/original_text'})
    ElementTree.SubElement(property_elem, 'lbm:value')

    relations_added = []
    for relat in node.attrib["relations"]:
        if relat.link not in relations_added:
            relation_elem = ElementTree.SubElement(subroot, 'lbm:familyRelation',
                                                   {'type': 'http://libmeta.ru/relation/family#related'})
            ElementTree.SubElement(relation_elem, 'lbm:value', {'rdf:resource': relat.link})

    return concept_root


def make_link(text: str, link: str, link_type: str) -> str:
    return f'<a href="/{link_type}/show?uri={link}">{text}</a>'


def make_concept_uri(uri: str) -> str:
    return CONCEPTS_URI_PREFIX + CONCEPTS_URI_POSTPREFIX + uri[len(URI_PREFIX) + len("article/"):]


def prepare_texts(node: Node) -> Node:
    text = node.attrib["text"] if node.attrib["text"] is not None else ''

    # Process publications
    if len(node.attrib["lit"]):
        text += '\n\n<i>Лит.</i>: '
    for pub_idx in range(1, len(node.attrib["lit"]) + 1):
        pub = node.attrib["lit"][pub_idx - 1]
        link = make_link(f'[{pub_idx}]', pub.link, 'object')
        text_pos = 0
        while text.find(f'[{pub_idx}]', text_pos) != -1:
            text = text[:text.find(f'[{pub_idx}]', text_pos)] + link +\
                   text[text.find(f'[{pub_idx}]', text_pos)+len(f'[{pub_idx}]'):]
            text_pos = text.find(f'[{pub_idx}]', text_pos)+len(f'[{pub_idx}]')
        text += f'{link} '
        pub_lst = []
        for auth in pub.attrib["authors"]:
            if auth.text != '':
                pub_lst.append(make_link(auth.text, auth.link, 'object'))
        text += str.join(', ', pub_lst) + ', '
        pub_lst = []
        if pub.attrib["title"] is not None and pub.attrib["title"] != '':
            pub_lst.append(pub.attrib["title"])
        if pub.attrib["publication"] is not None and pub.attrib["publication"] != '':
            pub_lst.append(pub.attrib["publication"])
        if pub.attrib["year"] is not None and pub.attrib["year"] != '':
            pub_lst.append(pub.attrib["year"])
        if pub.attrib["other"] is not None and pub.attrib["other"] != '':
            pub_lst.append(pub.attrib["other"])
        text += make_link(str.join(', ', pub_lst), pub.link, 'object') +\
                ('; ' if pub_idx < len(node.attrib["lit"]) else '.')

    # Process authors
    if len(node.attrib["authors"]):
        text += '\n\n'
        auth_lst = []
        for auth in node.attrib["authors"]:
            if auth.text is not None and auth.text != '':
                auth_lst.append(make_link(auth.text, auth.link, 'object'))
        text += '<i>' + str.join(', ', auth_lst) + '.</i>'

    # Process main formulas
    for form in node.attrib["f_main"]:
        link = make_link(f'$${form.text}$$', form.link, 'object')
        pos_start = text.find(form.attrib["uri"])
        if pos_start >= 0:
            pos_end = pos_start
            while text[pos_start:pos_start+2] != '\\[':
                if pos_start == 0:
                    break
                pos_start -= 1
            while text[pos_end-2:pos_end] != '\\]':
                if pos_end == len(text):
                    break
                pos_end += 1
            text = (text[:pos_start] if pos_start > 0 else '') + link + (text[pos_end:] if pos_end < len(text) else '')
    # Process auxiliary formulas
    for form in node.attrib["f_aux"]:
        link = make_link(f'$${form.text}$$', form.link, 'object')
        pos_start = text.find(form.attrib["uri"])
        if pos_start >= 0:
            pos_end = pos_start
            while text[pos_start:pos_start+1] != '$':
                if pos_start == 0:
                    break
                pos_start -= 1
            while text[pos_end-1:pos_end] != '$':
                if pos_end == len(text):
                    break
                pos_end += 1
            text = (text[:pos_start] if pos_start > 0 else '') + link + (text[pos_end:] if pos_end < len(text) else '')

    # Process relations
    for relat in node.attrib["relations"]:
        link = make_link(relat.text, relat.link, 'concept')
        pos_start = text.find(relat.attrib["uri"])
        if pos_start >= 0:
            pos_end = pos_start
            while text[pos_start:pos_start+5] != 'URI[[':
                if pos_start == 0:
                    break
                pos_start -= 1
            while text[pos_end-6:pos_end] != ']]/URI':
                if pos_end == len(text):
                    break
                pos_end += 1
            text = (text[:pos_start] if pos_start > 0 else '') + link + (text[pos_end:] if pos_end < len(text) else '')
            
    paragraphs = text.split('\n\n')
    for p in range(len(paragraphs)):
        paragraphs[p] = f'<P>{paragraphs[p]}<BR/></P>'
    text = str.join('', paragraphs)

    node.attrib["text"] = text
    return node


concepts = {}
concepts_index = CONCEPTS_NUM_RANGE[0]
objects = {}
objects_index = OBJECTS_NUM_RANGE[0]
doubles_person = 0
doubles_publication = 0
doubles_formula = 0


# Prepare directories
deep = 0
for next_dir in EXIT_DIR.split("/"):
    if next_dir not in ('.', ''):
        deep += 1
        os.chdir(next_dir)
try:
    os.chdir("concept")
    os.chdir("..")
except FileNotFoundError:
    os.mkdir("concept")
try:
    os.chdir("object")
    os.chdir("..")
except FileNotFoundError:
    os.mkdir("object")
for i in range(deep):
    os.chdir('..')

# Convert articles into a node tree
filenames = get_filenames(ARTICLES_DIR)
# filenames = filenames[:5]
# filenames = ["13_AVTOKOLEBANI.xml", "29_ADAMARA-PERRONA.xml"]

print("\nScanning articles...")
for filename in tqdm(filenames):
    root = parse_xml(ARTICLES_DIR + filename)
    article = Node()
    article.attrib["uri"] = root.attrib["uri"]
    article.link = make_concept_uri(root.attrib["uri"])
    article.text = get_xml_elem(root, "title").text

    # Extract article authors
    article.attrib["authors"] = []
    elem = get_xml_elem(root, "authors")
    for subelem in elem:
        if subelem.tag == 'author':
            author = Node()
            author.text = subelem.text
            # Check for duplicates
            author.link = add_person(author.text, 'art')
            article.attrib["authors"].append(author)

    # Extract literature
    article.attrib["lit"] = []
    elem = get_xml_elem(root, "literature")
    for subelem in elem:
        if subelem.tag == 'unit':
            unit = Node()
            unit.attrib["authors"] = []
            # Extract authors
            for subsubelem in subelem:
                if subsubelem.tag == 'author':
                    author = Node()
                    author.text = subsubelem.text
                    author.link = add_person(author.text, 'lit')
                    unit.attrib["authors"].append(author)
            # Extract other attributes
            unit.attrib['title'] = get_xml_elem(subelem, 'title').text
            unit.attrib['publication'] = get_xml_elem(subelem, 'publication').text
            unit.attrib['year'] = get_xml_elem(subelem, 'year').text
            unit.attrib['other'] = get_xml_elem(subelem, 'other').text
            # Check for duplicates and add
            article.attrib["lit"].append(add_publication(unit))

    # Extract formulas
    article.attrib["f_main"] = []
    elem = get_xml_elem(root, "formulas_main")
    for subelem in elem:
        if subelem.tag == 'formula':
            formula = Node()
            formula.text = subelem.text
            # Check for duplicates and add
            formula = add_formula(formula)
            formula.attrib["uri"] = subelem.attrib["uri"]
            article.attrib["f_main"].append(formula)
    article.attrib["f_aux"] = []
    elem = get_xml_elem(root, "formulas_aux")
    for subelem in elem:
        if subelem.tag == 'formula':
            formula = Node()
            formula.text = subelem.text
            # Check for duplicates and add
            formula = add_formula(formula)
            formula.attrib["uri"] = subelem.attrib["uri"]
            article.attrib["f_aux"].append(formula)

    # Extract relations
    article.attrib["relations"] = []
    elem = get_xml_elem(root, "relations")
    for subelem in elem:
        if subelem.tag == 'relation':
            relation = Node()
            relation.text = get_xml_elem(subelem, "rel_text").text
            relation.attrib['uri'] = subelem.attrib['uri']
            relation.attrib['tgt'] = get_xml_elem(subelem, 'target').text
            relation.link = make_concept_uri(relation.attrib['tgt'])
            article.attrib["relations"].append(relation)

    # Extract modified text
    article.attrib['text'] = get_xml_elem(root, 'text').text
    # Extract original text
    article.attrib['text_orig'] = get_xml_elem(root, 'text_orig').text

    # Create concepts
    idx = str(concepts_index)
    concepts_index += 1
    concepts[idx] = article

print(f"Total objects: {len(objects)}\n"
      f"Person duplicates found: {doubles_person}\n"
      f"Publication duplicates found: {doubles_publication}\n"
      f"Formula duplicates found: {doubles_formula}\n")

print("\nWriting objects...")
for idx in tqdm(objects.keys()):
    obj = ElementTree.Element('_')
    mml = ''
    if objects[idx].type == 'person':
        obj = make_person(objects[idx])
    elif objects[idx].type == 'publication':
        obj = make_publication(objects[idx])
    elif objects[idx].type == 'formula':
        obj, mml = make_formula(objects[idx])

    xml_out = prettify(obj)
    if objects[idx].type == 'formula':
        xml_out = insert_texts(xml=xml_out,
                               fragment='mathml"/>\n        <lbm:value/>',
                               left_scope='mathml"/>\n        <lbm:value>',
                               right_scope='</lbm:value>',
                               text=mml)
    with codecs.open(EXIT_DIR + 'object/' + idx + ('.xml' if XML_FILETYPE else ''), 'w', 'utf-8') as f:
        f.write(xml_out)

print("\nWriting concepts...")
for idx in tqdm(concepts.keys()):
    concept_node = prepare_texts(concepts[idx])
    obj = make_concept(concept_node, idx)
    xml_out = prettify(obj)

    xml_out = insert_texts(xml=xml_out,
                           fragment='<lbm:descriptor/>',
                           left_scope='<lbm:descriptor><![CDATA[',
                           right_scope=']]></lbm:descriptor>',
                           text=concept_node.text)

    xml_out = insert_texts(xml=xml_out,
                           fragment='attribute/article">\n        <lbm:value/>',
                           left_scope='attribute/article">\n        <lbm:value><![CDATA[',
                           right_scope=']]></lbm:value>',
                           text=concept_node.attrib['text'])

    xml_out = insert_texts(xml=xml_out,
                           fragment='attribute/original_text">\n        <lbm:value/>',
                           left_scope='attribute/original_text">\n        <lbm:value><![CDATA[',
                           right_scope=']]></lbm:value>',
                           text=concept_node.attrib['text_orig'])

    with codecs.open(EXIT_DIR + 'concept/' + idx + ('.xml' if XML_FILETYPE else ''), 'w', 'utf-8') as f:
        f.write(xml_out)


input("\nDone")
