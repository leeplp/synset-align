import bz2
import re
import sys
import hashlib
from collections import namedtuple
import math
import log_util as logutil
import gen_utils
import logging
import wordnet_read as wnparse
import pickle
import datetime
from ds import *


"""global data structures"""
# data structures for storing extraction data
dictTranslations = {}
dictLexEntries = {}
dictSenses = {}
dictSynonyms = {}

# data structures for re-organizing data for
# wordnet-dbnary synset alignment
dictWkTrans = {}    # key is defkey; each record is a list of translations
dictWkDef = {}      # key is defkey; each record is a tuple
dictWkSynm = {}     # key is defkey; each record is a synonym in the source language,
                    # considered as a source language "translation"
dictWnTrans = {}    # key is wncode; each record is a list of the lemmas/translations
                    # belonging to that synset (this represents the data from the
                    # wordnets.

# alignment data structures
dictAlignments = {}   # key is tuple (wncode, defkey) - wordnet-synset-id, wikt-synset-id
dictSelAlignments = {}  # key is wncode



"""constants"""
DBY_LANG_CODES_FILENAME = "language_codes.txt"
LANG_CODE_2CHAR = "en"
LANG_CODE_3CHAR = "eng"
posMap = { 'noun':'n', 'propernoun':'n', 'verb':'v', 'adjective':'a', 'adverb':'r'}

"""global variables"""
srcLangCode3ch = ""
srcLangCode2ch = ""

"""loggers"""
logger=None # general logger




def getTransGloss(ptyValStr, lineNum):
    """Gets the short gloss from the dbnary:gloss property
    in a translation record.
    """
    # Gloss is found within double quotes.
    result = re.search('\"(.*)\"', ptyValStr)
    if result :
        gloss = result.group(1)
        return gloss

    logger.debug("Error: search pattern not found for dbnary:gloss: line %d+ ptyValStr: %s", lineNum, ptyValStr)
    return ""


def getTransInfoItems(ptyValStr, lineNum):
    """Gets the headword, POS, headword-POS id from
    the dbnary:isTranslationOf property of a translation record.
    """
    # Search for string prefixed by source language code
    # String is suffixed by space and semi-colon.
    pattern = srcLangCode3ch+":(\S+)\s+;"
    result = re.search(pattern, ptyValStr)
    if result:
        extResult = result.group(1)
        items = re.split("_{2,}", extResult)
        if len(items) == 3:
            headword = items[0]
            pos = items[1]
            id = items[2]    # Note: changed the data type of id from int to str
            srcLexEntryKey = srcLangCode3ch+":"+extResult
            return srcLexEntryKey, headword, pos, id
    httpResult = re.search("<http:", ptyValStr)
    if httpResult:
        logger.debug("Warning: ptyValStr at line %d+ is a URL: %s", lineNum, ptyValStr)
    else:
        logger.debug("Error in splitting ptyValStr at line %d+ ptyValStr:%s", lineNum, ptyValStr)
    return "", "", 0, ""


def getTransUsage(ptyValStr, lineNum):
    """Gets the usage info (includes gender, transliteration, script)
       from the dbnary:usage property of the Translation record.
    """
    # String is found between double quotes.
    result = re.search('\"(.*)\"', ptyValStr)
    extResult = result.group(1)
    if extResult:
        return extResult
    logger.debug("Error: search pattern not found for dbnary:usage: line %d+ ptyValStr: %s", lineNum, ptyValStr)
    return ""


def getTransWrittenForm(ptyValStr, lineNum):
    """Gets the writtenForm info from the dbnary:writtenForm property value field
    of the Translation record."""
    # String is found between double quotes
    result = re.search('\"(.*)\"', ptyValStr)
    if result :
        extResult = result.group(1)
        if extResult :
            return extResult
    logger.debug("Error: search pattern not found for dbnary:writtenForm: line %d+ ptyValStr: %s", lineNum, ptyValStr)
    return ""


def getTransLanguage(ptyValStr, lineNum):
    """Gets the 3-char target language code from the dbnary:targetLanguage
    property of the Translation record
    """
    # target language is prefixed by lexvo:
    result = re.search('lexvo:(.*)\s+;', ptyValStr)
    extResult = result.group(1)
    if extResult :
        return extResult
    logger.debug("Error: search pattern not found for dbnary:targetLanguage: line %d+ ptyValStr: %s", lineNum, ptyValStr)
    return ""


def getSHA1DefKey(langCode, word, pos, shortGloss):
    """returns the SHA1 hash for defkey made up of info items from a translation record:
       language code, headword, POS, and short gloss"""
    hashInpStr = langCode+"-"+word+"-"+pos+"-"+shortGloss
    hashObject = hashlib.sha1( hashInpStr.encode(encoding='utf-8') )
    hashkey = hashObject.hexdigest()
    return hashkey


def saveTransRecord(key, srcLexEntryKey, headword, pos, tgtLangCode, gloss, lexId, usage, writtenForm, firstLineNum):
    """save a translation record in dictionary, with record key being the SHA1 hash of
       info items of the record: target language code, headword, POS, short gloss"""
    global dictTranslations
    global srcLangCode3ch

    if not key :
        logger.debug("Error: Key is null: line %d+", firstLineNum)
        return None
    if key in dictTranslations.keys():
       logger.debug("Error: Translation key found: key:%s lineNumList:%s", key, dictTranslations[key].lineNum)
    else:
       rec = TranslationRecord(srcLexEntryKey=srcLexEntryKey,
                               headword=headword, pos=pos,
                               srcLangCode=srcLangCode3ch, tgtLangCode=tgtLangCode,
                               gloss=gloss, lexId=lexId,
                               writtenForm=writtenForm, usage=usage,
                               lineNum=firstLineNum,
                               disambSenseList=[])
       dictTranslations[key] = rec




def extractTranslation(buffer, firstLineNum):
    """Extracts the info from a translation record, and
       places the info in a dictionary.  Key is given by
       defkey.
    """
    global dbTransCount

    if len(buffer) <= 1 :
        return None

    if "dbnary:Translation" in buffer[1]:
        # Initialize the record fields
        dbTransCount += 1
        gloss=""; headword=""; pos=""
        lexId=""; usage=""; writtenForm=""
        tgtLang=""
        srcLexEntryKey=""

        transKey = buffer[0].strip()   # DBnary "key" for the translation
        if transKey :
            for i in range(2, len(buffer)): #range(1, len(buffer)):
                line = buffer[i].strip()
                lineParts = re.split("\s+", line)
                ptyName = lineParts[0]
                ptyValStr = " ".join(lineParts[1:])
                if ptyName == "dbnary:gloss":
                    gloss = getTransGloss(ptyValStr, firstLineNum )
                elif ptyName=="dbnary:isTranslationOf":
                    srcLexEntryKey, headword, pos, lexId = getTransInfoItems(ptyValStr, firstLineNum)
                elif ptyName=="dbnary:targetLanguage":
                    tgtLang = getTransLanguage(ptyValStr, firstLineNum)
                elif ptyName=="dbnary:usage":
                    usage = getTransUsage(ptyValStr, firstLineNum)
                elif ptyName=="dbnary:writtenForm":
                    writtenForm = getTransWrittenForm(ptyValStr, firstLineNum)
            saveTransRecord(transKey, srcLexEntryKey, headword, pos, tgtLang, gloss, lexId, usage, writtenForm, firstLineNum)


def saveDByTransRecord(dictToSave, defkey, lemma, shortPos, tgtLang):
    """save a translation record as one item in a list of translations
       addressed by defkey
       """
    newRec = WnDByTransRecord(ignore=0,
                            lemma = lemma,
                            pos=shortPos,
                            lang = tgtLang )
    if defkey not in dictToSave.keys():
        newList = [newRec]
        dictToSave[defkey]=newList
    else:
        if newRec not in dictToSave[defkey]:
            dictToSave[defkey].append(newRec)


def getShortPosHeadword(lexEntryKey):
    global posMap

    leEntry = dictLexEntries.get(lexEntryKey)
    if leEntry is None:
        logger.debug("Error: lexEntryKey is not found: key:%s", lexEntryKey)
        return "?", None
    lexinfoPos = leEntry.lexinfoPos
    # if longPos is not found, default to "?"
    pos = posMap.get(lexinfoPos.lower(), "?")
    headword = leEntry.lemma
    return pos, headword


def saveDByDefRecord(defkey, srcLangCode, word, shortPos, glossDef, longPos, lineNum):
    global dictWkDef

    if defkey not in dictWkDef.keys():
        newRec = DByDefRecord(  ignore=0,
                                #defkey=defkey,
                                srcLang=srcLangCode,
                                word=word,
                                pos=shortPos, longPos=longPos,
                                gloss=glossDef,
                                longDef="",
                                lineNumList=[lineNum])
        dictWkDef[defkey] = newRec
    else:
        record = dictWkDef[defkey]
        numList = record.lineNumList
        numList.append(lineNum)
        dictWkDef[defkey] = record._replace(lineNumList=numList)


def normLemma(lemma):
    """ Normalize lemma for purpose of comparison.
    """
    nLemma = lemma.lower()
    nLemma = re.sub(r"-|_|\(|\)|\[|\]", " ", nLemma)
    nLemma = re.sub(r"\s+", " ", nLemma)
    nLemma = nLemma.strip()
    return nLemma


def makeDByDictionaries():
    global dictTranslations
    global dictWkTrans, dictWkSynm, dictWkDef
    global dictWnTrans

    for k, v in dictTranslations.items():
        shortPos, headword = getShortPosHeadword(v.srcLexEntryKey)
        defkey = getSHA1DefKey(srcLangCode3ch, v.headword, shortPos, v.gloss)
        saveDByTransRecord(dictWkTrans, defkey, normLemma(v.writtenForm), shortPos, v.tgtLangCode)
        if defkey not in dictWkDef:
            normHeadword = normLemma(v.headword)
            saveDByDefRecord(defkey, srcLangCode3ch, normHeadword, shortPos, v.gloss,
                             v.pos, v.lineNum )
            saveDByTransRecord(dictWkSynm, defkey, normHeadword, shortPos, srcLangCode3ch)  # note: add src headword

    for k, v in dictSynonyms.items():
        shortPos, headword = getShortPosHeadword(v.lexEntryKey)
        if headword is None:
            #print("Headword is none: lexEntryKey:", v.lexEntryKey)
            print("Synonym record: ")
            gen_utils.uprint(v)
            continue
        #defkey = getSHA1DefKey(srcLangCode3ch, v.word, shortPos, v.gloss)
        defkey = getSHA1DefKey(srcLangCode3ch, headword, shortPos, v.gloss)
        saveDByTransRecord(dictWkSynm, defkey, normLemma(v.word), shortPos, srcLangCode3ch)
        if defkey not in dictWkDef:
            normWord = normLemma(v.word)
            saveDByDefRecord(defkey, srcLangCode3ch, normWord, shortPos, v.gloss,
                             "", v.lineNum)


def normWnTrans():
    global posMap
    global dictWnTrans

    posValues = posMap.values()
    for k, vlist in dictWnTrans.items():
        normList = []
        if vlist[0].pos not in posValues:
            normList= [ v._replace(pos="?") for v in vlist]
        if vlist[0].pos == "s":
            normList = [ v._replace(pos="a") for v in vlist]

        normList = [ v._replace(lemma=normLemma(v.lemma)) for v in vList]
        dictWnTrans[k] = normList




def getLexEntKey(line, firstLineNum):
    """Get the key from key a lemon:LexicalEntry xxx ."""
    parts = re.split("\s+", line)
    if parts:
        key = parts[0]
    else:
        key = ""
        logger.debug("Error: search pattern not found; LexicalEntry key is not found at line %d+", firstLineNum)
    return key


def getLexEntryDBnaryPos(ptyValStr, firstLineNum):
    """Get the part of speech from dbnary:partOfSpeech field
    for the Lexical Entry"""
    # Search for the string within double quotes
    result = re.search('\"(.*)\"', ptyValStr)
    extResult = result.group(1)
    if extResult :
        pos = extResult    #extResult.lower()
        return pos
    logger.debug("Error: search pattern not found for dbnary:partOfSpeech at line %d+ ptyValStr:%s",
                 firstLineNum, ptyValStr)
    return ""


def getLexEntryLexinfoPos(ptyValStr, firstLineNum):
    """Gets the part of speech from lexinfo:partOfSpeech field
    for the Lexical Entry"""
    # Search for the string prefixed by lexinfo:
    result = re.search('lexinfo:(\S+)\s+', ptyValStr)
    if result:
        extResult = result.group(1)
        if extResult:
            return extResult.lower()
    logger.debug("Error: search pattern not found in line %d+ ptyValStr:%s", firstLineNum, ptyValStr)
    return ""


def getLexEntitySynonyms(ptyValStr, firstLineNum):
    """Gets the synonyms from dbnary:synonym field from either
    LexicalSense or LexicalEntry record"""
    finds = re.findall(':\S+\s', ptyValStr)

    # Synonyms are prefixed by source language code followed by :
    # Here, we only look for the colon.
    # Eliminate all finds that have "/", because these are URLs
    if finds :
        #synonyms = [ (x[1:]).strip() for x in finds[1:] if ("/" not in x) ]
        synonyms = [ (x[1:]).strip() for x in finds if ("/" not in x) ]
        logger.debug("Synonyms for line %d+:%s", firstLineNum, synonyms)
        return synonyms

    logger.debug("Error: search pattern not found for line %d+ ptyValStr:%s", firstLineNum, ptyValStr)
    return []



def getLexEntrySenses(ptyValStr, firstLineNum):
    """Gets the senses from lemon:sense field"""
    #finds = re.findall(':\S+\s', line)
    # note: the senses are separated by " ," and end with " ."
    finds = re.findall('\S+:\S+\s', ptyValStr)

    if finds :  #not empty list
        #[(x, y) for x in [1,2,3] for y in [3,1,4] if x != y]
        # remove first item in finds (this is the fieldname "sense")
        # then, remove the first character of each element in finds (this is the : character)
        ##senses = [ (x[1:]).strip() for x in finds[1:]]
        senses = [ x.strip() for x in finds ]
        logger.debug("Senses for line %d+:%s", firstLineNum, senses)
        return senses
    logger.debug("Error: search pattern not found for line %d+ ptyValStr:%s", firstLineNum, ptyValStr)
    return []


def saveLexEntryRec(key, lemma, lexinfoPos, dbPos, syns, senses):
    """Saves the lexicalEntry record in the dictionary"""
    global dictLexEntries
    if key :
        if key in dictLexEntries.keys():
            logger.debug("Error: key is already found in dictLexEntries: key=%s", key)
        else:
            #dictLexEntries[key]=[dBnaryPos, lexinfoPos, syns, senses]
            #LexEntryRecord = namedtuple('LexEntryRecord', 'word, pos, synonymsList, senses')
            rec = LexEntryRecord(lemma=lemma, lexinfoPos=lexinfoPos, dbPos=dbPos, synonymList=syns, senseList=senses )
            if syns:
                # print("Synonyms present: key is: "+key)
                logger.info("Synonyms found. LexEntry-key: %s Synonyms: %s", key, syns)
            dictLexEntries[key] = rec
    else:
        logger.debug("Error: key is empty")


def getLemmaFromLexEntryKey(key, firstLineNum):
    """Extracts the lemma for lexical entry from the key"""
    parts = re.split("__+", key)
    if parts: # len(parts) > 0 :
       #lemma = re.split(":", parts[0])[1]
       subParts = re.split(":", parts[0])    # : separates lemma from source language code
       if len(subParts) > 1:
           lemma = subParts[1]
           return lemma
    logger.debug("Error: search pattern not found in line %d+ lexEntryKey:%s", firstLineNum, key)
    return ""


def extractLexicalEntry(buffer, firstLineNum):
    """Extracts the record for a LexicalEntry, and
    stores it in dictionary.
    """
    global  lemonLexEntryCount
    global   lexEntryWithSynCount

    if len(buffer) <= 1 :
        return None

    if "lemon:LexicalEntry" in buffer[1]:
        lemonLexEntryCount += 1
        key = buffer[0].strip()
        lemma = getLemmaFromLexEntryKey(key, firstLineNum)
        dbPos = ""; syns = []; senses=[]; lexiPos="";
        for i in range(2, len(buffer)):   #range(1, len(buffer)):
            line = buffer[i]
            lineParts = re.split("\s+", line)
            ptyName = lineParts[0].strip()
            ptyValStr = " ".join(lineParts[1:])
            if ptyName=="dbnary:partOfSpeech":
                dbPos = getLexEntryDBnaryPos(ptyValStr, firstLineNum)
            elif ptyName=="dbnary:synonym":
                lexEntryWithSynCount += 1
                syns = getLexEntitySynonyms(ptyValStr, firstLineNum)
            elif ptyName=="lemon:sense":
                senses = getLexEntrySenses(ptyValStr, firstLineNum)
            elif ptyName=="lexinfo:partOfSpeech":
                lexiPos = getLexEntryLexinfoPos(ptyValStr, firstLineNum)
        saveLexEntryRec(key, lemma, lexiPos, dbPos, syns, senses)


# currently, not in use
def getSenseKey(line, firstLineNum):
    """Gets the key for sense, where the identifying field is lemon:LexicalSense"""
    # look for string that contains __ws as substring
    result = re.search('(__ws\S+)', line)
    if result:
        extResult = result.group(1)
        if extResult:
            key = extResult
            return key
    logger.debug("Error: search pattern is not found in line %d+", firstLineNum)
    return ""

def getSenseId(ptyValStr, firstLineNum):
    """Gets the id for the sense"""
    # search for id within double quotes
    result = re.search('\"(.*)\"', ptyValStr)
    if result:
       extResult = result.group(1)
       if extResult:
           senseId = extResult.lower()
           return senseId
    logger.debug("Error: search pattern not found in line %d+ ptyValStr:%s", firstLineNum, ptyValStr)
    return ""

def getSenseDefinition(ptyValStr, firstLineNum):
    """Gets the definition for the sense"""
    # Search for string within double quotes preceded by tag lemon:value
    result = re.search('lemon:value\s+\"(.+)\"', ptyValStr)
    if result:
        extResult = result.group(1)
        if extResult :
            return extResult
    logger.debug("Error: search pattern not found in line %d+ ptyValStr:%s", firstLineNum, ptyValStr)
    return ""

def saveSenseRec(key, lemma, senseId, syns, definition):
    """Saves the sense record in a dictionary"""
    global dictSenses
    if key:
        if key in dictSenses.keys():
            logger.debug("Error: key is already found in dictSenses: key=%s", key)
        else:
            rec = SenseRecord(lemma=lemma, senseId=senseId, synonymList=syns, definition=definition, disambTranslationList=[])
            dictSenses[key] = rec
    else:
        logger.debug("Error: key is empty string.")


def getLemmaFromSenseKey(key, firstLineNum):
    """Extracts the lemma from the sense key"""
    parts = re.split("__+", key)
    if len(parts) <= 1:
        lemma = ""
        logger.debug("Error: search pattern not found in line %d+ key:%s", firstLineNum, key)
    else:
        subParts = re.split("_", parts[1])
        if len(subParts) > 3:
            lemma = "_".join(subParts[2:])
        elif len(subParts) == 3:
            lemma = subParts[2]
        else:
            lemma = ""
            logger.debug("Error: search pattern not found in line %d+ key:%s subParts:%s",
                         firstLineNum, key, subParts)
    return lemma


def extractLexicalSense(buffer, firstLineNum):
    """Gets a sense record and stores it in a dictionary"""
    global lemonLexSenseCount
    global senseWithSynCount #synsInWsCount

    if len(buffer) <= 1 :
        return None

    if "lemon:LexicalSense" in buffer[1] :
        lemonLexSenseCount +=1 #wdSenseCount +=1
        #key = getWdSenseKey(buffer[0], firstLineNum)
        key = buffer[0].strip()
        lemma = getLemmaFromSenseKey(key, firstLineNum)
        senseId = ""; syns = []; definition="";
        for i in range(2, len(buffer)): #range(1, len(buffer)):
            line = buffer[i]
            lineParts = re.split("\s+", line)
            ptyName = lineParts[0]
            ptyValStr = " ".join(lineParts[1:])
            if ptyName == "dbnary:senseNumber":
                senseId = getSenseId(ptyValStr, firstLineNum)
            elif ptyName == "dbnary:synonym":
                senseWithSynCount += 1  # synsInWsCount += 1
                syns = getLexEntitySynonyms(ptyValStr, firstLineNum)
            elif ptyName == "lemon:definition":
                definition = getSenseDefinition(ptyValStr, firstLineNum)
        saveSenseRec(key, lemma, senseId, syns, definition)


def getSynonymWord(ptyValStr, firstLineNum):
    """extracts the synonym word from the property value field,
    assuming that the property fieldname is rdf:object
    """
    result = re.findall(srcLangCode3ch+":\S+", ptyValStr)
    if result:
        word = result[0][len(srcLangCode3ch)+1:]
        return word
    logger.debug("Error: search pattern not found in line %d+ ptyValStr:%s", firstLineNum, ptyValStr)
    return ""


def getSynonymGloss(ptyValStr, firstLineNum):
    """The short gloss for the synonym is found between double quotes.
    Assumes that the ptyFieldName is dbnary:gloss
    """
    result = re.search("\"(.*)\"", ptyValStr)
    if result:
        gloss = result.group(1)
        return gloss.strip()
    logger.debug("Error: search pattern not found in line %d+ ptyValStr:%s", firstLineNum, ptyValStr)
    return ""

def saveSynonymRec(key, synonym, lexEntryKey, synGloss, lineNum):
    """Saves the synonym record in the dictionary"""
    global dictSynonyms

    if not synonym:
        synonym = ""
        logger.debug("Synonym value is missing.")
    if not lexEntryKey:
        logger.debug("LexEntryKey value is missing.")
    newRec = SynonymRecord(word=synonym, lexEntryKey=lexEntryKey, gloss=synGloss, lineNum=lineNum)
    if key in dictSynonyms.keys():
        logger.debug("Error: synonym key %s is already found in dictSynonyms")
    else:
        dictSynonyms[key]= newRec


def extractSynonymRelation(buf, firstLineNum):
    """Extracts the synonym relation"""
    global synonymRelationsCount
    global srcLangCode3ch

    checkSynm = [ 1  for line in buf if re.search("rdf:predicate\s+dbnary:synonym", line) ]
    if checkSynm:
        synonymRelationsCount+=1
        key = buf[0].strip()
        synonym=""; lexEntryKey=""; synGloss=""
        for i in range(1, len(buf)):
            line = buf[i]
            lineParts = re.split("\s+", line)
            ptyName = lineParts[0]
            ptyValStr = " ".join(lineParts[1:])
            if ptyName == "rdf:object":
                synonym = getSynonymWord(ptyValStr, firstLineNum)
            elif ptyName == "rdf:subject":
                lexEntryKey = re.split("\s+", ptyValStr)[0]
            elif ptyName == "dbnary:gloss":
                synGloss = getSynonymGloss(ptyValStr, firstLineNum)
        if synonym and lexEntryKey.startswith(srcLangCode3ch):
            saveSynonymRec(key, synonym, lexEntryKey, synGloss, firstLineNum)


def getEntries(filePath, testNumLines=math.inf):
    """Extracts the translations, lexical entries, lexical senses
    from the main input file
    """

    global dictTranslations
    global dictLexEntries
    global dictSenses

    global dbTransCount
    global lemonLexEntryCount
    global lemonLexSenseCount

    global lexEntryWithSynCount
    global senseWithSynCount

    global synonymRelationsCount

    global srcLangCode3ch

    try:
        inputFile = bz2.open(filePath, 'rt', encoding='utf-8')
        lineNum = 1
        #testLim = testNumLines #28000000 #200 #28000000 #200  #28000000

        line = inputFile.readline()
        numRec = 0; engCount = 0;  httpCount = 0
        dbTransCount = 0;  lemonLexEntryCount = 0; lemonLexSenseCount = 0
        senseWithSynCount=0; lexEntryWithSynCount=0
        synonymRelationsCount=0
        readLineCount = 1
        while line:
            if line.startswith(srcLangCode3ch) or line.startswith('<http:') :
               #read next lines until a blank line is encountered
               if line.startswith(srcLangCode3ch):
                   engRec = True
                   engCount +=1
               else:
                   engRec = False
                   httpCount +=1
               buf = []
               while line.strip() :
                   buf.append(line.strip())
                   line = inputFile.readline()
                   readLineCount += 1
                   lineNum += 1
               if engRec :
                   reBuf = reOrgBuf2(buf, lineNum-len(buf)+1)
                   extractTranslation(reBuf, (lineNum-len(buf)+1))
                   extractLexicalEntry(reBuf,(lineNum-len(buf)+1))
                   extractLexicalSense(reBuf, (lineNum-len(buf)+1))
                   extractSynonymRelation(reBuf, (lineNum-len(buf)+1))
               numRec += 1
            else:
                if line.rstrip():
                    logger.info("Line %d not processed as record: %s", lineNum, line)
                line=inputFile.readline()
                readLineCount+=1
                lineNum += 1

            if lineNum > testNumLines:
               break

    except IOError as e:
        errno, strerror = e.args
        logger.exception("Exception: I/O error({0}): {1}".format(errno, strerror))
    except ValueError:
        logger.exception("Exception: ValueError: Could not convert data to an integer.")
    except Exception as ex:
        template = "An exception of type {0} occured. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logger.exception("Unexpected error: %s", sys.exc_info()[0])
        logger.exception(message)
    finally:
        if inputFile:
            inputFile.close()

    logger.info("Number of lines read from inputFile: %d", readLineCount)
    logger.info("Number of records processed: %d", numRec)

    logger.info("Number of xxx_records headed by 3-char lang code: %d", engCount)
    logger.info("Number of http_records: %d", httpCount)
    logger.info("Total number of records encountered: %d", (httpCount+engCount))

    logger.info("Number of dbnary:Translation processed: %d", dbTransCount)
    logger.info("Number of LexicalEntries processed: %d", lemonLexEntryCount)
    logger.info("Number of LexicalSenses processed: %d", lemonLexSenseCount)
    logger.info("Number of SynonymRelations processed: %d", synonymRelationsCount)

    logger.info("Number of LexicalEntry records with synonyms: %d", lexEntryWithSynCount)
    logger.info("Number of LexicalSense records with synonyms: %d", senseWithSynCount)
    logger.info("Total number of records with synonyms: %d", (lexEntryWithSynCount+senseWithSynCount))

    logger.info("Number of translations saved: %d", len(dictTranslations))
    logger.info("Number of lexical entries saved: %d", len(dictLexEntries))
    logger.info("Number of lexical senses saved: %d", len(dictSenses))
    logger.info("Number of synonym-relations saved: %d", len(dictSynonyms))


def reOrgBuf2(buf, firstLineNum):
    """Re-organises the record such that the first line has only the record
    identifier and the remaining lines contain the property name and value
    pairs; for consistency in the extraction process.
    """
    if buf :
        firstLineSplit = re.split("\s+", buf[0].strip())
        # Check whether first line has more than 1 non-space substring
        if len(firstLineSplit) > 1:
            line0 = firstLineSplit[0]
            line1 = " ".join(firstLineSplit[1:])
            newBuf = [line0, line1]
            newBuf.extend(buf[1:])
            return newBuf
        return buf   # Buffer does not need to be re-organised
    # print("Error in reOrgBuf2: Line "+str(firstLineNum)+"+: Buffer is empty")
    logger.debug("Record buffer is empty: line %d+", firstLineNum)
    return []


def getSrcLangCodes(filePath, langCodeFile):
    """Returns the 2-char language code from the input file name,
     and the 3-char code from the language codes file
     """

    langCode2Char, langCode3Char = '', ''
    # obtain the 2-char language code from the file name
    split = re.split(r"/|\\", filePath )
    fileName = split[-1]
    if len(fileName) >= 2:
        langCode2Char = fileName[0:2]
    else:
        logger.debug("Error: Cannot find 2-char lang code in input file path/name:%s", fileName)
    # return defaultLangCode2ch, defaultLangCode3ch
    if not langCode2Char :
        return LANG_CODE_2CHAR, LANG_CODE_3CHAR

    # Read in the language codes file to obtain the 3-char code
    # given the 2-char code.
    try:
        codeFile = open(langCodeFile)
        for line in codeFile:
            lineSplit = re.split("\s+", line )
            if langCode2Char == lineSplit[0]:
                langCode3Char = lineSplit[1]
                break
    except Exception as ex :
        # print("Unexpected error:", sys.exc_info()[0])
        template = "An exception of type {0} occured. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        # print(message)
        logger.exception("Unexpected Exception: %s", sys.exc_info()[0])
        logger.exception(message)
    finally:
        if codeFile :
            codeFile.close()

    # Defaults to English codes: eng en
    if not langCode3Char :
        return LANG_CODE_2CHAR, LANG_CODE_3CHAR

    return langCode2Char, langCode3Char



def testPrint(dictToPrint, numRecToPrint, title):
    """test  print out a few dictionary records"""
    printRecCount = 0
    print(title)
    for key in sorted(dictToPrint.keys()):
        printRecCount += 1
        print("Record "+str(printRecCount))
        print("Key: ", end=""); gen_utils.uprint(key)
        print(str(dictToPrint[key]).replace("),", "),\n"))
        print("")
        if printRecCount >= numRecToPrint :
            break


def printTransNonTgtLang():
    """ Prints out the translation records that do not have
        target language codes.
    """
    print("Translations without Target Language Code")
    nonTgts = [ x for x in dictTranslations.keys() if (not dictTranslations[x].tgtLangCode)]
    print("Total records: "+str(len(nonTgts)))
    for key in sorted(nonTgts):
        print("Key: ", end="")
        gen_utils.uprint(key)
        gen_utils.uprint(dictTranslations[key])

def testPrintWkDict(numRecToPrint, title):
    """Prints out the reorganized translation/synonym dictionaries
       designated for alignment with the wordnets.
    """
    global dictWkSynm, dictWkTrans, dictWkDef
    printRecCount = 0
    print(title)
    for key in dictWkDef:
        printRecCount += 1
        print("Record "+str(printRecCount))
        print("Key: ", end=""); gen_utils.uprint(key)
        print("++Synonym translations++")
        if key in dictWkSynm:
            gen_utils.uprint(dictWkSynm[key])
        else:
            print("No synonyms.")
        if key in dictWkTrans:
            print("++Other translations++")
            gen_utils.uprint(dictWkTrans[key])
        else:
            print("No translations.")
        print("++Definition Record++")
        gen_utils.uprint(dictWkDef[key])
        print("****************************")
        print("")
        if printRecCount >= numRecToPrint :
            break



def computeAlignmentStats(wnKeys, defKeys, dictAlignments):
    """
    Computes the statistics for the lemma/translation-count
    similarity matching. Assumes data are already matched
    in POS.
    """
    #global dictAlignments
    global dictWkSynm, dictWkTrans, dictWkDef
    global dictWnTrans

    countRec = 0; testLimit=10

    # get the fieldname index for sorting alignment stats
    isCandIndx = AlignStatsRecord._fields.index("isCand")
    scoreIndx = AlignStatsRecord._fields.index("score")
    srcMatchIndx = AlignStatsRecord._fields.index("srcMatch")

    for wncode in wnKeys:  #dictWnTrans:

        wnPos = dictWnTrans[wncode][0].pos

        wnLemmas = dictWnTrans[wncode]
        srcWnLemmas = [ rec for rec in wnLemmas if rec.lang==srcLangCode3ch ]
        langWnLemmas = [ rec for rec in wnLemmas if rec not in srcWnLemmas ]

        tempStatsList = []

        for defkey in defKeys:  #dictWkDef:

            countRec += 1

            srcMax = 0; langMax=0
            srcPc = 0; langPc = 0

            wkPos = dictWkDef[defkey].pos

            srcWkLemmas = dictWkSynm.get(defkey, [])
            langWkLemmas = dictWkTrans.get(defkey, [])

            srcMatch = len( set(srcWkLemmas).intersection(srcWnLemmas) )
            langMatch = len( set(langWkLemmas).intersection(langWnLemmas) )
            #langMatch = len( set(langWkLemmas).intersection(langWnLemmas) ) + srcMatch

            srcMax = min( len(srcWnLemmas), len(srcWkLemmas) )
            langMax = min( len(langWnLemmas), len(langWkLemmas))
            #langMax = min( len(langWnLemmas)+len(srcWnLemmas), len(langWkLemmas)+len(srcWkLemmas))

            if srcMax > 0:
                srcPc = srcMatch/srcMax
            if langMax > 0:
                langPc = langMatch/langMax


            if (srcMatch > 0) or (langMatch > 0):
                statsRec = AlignStatsRecord(defkey, srcMatch, langMatch, srcMax, langMax, srcPc, langPc, score=0, isCand=0)
                isCand, score = idScoreAlignment(wncode, statsRec)
                if isCand > 0:
                    statsRec = statsRec._replace(score=score, isCand=isCand)
                    tempStatsList.append(statsRec)

            if countRec >= testLimit:
                pass #break

        if tempStatsList:
            # sort list by descending isCand, descending score, and descending srcMatch
            dictAlignments[wncode] = sorted(tempStatsList,
                                             key=lambda x: (-x[isCandIndx], -x[scoreIndx], -x[srcMatchIndx]))

        if countRec >= testLimit:
            pass #break




def pickleDump():
    """
    Pickles the data structures for computing the overlap translation
    statistics.
    """

    global dictWkTrans, dictWkSynm, dictWnTrans, dictWkDef

    with open( "dictWkTrans.p", "wb" ) as f:
        pickle.dump( dictWkTrans, f  )
        f.close()
    with open( "dictWkSynm.p", "wb" ) as f:
        pickle.dump( dictWkSynm, f )
        f.close()
    with open( "dictWnTrans.p", "wb" ) as f:
        pickle.dump( dictWnTrans, f )
        f.close()
    with open( "dictWkDef.p", "wb" ) as f:
        pickle.dump( dictWkDef, f )
        f.close()

    print("Dumps are complete.")

    return None

def testAlignStatsByPos(givenPos, dbyFilePath):
    """
    Tests the computation of the alignment stats, loading
    in the pickled data structures to save on computation
    time. Parameters are testPos ("a", "r", "n", "v"),
    and DBnary filepath.
    """
    global dictWkTrans, dictWkSynm, dictWnTrans, dictWkDef
    global srcLangCode2ch, srcLangCode3ch

    dictAlign = {}
    # path to main input file
    #filePath = '../../dbnary/downloads/en_dbnary_lemon_july.ttl.bz2'
    # name of the file storing the 2-char and 3-char language codes
    #langCodeFile = "language_codes.txt"

    srcLangCode2ch, srcLangCode3ch = getSrcLangCodes(dbyFilePath, DBY_LANG_CODES_FILENAME)
    print("Source language codes: "+srcLangCode2ch+" "+srcLangCode3ch)

    with open( "dictWkTrans.p", "rb" ) as f:   # load the dbnary translations
        dictWkTrans = pickle.load( f )
        f.close()
    with open( "dictWkSynm.p", "rb" ) as f:    # load the dbnary synonyms
        dictWkSynm = pickle.load( f )
        f.close()
    with open( "dictWnTrans.p", "rb" ) as f:    # load the wordnet lemmas
        dictWnTrans = pickle.load( f )
        f.close()
    with open( "dictWkDef.p", "rb" ) as f:      # load the dbnary defintions
        dictWkDef = pickle.load( f )
        f.close()

    # select the keys for the given POS
    defKeys = [ k for k, v in dictWkDef.items() if v.pos==givenPos ]
    wnKeys = [ k for k, v in dictWnTrans.items() if v[0].pos == givenPos]

    print("Size of", givenPos, "wkDefs:", len(defKeys))
    print("Size of", givenPos, "wnTrans:", len(wnKeys))

    computeAlignmentStats(wnKeys, defKeys, dictAlign)

    print("Size of alignment dictionary:", len(dictAlign))

    listOfDefKeys = []; checkSum = 0
    for k, ik in dictAlign.items():
        keysList = [ i[0] for i in ik]
        checkSum += len(keysList)
        listOfDefKeys.extend(keysList)

    print("Number of defkeys aligned:", len(listOfDefKeys))
    print("Number of unique defkeys aligned:", len( set(listOfDefKeys)))

    return dictAlign


def getAlignStatsByPos(givenPos, dbyFilePath):
    """
    Tests the computation of the alignment stats, loading
    in the pickled data structures to save on computation
    time. Parameters are testPos ("a", "r", "n", "v"),
    and DBnary filepath.
    """
    global dictWkTrans, dictWkSynm, dictWnTrans, dictWkDef
    global srcLangCode2ch, srcLangCode3ch

    dictAlign = {}
    # path to main input file
    #filePath = '../../dbnary/downloads/en_dbnary_lemon_july.ttl.bz2'
    # name of the file storing the 2-char and 3-char language codes
    #langCodeFile = "language_codes.txt"

    #srcLangCode2ch, srcLangCode3ch = getSrcLangCodes(dbyFilePath, DBY_LANG_CODES_FILENAME)
    #print("Source language codes: "+srcLangCode2ch+" "+srcLangCode3ch)

    #with open( "dictWkTrans.p", "rb" ) as f:   # load the dbnary translations
    #    dictWkTrans = pickle.load( f )
    #    f.close()
    #with open( "dictWkSynm.p", "rb" ) as f:    # load the dbnary synonyms
    #    dictWkSynm = pickle.load( f )
    #    f.close()
    #with open( "dictWnTrans.p", "rb" ) as f:    # load the wordnet lemmas
    #    dictWnTrans = pickle.load( f )
    #    f.close()
    #with open( "dictWkDef.p", "rb" ) as f:      # load the dbnary defintions
    #    dictWkDef = pickle.load( f )
    #    f.close()

    # select the keys for the given POS
    defKeys = [ k for k, v in dictWkDef.items() if v.pos==givenPos ]
    wnKeys = [ k for k, v in dictWnTrans.items() if v[0].pos == givenPos]

    print("Size of", givenPos, "wkDefs:", len(defKeys))
    print("Size of", givenPos, "wnTrans:", len(wnKeys))

    computeAlignmentStats(wnKeys, defKeys, dictAlign)

    print("Size of alignment dictionary:", len(dictAlign))

    listOfDefKeys = []; checkSum = 0
    for k, ik in dictAlign.items():
        keysList = [ i[0] for i in ik]
        checkSum += len(keysList)
        listOfDefKeys.extend(keysList)

    print("Number of defkeys aligned:", len(listOfDefKeys))
    print("Number of unique defkeys aligned:", len( set(listOfDefKeys)))

    return dictAlign



def identifyCandAlignments():
    """Computes the candidacy value for an alignment"""
    global dictAlignments
    global dictWnTrans, dictWkDef

    isCand = 0
    for k, s in dictAlignments.items():
        # choose candidate based on match stats
        if s.langPc >= 0.7:
            isCand = 1
        if s.srcPc >= 0.5:
            if s.langPc >= 0.5:
                isCand = 1
            if s.langPc >= 0.45 and s.langMatch > 5:
                isCand = 1
        # require that the Wikt source language headword is in the wordnet sense
        if isCand == 1:
            defkey = k[1]; wncode = k[0]
            srcWkHeadword = normLemma(dictWkDef[ defkey ].word)
            srcLang = srcLangCode3ch
            wkPos = posMap.get(dictWkDef[ defkey ].pos, "")
            wkRec = WnDByTransRecord(ignore=0, lemma=srcWkHeadword, pos=wkPos, lang=srcLang)
            if wkRec in dictWnTrans[wncode]:
                isCand = 2

        dictAlignments[k] = s._replace(isCand=isCand)



def scoreCandAlignments():
    """
    Computes the score of the selected candidate
    alignments. Score is based on the match in
    the (non-source language) translations.
    """
    global dictAlignments

    score = 0
    for k, s in dictAlignments.items():
        if s.isCand >= 1:
            if s.langMax > 0:
                score = s.langMatch/math.sqrt(s.langMax)
        dictAlignments[k] = s._replace(score=score)


def idScoreAlignment(wncode, wktuple):
    """ Identifies the kind of candidate, and returns the
    score and candidacy status
    """
    global dictWkDef
    global srcLangCode3ch
    global posMap

    isCand = 0
    if wktuple.langPc >= 0.7:
        isCand = 1
    if wktuple.srcPc >= 0.5:
        if wktuple.langPc >= 0.5:
            isCand = 1
        if wktuple.langPc >= 0.45 and wktuple.langMatch > 5:
            isCand = 1
    # require that the Wikt source language headword is in the wordnet sense
    if isCand == 1:
        defkey = wktuple.defkey
        srcWkHeadword = normLemma(dictWkDef[ defkey ].word)
        srcLang = srcLangCode3ch
        wkPos = dictWkDef[ defkey ].pos #wkPos = posMap.get(dictWkDef[ defkey ].pos, "")
        wkRec = WnDByTransRecord(ignore=0, lemma=srcWkHeadword, pos=wkPos, lang=srcLang)
        if wkRec in dictWnTrans[wncode]:
            isCand = 2

    # compute score
    score = 0
    if isCand >= 1:
        if wktuple.langMax > 0:
            score = wktuple.langMatch/math.sqrt(wktuple.langMax)

    return isCand, score


def selectAlignments():
    """
    Select the best from the candidate alignments,
    where isCand is 2.  In the absence of these candidates,
    it selects the isCand=1 candidates.
    """
    global dictAlignments

    for k, v in dictAlignments.items():
        if v :
            if v[0].isCand > 1 :
                # remove all candidates with isCand=1, in the presence of isCand=2 candidates
                dictAlignments[k] = [ x for x in v if x.isCand > 1]



def extractData(dbyFilePath, wndbFilePath, logLevel="warning", logFileName=""):

    global srcLangCode2ch, srcLangCode3ch
    global logger
    global dictWnTrans
    #global dictWkTranslations
    global DBY_LANG_CODES_FILENAME

    logger = logging.getLogger(__name__)
    # Configure and initialize the logging; default level is set to "warning"
    logger=logutil.logConfigure(loggerName=__name__,
                                inputLogLevel=logLevel,
                                logFileName=logFileName)

    logger.debug("Start Logging!")

    srcLangCode2ch, srcLangCode3ch = getSrcLangCodes(dbyFilePath, DBY_LANG_CODES_FILENAME)
    print("language codes: "+srcLangCode2ch+" "+srcLangCode3ch)
    getEntries(dbyFilePath)

    # test the DBnary extracted data
    testPrint(dictLexEntries, 10, "Testing the Lexical Entries dictionary")
    print()
    testPrint(dictSynonyms, 10, "Testing the synonyms dictionary")
    print()
    testPrint(dictTranslations, 10, "Testing Wk Translations Dictionary")

    # read in the wordnet data from the sql database found at dbFilePath
    dictWnTrans = wnparse.getWnTrans(wndbFilePath)

    testPrint(dictWnTrans, 10, "Wordnet Translations")

    makeDByDictionaries()

    testPrintWkDict(10, "Testing the Wk Dictionaries")

    print("Size of wk Translations:"+str(len(dictWkTrans)))
    print("Size of wk synonyms:"+str(len(dictWkSynm)))
    print("Size of wn senses:"+str(len(dictWnTrans)))
    print("Size of wk lex entries:"+str(len(dictLexEntries)))

    return None

def getAlignStats(dbyFilePath, alignFilePath):
    """
    Compute the dictionary of alignments for all POS
    """
    global dictAlignments
    dictAlignments = {}
    for pos in posMap.values():
        dictAlignments.update(getAlignStatsByPos(pos, dbyFilePath))
    gen_utils.dumpAlignments(dictAlignments, alignFilePath)


def main(dbyFilePath, wndbFilePath, logLevel="warning", logFile="") :
    startTime = datetime.datetime.now()


    extractData(dbyFilePath, wndbFilePath, logLevel, logFile)  # default log to screen and level set to "warning"
    endTime = datetime.datetime.now()

    # pickle the extraction data dictionaries
    pickleDump()
    print("End dump time:", datetime.datetime.now())

    # test the alignment selecting the POS ("a", "v", "r", "n")
    # uses the pickled dump data dictionaries,
    # and pickles the resulting alignment dictionary
    testPos = "r"
    alignDumpFileName="align-r.p"
    dictAlignR=getAlignStatsByPos(testPos, dbyFilePath)


    # get the dictionary of all POS alignments
    # and dumps the alignment dictionary
    alignFileName = "align-all.p"
    getAlignStats(dbyFilePath, alignFileName)

    print("Processing Start time:", startTime)
    print("Processing End time:", endTime)


##### call main() ####

dbyFilePath = "../../dbnary/downloads/en_dbnary_lemon_july.ttl.bz2"
wndbFilePath = "../../data/sqlite_db/wn-multix.db"
main(dbyFilePath, wndbFilePath)











