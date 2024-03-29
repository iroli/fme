# 0. Общий код

# noinspection PyUnresolvedReferences
from os import walk
# noinspection PyUnresolvedReferences
from xml.etree import ElementTree
# noinspection PyUnresolvedReferences
from xml.dom import minidom
# noinspection PyUnresolvedReferences
import re
# noinspection PyUnresolvedReferences
import codecs
# noinspection PyUnresolvedReferences
from transliterate import translit, get_available_language_codes
# noinspection PyUnresolvedReferences
from random import randint
# noinspection PyUnresolvedReferences
import enchant
# noinspection PyUnresolvedReferences
from enchant.checker import SpellChecker
# noinspection PyUnresolvedReferences
from enchant.tokenize import EmailFilter, URLFilter
# noinspection PyUnresolvedReferences
import difflib
# noinspection PyUnresolvedReferences
import itertools
# noinspection PyUnresolvedReferences
from tqdm.auto import tqdm
# noinspection PyUnresolvedReferences
from multiprocessing import Pool
# noinspection PyUnresolvedReferences
import os
# noinspection PyUnresolvedReferences
import datetime
# noinspection PyUnresolvedReferences
from latex2mathml.converter import convert as tex2mml


# Small dictionaries merger
def dict_merge(dict1: dict, dict2: dict) -> dict:
    dict0 = {}
    for key_local in dict1.keys():
        dict0[key_local] = dict1[key_local]
    for key_local in dict2.keys():
        dict0[key_local] = dict2[key_local]
    return dict0


# -------------------------- VARS --------------------------------
# Symbols and combinations that have to be corrected after OCR
COMBINATIONS_CORR_ALPHABET = {
    'A': 'А', 'a': 'а', 'B': 'В', 'b': 'Ь', 'C': 'С', 'c': 'с', 'E': 'Е', 'e': 'е', 'H': 'Н', 'K': 'К', 'M': 'М',
    'O': 'О', 'P': 'Р', 'p': 'р', 'T': 'Т', 'X': 'Х', 'y': 'у', 'x': 'х',
    'U': 'И',
    'u': 'и',
    'r': 'г',
    'N': 'П',
    'n': 'п',
    'm': 'т',
    'Y': 'У',
    # 'S' : 'Я',		# Seems irrelevant
}
COMBINATIONS_CORR_UNICODE = {
    'І': 'I',  # These two "I" are different!
    'ก': 'п',
    '山': 'Ц',
    'כ': 'э',
    'חи': 'пи',
    'प': 'Ч',
    'иั': 'й'
}
COMBINATIONS_CORR_OTHER = {
    ' -': '-',
    '- ': '-',
    '0': 'О',
    '3': 'З',
    '6': 'б',
}
COMBINATIONS_CORR_GLOBAL = dict_merge(COMBINATIONS_CORR_ALPHABET,
                                      dict_merge(COMBINATIONS_CORR_UNICODE, COMBINATIONS_CORR_OTHER))
# Symbols excluded in xml have to be converted back
XML_EXCLUDES = {
    '&quot;': '"',
    '&apos;': "'",
    '&lt;': '<',
    '&gt;': '>',
    '&amp;': '&'
}
PERSONAL_WORD_LIST = "./matphys/PWL.txt"
URI_PREFIX = "http://libmeta.ru/fme/"
# ----------------------------------------------------------------


# Get names of files in given directory
def get_filenames(directory: str) -> list:
    return next(walk(directory), (None, None, []))[2]  # [] if no file


# Write xml tree to file
def prettify(element_tree: ElementTree.Element) -> str:
    # Pretty-printed XML string for the Element.
    rough_string = ElementTree.tostring(element_tree, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def xml_write(element_tree: ElementTree.Element, file_name: str):
    with codecs.open(file_name, 'w', 'utf-8') as f_out:
        f_out.write(prettify(element_tree))


# Convert xml excluded symbols
def xml_excluded_convert(text_to_process: str) -> str:
    for key_local in XML_EXCLUDES.keys():
        while text_to_process.find(key_local) != -1:
            pos_local = text_to_process.find(key_local)
            text_to_process = text_to_process[:pos_local] + XML_EXCLUDES[key_local] + text_to_process[
                                                                                      pos_local + len(key_local):]
    return text_to_process


def remove_xml_spaces(element_tree: ElementTree.Element, file_name: str) -> ElementTree.Element:
    element_tree.tail = None
    if element_tree.text is not None:
        is_space = True
        for letter in element_tree.text:
            is_space = False if letter != ' ' else is_space
        if is_space:
            element_tree.text = None
        else:
            if element_tree.tag == 'text':
                element_tree.text = get_texts(file_name)[0]
            elif element_tree.tag == 'text_orig':
                element_tree.text = get_texts(file_name)[1]
            element_tree.text = xml_excluded_convert(element_tree.text)
    for subelem in element_tree:
        subelem = remove_xml_spaces(subelem, file_name)
        subelem.tail = None  # A dummy action to get item used for pylint
    return element_tree


def parse_xml(file_name: str) -> ElementTree.Element:
    # Parse existing xml (string parsing is needed to avoid extra newlines appearing)
    exit_string = ''
    with codecs.open(file_name, 'r', 'utf-8') as f_in:
        for line in f_in.readlines():
            exit_string += line[:-1]
    et_root = ElementTree.fromstring(exit_string)
    et_root = remove_xml_spaces(et_root, file_name)
    return et_root


# !!!BUG!!! for some reason newlines disappear in texts in parsed xml, so extract article texts manually and replace
def get_texts(file_name: str) -> tuple[str, str]:
    with codecs.open(file_name, 'r', 'utf-8') as f_in:
        file_content = f_in.read()
    text_local = file_content[file_content.find('<text>') + 6:file_content.find('</text>')]
    with codecs.open(file_name, 'r', 'utf-8') as f_in:
        file_content = f_in.read()
    text_orig = file_content[file_content.find('<text_orig>') + 11:file_content.find('</text_orig>')]
    return text_local, text_orig


# Inserts [left_scope + text + right_scope] instead of [fragment] if exists.
# Common use: CDATA insertion
def insert_texts(xml: str, fragment: str, left_scope: str, right_scope: str, text: str) -> str:
    if xml.find(fragment) != -1:
        frag_pos = xml.find(fragment)
        frag_len = len(fragment)
        xml = xml[:frag_pos] + left_scope + (text if text is not None else '') + right_scope +\
              (xml[frag_pos+frag_len:] if ((frag_pos + frag_len) < len(xml)) else '')
    return xml


# Get xml tree element with certain tag name
def get_xml_elem(element: ElementTree.Element, elem_path: str) -> ElementTree.Element:
    tgt = elem_path.split('/')[0]
    for subelem in element:
        if subelem.tag == tgt:
            if elem_path.find('/') != -1:
                return get_xml_elem(subelem, elem_path[elem_path.find('/') + 1:])
            else:
                return subelem
    return element


# Titles handling functions
# Correct preferred combinations and latin letters
def title_handle_latin(new_title: str, HANDLER_COMBINATIONS_CORR: dict) -> str:
    if new_title is None or len(new_title) == 0:
        return ''
    for combi in HANDLER_COMBINATIONS_CORR.keys():
        while new_title.find(combi) != -1:
            new_title = new_title[:new_title.find(combi)] + \
                        HANDLER_COMBINATIONS_CORR[combi] + new_title[new_title.find(combi) + len(combi):]
    return new_title


# Remove bounding symbols
def title_handle_bounding(new_title: str) -> str:
    if new_title is None or len(new_title) == 0:
        return ''
    return new_title.strip("!#%&'*+-.^_`|~:;")


# Merge single-lettered words
def title_handle_merge(new_title: str) -> str:
    if new_title is None or len(new_title) == 0:
        return ''
    new_title = ' ' + new_title + ' '
    for p in range(len(new_title) - 4):
        if (new_title[p] == ' ' or new_title[p] == '№') and new_title[p + 2] == ' ' and new_title[p + 4] == ' ':
            new_title = new_title[:p + 2] + '№' + new_title[p + 3:]
    p = 0
    while p < len(new_title):
        if new_title[p] == '№':
            new_title = new_title[:p] + new_title[p + 1:]
            p = 0
        else:
            p += 1
    while new_title[0] == ' ':
        new_title = new_title[1:]
    while new_title[-1] == ' ':
        new_title = new_title[:-1]
    return new_title


# Revert changes for aux formulas in titles
def title_handle_formulas(new_title: str, old_title: str) -> str:
    if new_title is None or len(new_title) == 0:
        return ''
    pos_old = 0
    pos_new = 0
    while old_title.find('$', pos_old) != -1 and new_title.find('$', pos_new) != -1:
        pos_old = old_title.find('$', pos_old) + 1
        pos_new = new_title.find('$', pos_new) + 1
        pos_old_next = old_title.find('$', pos_old) if old_title.find('$', pos_old) != -1 else len(old_title)
        pos_new_next = new_title.find('$', pos_new) if new_title.find('$', pos_new) != -1 else len(new_title)
        new_title = new_title[:pos_new] + old_title[pos_old:pos_old_next] + new_title[pos_new_next:]
        pos_old = pos_old_next + 1
        pos_new = (new_title.find('$', pos_new) if new_title.find('$', pos_new) != -1 else len(new_title)) + 1
    while new_title[-2:] == '-$' or new_title[-2:] == ',$' or new_title[-2:] == ':$':
        new_title = new_title[:-2] + '$'
    return new_title


# Position checkers
# Checks if given position is between opening and closing scopes
def check_in_scopes(text_to_check: str, pos_to_check: int, opening_scope: str, closing_scope: str) -> bool:
    if text_to_check is None:
        return False
    open_prev = text_to_check.rfind(opening_scope, 0, pos_to_check)
    close_prev = text_to_check.rfind(closing_scope, 0, pos_to_check)
    open_next = text_to_check.find(opening_scope, pos_to_check)
    close_next = text_to_check.find(closing_scope, pos_to_check)
    after_open = True if (
            (open_prev != -1 and close_prev == -1) or (open_prev > close_prev != -1 and open_prev != -1)) else False
    before_close = True if ((open_next == -1 and close_next != -1) or (
            open_next > close_next != -1 and open_next != -1)) else False
    return after_open and before_close


def check_in_uri(text_to_check: str, pos_to_check: int) -> bool:
    return check_in_scopes(text_to_check, pos_to_check, 'URI[[', ']]/URI')


def check_in_link(text_to_check: str, pos_to_check: int) -> bool:
    return check_in_scopes(text_to_check, pos_to_check, '![](', ')')


def check_in_formula(text_to_check: str, pos_to_check: int) -> bool:
    # Main formulas
    in_main = check_in_scopes(text_to_check, pos_to_check, '\\[', '\\]')
    # Aux formulas
    if text_to_check is None:
        return False
    p_find = 0
    cntr = 0
    found_before = 0
    # Count dollar symbols and find target position
    while text_to_check.find('$', p_find) != -1:
        p_find = text_to_check.find('$', p_find)
        cntr += 1
        if not found_before and pos_to_check <= p_find:
            found_before = cntr
        p_find += 1
    # If cnt is not even assume that first one is garbage from title
    in_aux = not ((found_before + cntr) % 2) and found_before > 0
    return in_main or in_aux


# Prepare spellcheckers
ru_dict = enchant.DictWithPWL("ru_RU", PERSONAL_WORD_LIST)
ru_checker = SpellChecker(ru_dict, filters=[EmailFilter, URLFilter])
en_dict = enchant.DictWithPWL("en_US", PERSONAL_WORD_LIST)
en_checker = SpellChecker(en_dict, filters=[EmailFilter, URLFilter])


def spellcheck_dict_update():
    global ru_dict
    global ru_checker
    global en_dict
    global en_checker
    ru_dict = enchant.DictWithPWL("ru_RU", PERSONAL_WORD_LIST)
    ru_checker = SpellChecker(ru_dict, filters=[EmailFilter, URLFilter])
    en_dict = enchant.DictWithPWL("en_US", PERSONAL_WORD_LIST)
    en_checker = SpellChecker(en_dict, filters=[EmailFilter, URLFilter])


# Use PyEnchant spellchecker
def do_spellcheck(text_to_check: str) -> dict:
    global ru_dict
    global ru_checker
    global en_dict
    global en_checker
    dictionaries = [ru_dict, en_dict]
    checkers = [ru_checker, en_checker]
    text_suggestions_local = dict()

    # Spellcheck
    for p in range(len(checkers)):
        checker = checkers[p]
        dictionary = dictionaries[p]

        checker.set_text(text_to_check)
        for woi in checker:
            # Exclude some wois to reduce computation time and output
            if check_in_uri(text_to_check, woi.wordpos) or check_in_link(text_to_check, woi.wordpos) or \
                    check_in_formula(text_to_check, woi.wordpos) or len(woi.word) < 4 or \
                    woi.wordpos in text_suggestions_local.keys() or \
                    text_to_check[min(woi.wordpos + len(woi.word), len(text_to_check) - 1)] in ['.']:
                continue
            # Ignore "...x- x..." cases
            if woi.wordpos >= 3 and text_to_check[woi.wordpos - 1] == ' ' and \
                    text_to_check[woi.wordpos - 2] == '-' and text_to_check[woi.wordpos - 3] != ' ':
                continue
            if woi.wordpos + len(woi.word) + 2 < len(text_to_check) and \
                    text_to_check[woi.wordpos + len(woi.word)] == '-' and \
                    text_to_check[woi.wordpos + len(woi.word) + 1] == ' ' and \
                    text_to_check[woi.wordpos + len(woi.word) + 2] != ' ':
                continue
            # Check if word is correct in some other language
            word_is_correct_in_other_dict = False
            for _dictionary in dictionaries:
                word_is_correct_in_other_dict = True if _dictionary.check(woi.word) else word_is_correct_in_other_dict
            if word_is_correct_in_other_dict:
                continue
            # Generate a suggestion
            sim = dict()
            word_suggestions = set(dictionary.suggest(woi.word))
            for word_local in word_suggestions:
                measure = difflib.SequenceMatcher(None, woi.word, word_local).ratio()
                if len(woi.word) == len(word_local):
                    measure += 2.0  # Give priority to length-constant suggestions (i.e. with no extra whitespaces)
                    cnt_err = 0
                    cnt_err_sel = 0
                    for letter in range(len(word_local)):
                        if woi.word[letter] != word_local[letter]:
                            cnt_err += 1
                            if (woi.word[letter] == 'ш' or woi.word[letter] == 'щ') and (
                                    word_local[letter] == 'ш' or word_local[letter] == 'щ'):
                                cnt_err_sel += 1
                    measure += 2.0 if cnt_err == cnt_err_sel else 0.0  # Give even more priority in "ш-щ" case
                # Write measure
                sim[measure] = word_local
            suggest = sim[max(sim.keys())] if len(sim.keys()) else None
            # Exclude some wois to reduce computation time and output
            if suggest is None or suggest == woi.word:
                continue
            else:
                text_suggestions_local[woi.wordpos] = (woi.word, suggest)

    return text_suggestions_local


def add_to_pwl(word_to_add: str):
    with codecs.open(PERSONAL_WORD_LIST, 'r', 'utf-8') as f_in:
        pwl = f_in.read()
    if pwl.find(f"\n{word_to_add}\n") == -1:
        with codecs.open(PERSONAL_WORD_LIST, 'a', 'utf-8') as f_out:
            f_out.write(f"{word_to_add.strip()}\n")
