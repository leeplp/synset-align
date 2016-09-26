from collections import namedtuple


# record structures for DBnary data extraction
TranslationRecord = namedtuple('TranslationRecord',
                               "srcLexEntryKey, headword, pos, srcLangCode, tgtLangCode, gloss, lexId, writtenForm, usage, lineNum, disambSenseList")

LexEntryRecord = namedtuple('LexEntryRecord', 'lemma, lexinfoPos, dbPos, synonymList, senseList')
SenseRecord = namedtuple('SenseRecord', 'lemma, senseId, synonymList, definition, disambTranslationList')
SynonymRecord = namedtuple('SynonymRecord', 'word, lexEntryKey, gloss, lineNum')


# data structures for synset alignment comparisons
DByDefRecord = namedtuple('DByDefRecord', "ignore, srcLang, word, pos, longPos, gloss, longDef, lineNumList")   # key is defkey
WnDByTransRecord = namedtuple('WnDByTransRecord', "lemma, lang, pos, ignore")   # key is wncode or defkey to a list of these records

# data structures for sense alignments
AlignStatsRecord = namedtuple('AlignStatsRecord', "defkey, srcMatch, langMatch, srcMax, langMax, srcPc, langPc, score, isCand")  # key is wncode

# data structure for wordnet sense definition
WnSenseDef = namedtuple('WnSenseDef', "wncode, lang, definition")
