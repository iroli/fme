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
START_PAGE = 148
END_PAGE = 200
# How many words to display before and after a potential title
LEAD_WORDS = 5
AFT_WORDS = 5
# Look in the description
CAPS_QUOT = 0.51
EXCEPTIONS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'МэВ']
##################################################################



class Article:
	start_title = 0
	end_title = 0
	filename = ''



# Write xml tree to file
def prettify(elem):
	# Pretty-printed XML string for the Element.
	rough_string = ET.tostring(elem, 'utf-8')
	reparsed = minidom.parseString(rough_string)
	return reparsed.toprettyxml(indent="  ")
def xml_write(root):
	with codecs.open(EXIT_DIR + EXIT_FILE, 'w', 'utf-8') as f:
		f.write(prettify(root))


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
	xml_write(root)


# Parse existing xml (string parsing is needed to avoid extra newlines appearing)
exit_string = ''
with codecs.open(EXIT_DIR + EXIT_FILE, 'r', 'utf-8') as f:
	for i in f.readlines():
		exit_string += i[:-1]
root = ET.fromstring(exit_string)
# Remove empty tails and texts
root.tail = None
root.text = None
for i in root:
	i.tail = None
	i.text = None
	for j in i:
		j.tail = None
		is_space = True
		for letter in j.text:
			is_space = False if letter != ' ' else is_space
		j.text = None if is_space else j.text
		for k in j:
			k.tail = None
			is_space = True
			for letter in k.text:
				is_space = False if letter != ' ' else is_space
			k.text = None if is_space else k.text


# Add article title and metadata to xml tree
def add_artice(elem, root, num):
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
	xml_write(root)


# Count number of alphabetic letters in word
def count_letters(word):
	num = 0
	for letter in word:
		num += 0 if re.match(r"[A-ZА-Яa-zа-я]", letter) == None else 1
	return num

# Check if word is written in CAPS
def check_caps(word):
	num = 0
	len_word = 0
	for letter in word:
		#num += 0 if re.match(r"[A-ZА-Я0-9]|[!#$%&'*+-.^_`|~:]", letter) == None else 1					# Too many symbols, math formulas are being detected
		len_word += 1 if re.match(r"[!#$%&'*+-.^_`|~:]", letter) == None else 0
		num += 0 if re.match(r"[A-ZА-Я]", letter) == None else 1
	return 0 if len_word == 0 or num / len_word < CAPS_QUOT or word in EXCEPTIONS else num				# Also exclude common roman numbers

# Check for initials like "I.E."
def check_initials(word):
	initials = True
	for i in range(len(word) - 1):
		type_1 = 0 if re.match(r"[A-ZА-Яa-zа-я]", word[i]) == None else 1
		type_2 = 0 if re.match(r"[A-ZА-Яa-zа-я]", word[i + 1]) == None else 1
		initials = False if type_1 and type_2 else initials
	return initials


# Find next ot prev word boundary (space / newline)
def prev_from(pos, file):
	pos = max(pos, 0)
	prev_space = file.rfind(' ', 0, pos)
	prev_nl = file.rfind('\n', 0, pos)
	prev_space = -1 if prev_space == -1 else prev_space
	prev_nl = -1 if prev_nl == -1 else prev_nl
	return max(prev_nl, prev_space)
def next_from(pos, file, end_replace = True):
	next_space = file.find(' ', pos + 1)
	next_nl = file.find('\n', pos + 1)
	if end_replace:
		next_space = len(file) if next_space == -1 else next_space
		next_nl = len(file) if next_nl == -1 else next_nl
	return max(next_nl, next_space) if next_space == -1 or next_nl == -1 else min(next_nl, next_space)


# Main loop
num = len(root) + 1
for filename in filenames:
	print()
	print("################################ " + filename + " ################################")
	with codecs.open(PAGES_DIR + filename, 'r', 'utf-8') as f:
		file = f.read()
	
	word_bound_l = -1
	word_bound_r = next_from(word_bound_l, file, end_replace=False)
	EOF_reached = False

	while not EOF_reached:
		if word_bound_r == -1:
			word_bound_r = len(file)
			EOF_reached = True


		if check_caps(file[word_bound_l+1:word_bound_r]) < 2 or check_initials(file[word_bound_l+1:word_bound_r]):
			word_bound_l = word_bound_r
			word_bound_r = next_from(word_bound_l, file, end_replace=False)
		
		else: # Possibly found a title
			# Left border of a title is already known
			start_title = word_bound_l

			# Define right border of a title
			defined_end = False
			end_title = word_bound_r
			while not defined_end:
				word_bound_l = word_bound_r
				word_bound_r = next_from(word_bound_l, file)

				if word_bound_l == len(file):
					defined_end = True
				elif not check_caps(file[word_bound_l+1:word_bound_r]) and count_letters(file[word_bound_l+1:word_bound_r]) < 2:
					pass
				elif check_caps(file[word_bound_l+1:word_bound_r]):
					end_title = word_bound_r
				else:
					defined_end = True

			next_title = False
			while not next_title:
				# Console output for further user actions
				segment_start = start_title
				segment_end = end_title
				for i in range(LEAD_WORDS):
					segment_start = prev_from(segment_start, file)
				for i in range(AFT_WORDS):
					segment_end = next_from(segment_end, file)
				
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
				if response == '':
					# Add article
					print(f"Adding article, n=\"{num}\", title=\"{file[start_title+1:end_title]}\"\n\n")
					article = Article()
					article.start_title = start_title
					article.end_title = end_title
					article.filename = filename
					add_artice(article, root, num)
					num += 1
					next_title = True
				elif response == 'n':
					# Do not add this one
					print("Not an article, skipping\n\n")
					next_title = True
				else:
					# Change title borders
					print("Changing title borders\n\n")
					corrections = response.split(' ')
					corrections[0] = int(corrections[0])
					corrections[1] = int(corrections[1])
					if corrections[0] > 0:
						for i in range(abs(corrections[0])):
							start_title = prev_from(start_title, file)
					if corrections[0] < 0:
						for i in range(abs(corrections[0])):
							start_title = next_from(start_title, file)
					if corrections[1] < 0:
						for i in range(abs(corrections[1])):
							end_title = prev_from(end_title, file)
					if corrections[1] > 0:
						for i in range(abs(corrections[1])):
							end_title = next_from(end_title, file)


# End reached
print('###########################################################################################')
print('Last requested page processd. Press "Enter" to close this window.')
response = input()