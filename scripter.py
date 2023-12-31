# 1. Базовый парсер заголовков

from os import walk
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import codecs


############################ VARS ################################
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
# Symbols excluded in xml have to be converted back
XML_EXCLUDES = {'&quot;' : '"', '&apos;' : "'", '&lt;' : '<',	'&gt;' : '>',	'&amp;' : '&'}
##################################################################



class Article:
	start_title = 0
	end_title = 0
	filename = ''



# Write xml tree to file
def prettify_1(elem:ET.Element) -> str:
	# Pretty-printed XML string for the Element.
	rough_string = ET.tostring(elem, 'utf-8')
	reparsed = minidom.parseString(rough_string)
	return reparsed.toprettyxml(indent="  ")
def xml_write_1(root:ET.Element):
	with codecs.open(EXIT_DIR + EXIT_FILE, 'w', 'utf-8') as f:
		f.write(prettify_1(root))


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
if not(EXIT_FILE in filenames_raw):
	root = ET.Element('data')
	xml_write_1(root)


# Convert xml excluded symbols
def xml_excluded_convert (text:str) -> str:
	for key in XML_EXCLUDES.keys():
		while text.find(key) != -1:
			pos = text.find(key)
			text = text[:pos] + XML_EXCLUDES[key] + text[pos+len(key):]
	return text
def remove_xml_spaces_1(elem:ET.Element) -> ET.Element:
	elem.tail = None
	if elem.text != None:
		is_space = True
		for letter in elem.text:
			is_space = False if letter != ' ' else is_space
		elem.text = None if is_space else xml_excluded_convert(elem.text)
	for subelem in elem:
		subelem = remove_xml_spaces_1(subelem)
	return elem
def parse_xml_1() -> ET.Element:
	# Parse existing xml (string parsing is needed to avoid extra newlines appearing)
	exit_string = ''
	with codecs.open(EXIT_DIR + EXIT_FILE, 'r', 'utf-8') as f:
		for i in f.readlines():
			exit_string += i[:-1]
	root = ET.fromstring(exit_string)
	# Remove empty tails and texts
	root = remove_xml_spaces_1(root)
	return root
root = parse_xml_1()
num = len(root) + 1


# Add article title and metadata to xml tree
def add_artice_1(elem:Article) -> int:
	# Update root in case it's been changed
	root = parse_xml_1()
	num = len(root) + 1
	article = ET.SubElement(root, 'article', {'n':str(num)})
	title = ET.SubElement(article, 'title')
	title.text = file[elem.start_title+1:elem.end_title]
	title_meta = ET.SubElement(article, 'title-meta')
	title_file = ET.SubElement(title_meta, 'title-file')
	title_file.text = elem.filename
	title_start = ET.SubElement(title_meta, 'title-start')
	title_start.text = str(elem.start_title + 1)
	title_end = ET.SubElement(title_meta, 'title-end')
	title_end.text = str(elem.end_title)
	xml_write_1(root)
	return num


# Count number of alphabetic letters in word
def count_letters_1(word:str) -> int:
	num = 0
	for letter in word:
		num += 0 if re.match(r"[A-ZА-Яa-zа-я]", letter) == None else 1
	return num

# Check if word is written in CAPS
def check_caps_1(word:str) -> int:
	num = 0
	len_word = 0
	while len(word) and re.match(r"[!#$%&'*+-.^_`|~:]", word[-1]) != None:
		word = word[:-1]
	while len(word) and re.match(r"[!#$%&'*+-.^_`|~:]", word[0]) != None:
		word = word[1:]
	for letter in word:
		#num += 0 if re.match(r"[A-ZА-Я0-9]|[!#$%&'*+-.^_`|~:]", letter) == None else 1					# Too many symbols, math formulas are being detected
		len_word += 1 if re.match(r"[!#$%&'*+-.^_`|~:]", letter) == None else 0
		num += 0 if re.match(r"[A-ZА-Я]", letter) == None else 1
	return 0 if len_word == 0 or num / len_word < CAPS_QUOT or word in EXCEPTIONS else num				# Also exclude common roman numbers

# Check for initials like "I.E."
def check_initials_1(word:str) -> bool:
	initials = True
	for i in range(len(word) - 1):
		type_1 = 0 if re.match(r"[A-ZА-Яa-zа-я]", word[i]) == None else 1
		type_2 = 0 if re.match(r"[A-ZА-Яa-zа-я]", word[i + 1]) == None else 1
		initials = False if type_1 and type_2 else initials
	return initials

# Check if the word is "CM." which happens often
def check_link_1(word:str) -> bool:
	word = word.upper()
	# Convert to cyrillic
	for i in range(len(word)):
		word = (word[:i] + 'С' + word[i+1:]) if word[i] == 'C' else word
		word = (word[:i] + 'М' + word[i+1:]) if word[i] == 'M' else word
	return True if word == 'СМ.' else False


# Find next ot prev word boundary (space / newline)
def prev_from_1(pos:int, file:str) -> int:
	pos = max(pos, 0)
	prev_space = file.rfind(' ', 0, pos)
	prev_nl = file.rfind('\n', 0, pos)
	prev_space = -1 if prev_space == -1 else prev_space
	prev_nl = -1 if prev_nl == -1 else prev_nl
	return max(prev_nl, prev_space)
def next_from_1(pos:int, file:str, end_replace = True) -> int:
	next_space = file.find(' ', pos + 1)
	next_nl = file.find('\n', pos + 1)
	if end_replace:
		next_space = len(file) if next_space == -1 else next_space
		next_nl = len(file) if next_nl == -1 else next_nl
	return max(next_nl, next_space) if next_space == -1 or next_nl == -1 else min(next_nl, next_space)


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


		if check_caps_1(file[word_bound_l+1:word_bound_r]) < 2 or check_initials_1(file[word_bound_l+1:word_bound_r]) or check_link_1(file[word_bound_l+1:word_bound_r]):
			word_bound_l = word_bound_r
			word_bound_r = next_from_1(word_bound_l, file, end_replace=False)
		
		else: # Possibly found a title
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
				elif check_link_1(file[word_bound_l+1:word_bound_r]):
					# A "CM." link, not a title
					pass
				elif not check_caps_1(file[word_bound_l+1:word_bound_r]) and count_letters_1(file[word_bound_l+1:word_bound_r]) < 2:
					if re.match(r"[A-ZА-Яa-zа-я]", file[word_bound_l+1]) != None:
						# Most possibly belongs to title
						end_title = word_bound_r
					else:
						# Most possibly NOT belongs to title
						pass
				elif check_caps_1(file[word_bound_l+1:word_bound_r]):
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
				
				out_str = file[segment_start+1:segment_end]

				# Format
				for i in range(len(out_str)):
					out_str = out_str[:i] + ('$' if out_str[i] == '\n' else out_str[i]) + out_str[i+1:]
				out_str = f"{num})\n" + out_str + '\n' + ' ' * (start_title - segment_start) + '^' * (end_title - start_title - 1)
				# Check for "section" in the string. This is referred to alphabetic tip at the bottom of the page
				"""if 'section' in out_str or 'title' in out_str:
					out_str += '     ############################### Title or section found! ###############################'""" # Not Used
				print(out_str)

				# User actions
				response = input()
				try:
					if response == '':
						# Add article
						article = Article()
						article.start_title = start_title
						article.end_title = end_title
						article.filename = filename
						num = add_artice_1(article)
						next_title = True
						word_bound_l = end_title
						word_bound_r = next_from_1(word_bound_l, file, end_replace=False)
						print(f'Adding article, n="{num}", title="{file[start_title+1:end_title]}"\n\n')
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
						corrections[0] = int(corrections[0])
						corrections[1] = int(corrections[1])
						if corrections[0] > 0:
							for i in range(abs(corrections[0])):
								start_title = prev_from_1(start_title, file)
						if corrections[0] < 0:
							for i in range(abs(corrections[0])):
								start_title = next_from_1(start_title, file)
						if corrections[1] < 0:
							for i in range(abs(corrections[1])):
								end_title = prev_from_1(end_title, file)
						if corrections[1] > 0:
							for i in range(abs(corrections[1])):
								end_title = next_from_1(end_title, file)
						print("Changing title borders\n\n")
				except:
					print("########## !!! Failed on input, try again !!! ##########\n\n")


# End reached
print('###########################################################################################')
print('Last requested page processed. Press "Enter" to close this window.')
response = input()