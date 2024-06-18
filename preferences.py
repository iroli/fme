
# -------------------------- НАСТРОЙКИ --------------------------------

# -------------- КОТОРЫЕ СКОРЕЕЕ ВСЕГО НУЖНО ПОМЕНЯТЬ -----------------

# Префикс, использующийся для формирования uri и url в ходе обработки.
# Пример: "http://libmeta.ru/fme/".
GLOBAL_URI_PREFIX = "http://libmeta.ru/fme/"

# Указание на рабочую папку,
# в которую будут помещены предварительный результат разметки заголовков,
# предварительный результат проверки орфографии и т.д.
# Пример: "./matphys/".
GLOBAL_WORK_DIR = "./matphys/"

# Указание на папку, в которую будут записаны результаты,
# такие как файлы размеченных и обработанных заголовков, индивидуальные файлы статей и т.д.
# Пример: "./fme_results/".
GLOBAL_RESULTS_DIR = "./fme_results/"

# Указание на папку с исходными оцифрованными текстами.
# Пример: "rpages/"
# Должна быть расположена внутри GLOBAL_WORK_DIR.
GLOBAL_PAGES_DIR = "rpages/"

# Параметры префиксов ссылок и URI финального преобразования в формат RDF:
# Resources links
RDF_RESOURCE_CONCEPT = "http://libmeta.ru/thesaurus/528624"
RDF_RESOURCE_PERSON = "http://libmeta.ru/resource/person"
RDF_RESOURCE_PUBLICATION = "http://libmeta.ru/resource/publication"
RDF_RESOURCE_FORMULA = "http://libmeta.ru/resource/Formula"
# Uri prefixes
RDF_CORE_URL = "http://libmeta.ru/concept/show/"
RDF_CONCEPTS_URI_POSTPREFIX = "fme_"
RDF_CONCEPTS_URI_PREFIX = "http://libmeta.ru/thesaurus/concept/"
RDF_PERSONS_URI_PREFIX = "http://libmeta.ru/io/Person#"
RDF_PUBLICATIONS_URI_PREFIX = "http://libmeta.ru/io/Publication#"
RDF_FORMULAS_URI_PREFIX = "http://libmeta.ru/thesaurus/Formula_"
# Filename and uri ranges
RDF_CONCEPTS_NUM_RANGE = (1, 99999)
RDF_OBJECTS_NUM_RANGE = (1, 99999)


# -------------- КОТОРЫЕ СКОРЕЕ ВСЕГО НЕ НУЖНО МЕНЯТЬ -----------------

# Указание на папку внутри `WORK_DIR`, содержащую папку с файлами размеченных и обработанных заголовков.
# Пример: "titles/" (по умолчанию).
# Должна быть расположена внутри GLOBAL_RESULTS_DIR.
GLOBAL_TITLES_DIR = "titles/"

# Указание на папку, в которую будут сохранены индивидуальные xml-файлы статей.
# Пример: `"articles/"` (по умолчанию).
# Должна быть расположена внутри GLOBAL_RESULTS_DIR.
GLOBAL_ARTICLES_DIR = "articles/"

# Указание на папку, в которой находятся результаты орфографической обработки текстов статей.
# Пример: "spellcheck/" (по умолчанию).
# Должна быть расположена внутри GLOBAL_RESULTS_DIR.
GLOBAL_SPELLCHECK_DIR = "spellcheck/"

# "Пользовательский" словарь со специфическими именами и терминами.
# Пример: "PWL.txt" (по умолчанию).
# Должен быть расположен внутри GLOBAL_WORK_DIR.
GLOBAL_PERSONAL_WORD_LIST = "PWL.txt"

# Указание на папку, в которой находятся результаты преобразования xml-файлов статей в формат RDF.
# Пример: "rdf/" (по умолчанию).
# Должна быть расположена внутри GLOBAL_RESULTS_DIR.
GLOBAL_RDF_DIR = "rdf/"

# Имя файла для записи предварительных результатов разметки заголовков.
# Пример: "titles-raw.xml".
# Будет расположен внутри GLOBAL_WORK_DIR.
BASE_TITLES_PARSER_OUTPUT_FILE = "titles-raw.xml"

# Имя файла для записи предварительных результата разметки заголовка.
# Пример: "titles-added-manually.xml" (по умолчанию), "titles-raw.xml".
# Будет расположен внутри GLOBAL_WORK_DIR.
SINGLE_TITLE_PARSER_OUTPUT_FILE = "titles-added-manually.xml"

# Имя файла, в который будут записаны результаты предварительной обработки и исправления ошибок в заголовках.
# Пример: "titles-corr.xml" (по умолчанию).
# Будет расположен внутри GLOBAL_WORK_DIR.
TITLES_CHECKER_CORRECTIONS_FILE = "titles-corr.xml"

# Имя файла для записи финального варианта размеченных и обработанных заголовков.
# Пример: "titles-checked.xml" (по умолчанию).
# Будет расположен внутри GLOBAL_WORK_DIR.
CHECKED_TITLES_FILE = "titles-checked.xml"

# Имя файла для хранения кеша назначенных URI.
# Пример: "titles-uri-cache.xml" (по умолчанию).
# Будет расположен внутри GLOBAL_TITLES_DIR.
GLOBAL_URI_CACHE = "titles-uri-cache.xml"

# Имя файла для записи результата слития файлов с обработанными заголовками.
# Пример: "titles-merged.xml" (по умолчанию).
# Будет расположен внутри GLOBAL_RESULTS_DIR.
GLOBAL_MERGED_TITLES_FILE = "titles-merged.xml"

# Имя файла, в который будет записан общий список формул со всех статей.
# Пример: "formulas-extracted.xml" (по умолчанию).
# Будет расположен внутри GLOBAL_RESULTS_DIR.
GLOBAL_EXTRACTED_FORMULAS_FILE = "formulas-extracted.xml"

# Имя файла, в который будут записаны формулы для проверки и оценки.
# Пример: "formulas_check.md" (по умолчанию).
# Будет расположен внутри GLOBAL_WORK_DIR.
GLOBAL_FORMULAS_CHECK_FILE = "formulas-check.md"
