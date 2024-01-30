# 1. Базовый парсер заголовков

# noinspection PyUnresolvedReferences
from os import walk
# noinspection PyUnresolvedReferences
import xml.etree.ElementTree as ElementTree
# noinspection PyUnresolvedReferences
from xml.dom import minidom
# noinspection PyUnresolvedReferences
import re
# noinspection PyUnresolvedReferences
import codecs
# noinspection PyUnresolvedReferences
from lib import *

# -------------------------- VARS --------------------------------
PAGES_DIR = "./matphys/rpages/"
EXIT_DIR = "./matphys/"
EXIT_FILE = "FMEv2.xml"
# First and last pages to be parsed
START_PAGE = 639
END_PAGE = 700
# How many words to display before and after a potential title
LEAD_WORDS = 5
AFT_WORDS = 5
# Look in the description
CAPS_QUOT = 0.51
EXCEPTIONS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'МэВ', 'ГэВ']
# ----------------------------------------------------------------


class Article:
    start_title = 0
    end_title = 0
    filename = ''


# Write xml tree to file
def prettify_1(elem_local: ElementTree.Element) -> str:
    # Pretty-printed XML string for the Element.
    rough_string = ElementTree.tostring(elem_local, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def xml_write_1(root_local: ElementTree.Element):
    with codecs.open(EXIT_DIR + EXIT_FILE, 'w', 'utf-8') as f_out:
        f_out.write(prettify_1(root_local))


# Convert xml excluded symbols
def xml_excluded_convert(text_local: str) -> str:
    for key_local in XML_EXCLUDES.keys():
        while text_local.find(key_local) != -1:
            pos_local = text_local.find(key_local)
            text_local = text_local[:pos_local] + XML_EXCLUDES[key_local] + text_local[pos_local + len(key_local):]
    return text_local


def remove_xml_spaces_1(elem_local: ElementTree.Element) -> ElementTree.Element:
    elem_local.tail = None
    if elem_local.text is not None:
        is_space = True
        for letter in elem_local.text:
            is_space = False if letter != ' ' else is_space
        elem_local.text = None if is_space else xml_excluded_convert(elem_local.text)
    for subelem in elem_local:
        subelem = remove_xml_spaces_1(subelem)
        subelem.tail = None
    return elem_local


def parse_xml_1() -> ElementTree.Element:
    # Parse existing xml (string parsing is needed to avoid extra newlines appearing)
    exit_string = ''
    with codecs.open(EXIT_DIR + EXIT_FILE, 'r', 'utf-8') as f_in:
        for p in f_in.readlines():
            exit_string += p[:-1]
    root_local = ElementTree.fromstring(exit_string)
    # Remove empty tails and texts
    root_local = remove_xml_spaces_1(root_local)
    return root_local


# Add article title and metadata to xml tree
def add_article_1(elem_local: Article) -> int:
    global file
    # Update root in case it's been changed
    elem_root = parse_xml_1()
    elem_num = len(elem_root) + 1
    elem_article = ElementTree.SubElement(elem_root, 'article', {'n': str(elem_num)})
    elem_title = ElementTree.SubElement(elem_article, 'title')
    elem_title.text = file[elem_local.start_title + 1:elem_local.end_title]
    elem_title_meta = ElementTree.SubElement(elem_article, 'title-meta')
    elem_title_file = ElementTree.SubElement(elem_title_meta, 'title-file')
    elem_title_file.text = elem_local.filename
    elem_title_start = ElementTree.SubElement(elem_title_meta, 'title-start')
    elem_title_start.text = str(elem_local.start_title + 1)
    elem_title_end = ElementTree.SubElement(elem_title_meta, 'title-end')
    elem_title_end.text = str(elem_local.end_title)
    xml_write_1(elem_root)
    return elem_num


# Count number of alphabetic letters in word
def count_letters_1(word_local: str) -> int:
    number = 0
    for letter in word_local:
        number += 0 if re.match(r"[A-ZА-Яa-zа-я]", letter) is None else 1
    return number


# Check if word is written in CAPS
def check_caps_1(word_local: str) -> int:
    number = 0
    len_word = 0
    while len(word_local) and re.match(r"[!#$%&'*+-.^_`|~:]", word_local[-1]) is not None:
        word_local = word_local[:-1]
    while len(word_local) and re.match(r"[!#$%&'*+-.^_`|~:]", word_local[0]) is not None:
        word_local = word_local[1:]
    for letter in word_local:
        # Too many symbols, math formulas are being detected:
        # num += 0 if re.match(r"[A-ZА-Я0-9]|[!#$%&'*+-.^_`|~:]", letter) is None else 1
        len_word += 1 if re.match(r"[!#$%&'*+-.^_`|~:]", letter) is None else 0
        number += 0 if re.match(r"[A-ZА-Я]", letter) is None else 1
    # Also exclude common roman numbers:
    return 0 if len_word == 0 or number / len_word < CAPS_QUOT or word_local in EXCEPTIONS else number


# Check for initials like "I.E."
def check_initials_1(word_to_check: str) -> bool:
    initials = True
    for p in range(len(word_to_check) - 1):
        type_1 = 0 if re.match(r"[A-ZА-Яa-zа-я]", word_to_check[p]) is None else 1
        type_2 = 0 if re.match(r"[A-ZА-Яa-zа-я]", word_to_check[p + 1]) is None else 1
        initials = False if type_1 and type_2 else initials
    return initials


# Check if the word is "CM." which happens often
def check_link_1(word_local: str) -> bool:
    word_local = word_local.upper()
    # Convert to cyrillic
    for p in range(len(word_local)):
        word_local = (word_local[:p] + 'С' + word_local[p + 1:]) if word_local[p] == 'C' else word_local
        word_local = (word_local[:p] + 'М' + word_local[p + 1:]) if word_local[p] == 'M' else word_local
    return True if word_local == 'СМ.' else False


# Find next ot prev word boundary (space / newline)
def prev_from_1(position: int, file_name: str) -> int:
    position = max(position, 0)
    prev_space = file_name.rfind(' ', 0, position)
    prev_nl = file_name.rfind('\n', 0, position)
    prev_space = -1 if prev_space == -1 else prev_space
    prev_nl = -1 if prev_nl == -1 else prev_nl
    return max(prev_nl, prev_space)


def next_from_1(position: int, file_name: str, end_replace=True) -> int:
    next_space = file_name.find(' ', position + 1)
    next_nl = file_name.find('\n', position + 1)
    if end_replace:
        next_space = len(file_name) if next_space == -1 else next_space
        next_nl = len(file_name) if next_nl == -1 else next_nl
    return max(next_nl, next_space) if next_space == -1 or next_nl == -1 else min(next_nl, next_space)


file = ''


def run():
    global file
    # Get filenames needed
    filenames_raw = next(walk(PAGES_DIR), (None, None, []))[2]  # [] if no file
    filenames = []
    for i in range(START_PAGE, END_PAGE + 1):
        for filename in filenames_raw:
            beginning = "rp-" + str(i) + "_"
            if filename[:len(beginning)] == beginning and filename[-4:] == ".mmd":
                filenames.append(filename)

    # Check for existing xml
    filenames_raw = next(walk(EXIT_DIR), (None, None, []))[2]  # [] if no file
    if not (EXIT_FILE in filenames_raw):
        root = ElementTree.Element('data')
        xml_write_1(root)

    # Main loop
    for filename in filenames:
        print()
        print("################################ " + filename + " ################################")
        with codecs.open(PAGES_DIR + filename, 'r', 'utf-8') as f:
            file = f.read()

        word_bound_l = -1
        word_bound_r = next_from_1(word_bound_l, file, end_replace=False)
        EOF_reached = False

        while not EOF_reached:
            if word_bound_r == -1:
                word_bound_r = len(file)
                EOF_reached = True

            if check_caps_1(file[word_bound_l + 1:word_bound_r]) < 2 or check_initials_1(
                    file[word_bound_l + 1:word_bound_r]) or check_link_1(file[word_bound_l + 1:word_bound_r]):
                word_bound_l = word_bound_r
                word_bound_r = next_from_1(word_bound_l, file, end_replace=False)

            else:  # Possibly found a title
                # Left border of a title is already known
                start_title = word_bound_l

                # Define right border of a title
                defined_end = False
                end_title = word_bound_r
                while not defined_end:
                    word_bound_l = word_bound_r
                    word_bound_r = next_from_1(word_bound_l, file)

                    if word_bound_l == len(file):
                        defined_end = True
                    elif check_link_1(file[word_bound_l + 1:word_bound_r]):
                        # A "CM." link, not a title
                        pass
                    elif not check_caps_1(file[word_bound_l + 1:word_bound_r]) and count_letters_1(
                            file[word_bound_l + 1:word_bound_r]) < 2:
                        if re.match(r"[A-ZА-Яa-zа-я]", file[word_bound_l + 1]) is not None:
                            # Most possibly belongs to title
                            end_title = word_bound_r
                        else:
                            # Most possibly NOT belongs to title
                            pass
                    elif check_caps_1(file[word_bound_l + 1:word_bound_r]):
                        end_title = word_bound_r
                    else:
                        defined_end = True

                next_title = False
                while not next_title:
                    # Update root in case it's been changed
                    root = parse_xml_1()
                    num = len(root) + 1

                    # Console output for further user actions
                    segment_start = start_title
                    segment_end = end_title
                    for i in range(LEAD_WORDS):
                        segment_start = prev_from_1(segment_start, file)
                    for i in range(AFT_WORDS):
                        segment_end = next_from_1(segment_end, file)

                    out_str = file[segment_start + 1:segment_end]

                    # Format
                    for i in range(len(out_str)):
                        out_str = out_str[:i] + ('$' if out_str[i] == '\n' else out_str[i]) + out_str[i + 1:]
                    out_str = f"{num})\n" + out_str + '\n' + ' ' * (start_title - segment_start) + '^' * (
                            end_title - start_title - 1)
                    # Check for "section" in the string. This is referred to alphabetic tip at the bottom of the page
                    """if 'section' in out_str or 'title' in out_str:
                        out_str += '     ######################### Title or section found! #########################'"""
                    print(out_str)

                    # User actions
                    response = input()
                    # noinspection PyBroadException
                    try:
                        if response == '':
                            # Add article
                            article = Article()
                            article.start_title = start_title
                            article.end_title = end_title
                            article.filename = filename
                            num = add_article_1(article)
                            next_title = True
                            word_bound_l = end_title
                            word_bound_r = next_from_1(word_bound_l, file, end_replace=False)
                            print(f'Adding article, n="{num}", title="{file[start_title + 1:end_title]}"\n\n')
                        elif response == 'n' or response == 'т':
                            # Do not add this one
                            next_title = True
                            print("Not an article, skipping\n\n")
                        elif response[0] == '.':
                            end_title += int(response[1:])
                            print("Changing title right border\n\n")
                        else:
                            # Change title borders
                            corrections = response.split(' ')
                            corrections_0 = int(corrections[0])
                            corrections_1 = int(corrections[1])
                            if corrections_0 > 0:
                                for i in range(abs(corrections_0)):
                                    start_title = prev_from_1(start_title, file)
                            if corrections_0 < 0:
                                for i in range(abs(corrections_0)):
                                    start_title = next_from_1(start_title, file)
                            if corrections_1 < 0:
                                for i in range(abs(corrections_1)):
                                    end_title = prev_from_1(end_title, file)
                            if corrections_1 > 0:
                                for i in range(abs(corrections_1)):
                                    end_title = next_from_1(end_title, file)
                            print("Changing title borders\n\n")
                    except:
                        print("########## !!! Failed on input, try again !!! ##########\n\n")

    # End reached
    print('###########################################################################################')
    print('Last requested page processed. Press "Enter" to close this window.')
    input()


if __name__ == "__main__":
    run()
