import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import codecs


############################ VARS ################################
INPUT_FILE = 'Labels_53.txt'
CONCEPTS_FILE = '12_UDC_Concepts_53.xml'
RELATIONS_FILE = '14_UDC_Relations_53.xml'
##################################################################



class Article:
	name = ''
	code = ''
	code_parent = ''



# Write xml tree to file
def prettify(elem):
	# Pretty-printed XML string for the Element.
	rough_string = ET.tostring(elem, 'utf-8')
	reparsed = minidom.parseString(rough_string)
	return reparsed.toprettyxml(indent="  ")
def xml_write(root, FILE):
	with codecs.open(FILE[:FILE.find('.xml')] + 'new.xml', 'w', 'utf-8') as f:
		f.write(prettify(root))


def parse_xml(FILE):
	# Parse existing xml (string parsing is needed to avoid extra newlines appearing)
	exit_string = ''
	with codecs.open(FILE, 'r', 'utf-8') as f:
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
	return root
concepts_root = parse_xml(CONCEPTS_FILE)
relations_root = parse_xml(RELATIONS_FILE)


# Add article to xml tree
def add_artice(art):
	global concepts_root
	global relations_root

	article = ET.SubElement(concepts_root, 'taxon', {'uri':'http://libmeta.ru/taxon/udc#'+art.code})
	name = ET.SubElement(article, 'name')
	name.text = art.name
	#name.text = name.text[:-1] if name.text[-1] == '\n' else name.text
	code = ET.SubElement(article, 'code')
	code.text = art.code
	scope = ET.SubElement(article, 'scope')
	scope.text = 'http://libmeta.ru/taxonomy#udc'
	priority = ET.SubElement(article, 'priority')
	priority.text = '1'

	article = ET.SubElement(relations_root, 'taxon', {'uri':'http://libmeta.ru/taxon/udc#'+art.code})
	name = ET.SubElement(article, 'parent')
	name.text = 'http://libmeta.ru/taxon/udc#' + art.code_parent


# Read labels.txt and convert to dict
labels_dict = {}

with codecs.open(INPUT_FILE, 'r', 'utf-8') as f:
	file = f.read().split('\n')

for line in file:
	art = Article()
	if line[:3] == 'УДК':
		art.code = line[4:line.find(' ', 4)]
		art.name = line[line.find(' ', 4)+1:]
	else:
		art.code = line[:line.find(' ')]
		art.name = line[58:]
	#art.name = art.name[:-1] if art.name[-1] == '\n' else art.name
	print(art.code, art.name)
	labels_dict[art.code] = art

# Compute parents and write
for key in labels_dict.keys():
	if key == '53':
		parent = 'UDC'
	else:
		parent = key[:-1]
		while parent not in labels_dict.keys():
			parent = parent[:-1]
	labels_dict[key].code_parent = parent

	add_artice(labels_dict[key])

xml_write(concepts_root, CONCEPTS_FILE)
xml_write(relations_root, RELATIONS_FILE)


# For some reason all names keep write with \n in the end
with codecs.open(CONCEPTS_FILE[:CONCEPTS_FILE.find('.xml')] + 'new.xml', 'r', 'utf-8') as f:
	file = f.read()
while file.find('\n</name>') != -1:
	file = file[:file.find('\n</name>')] + '</name>' + file[file.find('\n</name>')+8:]
with codecs.open(CONCEPTS_FILE[:CONCEPTS_FILE.find('.xml')] + 'new.xml', 'w', 'utf-8') as f:
	f.write(file)

#input()
