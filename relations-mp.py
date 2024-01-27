# 9. Парсер ссылок типа "смотри также"

# -------------------------- VARS --------------------------------
ARTICLES_DIR = "./results/FMEarticles/"
STRICT_SEQUENCING = False  # DEFAULT: False; Links with changed order of words will also be found if False
BRUTE_FORCE_MODE = True  # Maximum amount of links to find, but takes more time (very slow, use with multiprocessing)
USE_MULTIPROCESSING = True  # WARNING: Does not work inside Jupyter!!!; Significantly speeds up scanning process
KEEP_FREE = 0  # Make multiprocessing keep free a specified amount of logic processors, if needed.
# ----------------------------------------------------------------


from lib import *

number_of_processors = max(1, os.cpu_count() - KEEP_FREE)
matches_list = []


# Find previous word beginning - 1 from given position
def find_prev_space(work_text: str, start_pos: int) -> int:
    new_pos = 0
    for sym in ' \n\r':
        new_pos_s = work_text.rfind(sym, 0, start_pos)
        new_pos = max(new_pos, (0 if new_pos_s == -1 else new_pos_s))
    return new_pos


# Find next word ending + 1 from given position
def find_next_space(work_text: str, start_pos: int) -> int:
    new_pos = len(work_text)
    for sym in ' \n\r':
        new_pos_s = work_text.find(sym, start_pos + 1)
        new_pos = min(new_pos, (len(work_text) if new_pos_s == -1 else new_pos_s))
    return new_pos


# Try to find a matching title to the given one
def find_matching_title(sequence_list: list) -> (bool, bool, bool, int):
    match_possible_local = False
    global matches_list
    global titles_list
    # Check with titles from matches list
    for list_pos in range(len(titles_list)):
        if list_pos in matches_list:
            match_local = False
            title_sel = titles_list[list_pos]
            # No match if the title is shorter than the sequence
            if len(title_sel) >= len(sequence_list):
                title_positions = [p for p in range(len(title_sel))]
                len_diff = len(title_positions) - len(sequence_list)
                # Check each word in given sequence
                for p in range(len(sequence_list)):
                    match_current = False
                    # Check if any word form title matches the current word from the sequence
                    for position in title_positions:
                        seq_item = sequence_list[p]
                        if STRICT_SEQUENCING:
                            position = title_positions[0]  # Force straight title words sequencing
                        title_item = title_sel[position]
                        # Try to negotiate word endings
                        seq_len = len(seq_item)
                        title_len = len(title_item)
                        max_len = max(len(title_item), len(seq_item))
                        if seq_len > 5 and title_len > 5 and abs(seq_len - title_len) <= 1:
                            cut_len = min(max_len - 3, 4)
                            seq_item = seq_item[:cut_len]
                            title_item = title_item[:cut_len]
                        # Found matching word
                        if seq_item == title_item:
                            match_current = True
                            title_positions.remove(position)  # Each word from title can be met only once
                            break
                    # If no matching word found then there is no local match
                    if not match_current:
                        break
                match_local = len(title_positions) == len_diff  # Match found for every word in sequence
                match_possible_local = match_possible_local or match_local
            # Remove the title position from matches list if no match for sure
            if not match_local:
                matches_list.remove(list_pos)
            # Exact match for the given sequence
            if match_local and len(title_sel) == len(sequence_list):
                return True, True, True, list_pos

    # If only one local match consider possible solid match where title is longer than the link sequence
    if len(matches_list) == 1:
        return True, True, False, matches_list[0]

    # No solid match found
    return match_possible_local, False, False, -1


# Function for multiprocessing speedup
def loop(filenames_loc: list) -> int:
    global matches_list
    n_loc = 0
    for filename_loc in tqdm(filenames_loc):
        article_loc = parse_xml(ARTICLES_DIR + filename_loc)
        textelem_loc = get_xml_elem(article_loc, 'text')
        text_loc = textelem_loc.text
        n_loc_loc = 0

        if text_loc is not None and len(text_loc):
            # Move along the text from right to left to allow easier uri insertion
            find_right_loc = len(text_loc)
            find_left_loc = find_prev_space(text_loc, find_right_loc)
            _border_left_loc = find_right_loc + 1

            # Find link starting word
            while find_left_loc != -1:
                if check_in_uri(text_loc, find_left_loc):
                    find_right_loc = find_left_loc
                    find_left_loc = find_prev_space(text_loc, find_left_loc) if find_left_loc else -1
                    continue
                word_loc = title_handle_latin(text_loc[find_left_loc:find_right_loc].strip(' \n\r.,;:!?\\()[]{}&'),
                                              COMBINATIONS_CORR_GLOBAL).upper()
                # 'm' can be interpreted both as 'M' and 'T'
                if word_loc == 'СМ' or word_loc == 'СТ' or BRUTE_FORCE_MODE:
                    border_left_loc = find_left_loc if BRUTE_FORCE_MODE else find_right_loc
                    while border_left_loc < len(text_loc) and text_loc[border_left_loc] in ' \n\r.,;:!?\\()[]{}&':
                        border_left_loc += 1
                    if _border_left_loc <= border_left_loc:
                        # Same position as before
                        break
                    border_right_f_loc = border_left_loc
                    _border_right_loc = border_left_loc
                    border_find_allowed_loc = True
                    _match_single_loc = False
                    _match_pos_loc = -1
                    matches_list = [p for p in range(len(titles_list))]
                    _event_parts_len = 0
                    while border_find_allowed_loc:
                        border_right_f_loc = find_next_space(text_loc, border_right_f_loc)
                        border_right_loc = border_right_f_loc
                        while text_loc[border_right_loc - 1] in ' \n\r.,;:!?\\()[]{}&':
                            border_right_loc -= 1
                        if border_right_loc - border_left_loc < 2:
                            _border_left_loc = border_left_loc
                            break
                        border_find_allowed_loc = False if border_right_f_loc == len(text_loc) else True
                        event_loc = title_handle_latin(
                            text_loc[border_left_loc:border_right_loc], COMBINATIONS_CORR_GLOBAL).upper()
                        if event_loc in ['В', 'ПРИ', 'ТАКЖЕ', 'В СТ', 'ПРИ СТ', 'SЕЕАLSО', 'SАMЕАS'] and \
                                not BRUTE_FORCE_MODE:
                            # Starting words continuation
                            continue

                        # Extract word sequence and try to find a matching title from list
                        event_parts_loc = event_loc.split(' ')
                        # Check for punctuation in event
                        if len(event_parts_loc) and len(event_parts_loc[-1]):
                            part_loc = event_parts_loc[-1]
                            for sym in '\n\r\\':
                                if sym in part_loc:
                                    # Severe punctuation
                                    _border_left_loc = border_left_loc
                                    break
                        if len(event_parts_loc) > 1:
                            part_loc = event_parts_loc[-1]
                            if len(part_loc) and (part_loc[0] in '\n\r([{'):
                                # Severe punctuation
                                _border_left_loc = border_left_loc
                                break
                            part_loc = event_parts_loc[-2]
                            if len(part_loc) and (part_loc[0] in '\n\r([{' or part_loc[-1] in ',;:!?\\)]}') \
                                    or (len(part_loc) > 2 and part_loc[-1] == '.'):
                                # Severe punctuation
                                _border_left_loc = border_left_loc
                                break
                        for part_loc in event_parts_loc:
                            if part_loc == '' or part_loc in ' \n\r.,;:!?\\()[]{}&':
                                event_parts_loc.remove(part_loc)
                        if _event_parts_len == len(event_parts_loc):
                            # Nothing new here
                            continue
                        _event_parts_len = len(event_parts_loc)
                        # Check for junk sequences
                        not_junk_loc = 0
                        _not_junk_loc = 0
                        for part_loc in event_parts_loc:
                            _not_junk_loc = not_junk_loc
                            not_junk_loc += 1 if len(part_loc.strip(' \n\r.,;:!?\\()[]{}&')) > 5 else 0
                        if not_junk_loc < 2 and len(event_parts_loc) >= 2:
                            not_junk_loc = 0
                        if _not_junk_loc < 2 and len(event_parts_loc) >= 2:
                            _not_junk_loc = 0

                        (match_possible_loc, match_single_loc, match_exact_loc, match_pos_loc) = find_matching_title(
                            [p.strip(' \n\r.,;:!?\\()[]{}&') for p in event_parts_loc])
                        border_find_allowed_loc = border_find_allowed_loc and match_possible_loc
                        # Remember if single match
                        if match_single_loc:
                            _border_right_loc = border_right_loc
                            _match_pos_loc = match_pos_loc
                        # Consider last single match as exact
                        if (not match_single_loc and _match_single_loc and _not_junk_loc) or (
                                not border_find_allowed_loc and match_single_loc and not_junk_loc):
                            border_right_loc = _border_right_loc
                            match_pos_loc = _match_pos_loc
                            match_exact_loc = True

                        _match_single_loc = match_single_loc
                        # Process exact match
                        if match_exact_loc:
                            _match_single_loc = False
                            # Add an inter-link
                            n_loc_loc += 1
                            uri_pos_us = article_loc.attrib['uri'].find('_')
                            uri_pos_sl = article_loc.attrib['uri'].rfind('/', 0, uri_pos_us)
                            uri_loc = URI_PREFIX + 'relation' + \
                                      article_loc.attrib['uri'][uri_pos_sl:uri_pos_us + 1] + \
                                      str(n_loc_loc) + \
                                      article_loc.attrib['uri'][uri_pos_us:]
                            relations_loc = get_xml_elem(article_loc, 'relations')
                            relation_loc = ElementTree.SubElement(relations_loc, 'relation', {'uri': uri_loc})
                            rel_text_loc = ElementTree.SubElement(relation_loc, 'rel_text')
                            rel_text_loc.text = text_loc[border_left_loc:border_right_loc]
                            rel_tgt_loc = ElementTree.SubElement(relation_loc, 'target')
                            related_article_loc = parse_xml(ARTICLES_DIR + articles_list[match_pos_loc])
                            rel_tgt_loc.text = related_article_loc.attrib['uri']
                            text_loc = text_loc[:border_left_loc] + 'URI[[' + uri_loc + ']]/URI' + text_loc[
                                                                                                   border_right_loc:]
                            # Continue in case of multilink
                            if not BRUTE_FORCE_MODE:
                                border_left_loc += len('URI[[' + uri_loc + ']]/URI')
                                while border_left_loc < len(text_loc) and not text_loc[border_left_loc] in ' \n\r':
                                    border_left_loc += 1
                                border_right_f_loc = border_left_loc
                                matches_list = [p for p in range(len(titles_list))]
                            else:
                                _border_left_loc = border_left_loc
                                break
                        elif not border_find_allowed_loc:
                            _border_left_loc = border_right_loc

                find_right_loc = find_left_loc
                find_left_loc = find_prev_space(text_loc, find_left_loc) if find_left_loc else -1

        # Write xml
        textelem_loc.text = text_loc
        xml_write(article_loc, ARTICLES_DIR + filename_loc)
        n_loc += n_loc_loc

    return n_loc


# Get filenames needed
filenames = get_filenames(ARTICLES_DIR)

# Get all the titles into a list
articles_list = []
titles_list = []
if __name__ != '__main__' or not USE_MULTIPROCESSING:

    # DEBUG                           ###
    # filenames = ["1583_LI.xml", "2471_PUASSONA.xml", "2472_PUASSONA.xml"]
    #####################################
    if __name__ == '__main__':
        print("Preparing search base...")
    for filename in tqdm(filenames):
        article = parse_xml(ARTICLES_DIR + filename)
        title = get_xml_elem(article, 'title').text
        titles_list.append([title_word.upper().strip(' \n\r.,;:!?\\()[]{}&') for title_word in title.split(' ')])
        articles_list.append(filename)

if __name__ == '__main__':

    # DEBUG                           ###
    # filenames = ['3576_JaKOBI.xml']    ###
    #####################################
    print("Searching relations in articles...")
    if USE_MULTIPROCESSING:
        arrays = []
        with Pool(number_of_processors) as pool:
            for i in range(number_of_processors):
                arr_len = len(filenames)
                arr_start = i * (arr_len // number_of_processors)
                arr_end = ((i + 1) * (arr_len // number_of_processors)) if i + 1 < number_of_processors else arr_len
                arrays.append(filenames[arr_start:arr_end])
            n = sum(pool.map(loop, arrays))
    else:
        n = loop(filenames)
    print("Relations found in total:", n)
    if USE_MULTIPROCESSING:
        input()
