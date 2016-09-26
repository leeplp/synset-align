import itertools
import gen_utils as genutils
import collections
import wordnet_read as wn
from ds import *
import re
import random

def getLangs(listTuples):
   langs = [ v.lang for v in listTuples]
   return langs


def getSetLangs(dictListTuples):

    flatList = [item for sublist in list(dictListTuples.values()) for item in sublist]
    langs = sorted(set([vv.lang for vv in flatList]))
    return langs


def getWnStats():
    dictWnTrans2 = genutils.loadWnTranslations()
    dictWnTrans = {}
    for k, v in dictWnTrans2.items():
        if k.endswith("n"):
            pass
        else:
            dictWnTrans[k] = v

    print("Size of wn translations:", len(dictWnTrans))
    print("Size of flat list of translations:", sum([len(v) for v in list(dictWnTrans.values())]))

    # find the set of language codes
    flatList = [item for sublist in list(dictWnTrans.values()) for item in sublist]
    langs = sorted( set( [ vv.lang for vv in flatList] ) )
    #print("Number of languages: ", len(langs))
    #print(langs)

    # get the list of list of langs
    listOfSublists =  [ getLangs(v) for v in list( dictWnTrans.values())  ]
    #print("Number of sublists:", len(listOfSublists))
    #print("First sublist:", listOfSublists[0])

    # get the number of senses, number of synsets for each lang
    counters = [ collections.Counter(v) for v in listOfSublists ]
    #print("counters[0]:", counters[0])
    dictSynsetCounts= {}
    dictSenseCounts=collections.Counter([vv.lang for vv in flatList])
    for lang in langs:
        dictSynsetCounts[lang] = sum([ 1 for counter in counters if (lang in counter) ])
        #print(lang, dictSynsetCounts[lang], dictSenseCounts.get(lang, 0))

    return dictSynsetCounts, dictSenseCounts


def printCounters(dictCounts1, dictCounts2, title):
    print(title)

    keySet = set( list(dictCounts1.keys()) + list(dictCounts2.keys()) )
    for k in sorted(keySet):
        val1 = dictCounts1.get(k, 0)
        val2 = dictCounts2.get(k, 0)
        print(k, ",", val1, ",", val2 )


def getWkLangs(dictWnTrans, dictWkSynm):
    langs = getSetLangs(dictWnTrans)
    srcLang = ""
    for k, v in dictWkSynm.items():
        srcLang = v[0].lang
        if srcLang:
            break
    langs.append(srcLang)
    return list(set(langs))


def getLangNames(filename):
    dictLang={}

    langFile = open(filename, "r", encoding='utf-8')
    for line in langFile:
        lineSplit = re.split("\t", line )
        code = lineSplit[0]; langName= lineSplit[1]
        dictLang[code] = langName
    langFile.close()
    return dictLang

def wnBasedEvaluate():

    dictWnTrans = genutils.loadWnTranslations()
    dictWkTrans = genutils.loadWiktTranslations()
    dictWkSynm = genutils.loadWiktSynonyms()


    StatsRec = collections.namedtuple("StatsRec", "numMatchedVsWn, numMatchedVsWk, "
                                                  "lowerBound, lowerBoundPct, "
                                                  "wnTotal, wkTotal, "
                                                  "recall, precision, "
                                                  "numSynsets, numSenses")
    dictOverlapCounts = {}
    dictSetOverlapCounts = {}
    dictWkCounts = {}
    dictWnCounts = {}
    dictResultStats = {}
    dictWkCountsByDefKey = {}

    #dictSynsetCounts, dictSenseCounts = getWnStats()
    listOfDefKeysAligned = []

    dictAlignments={}
    dictAlignments = genutils.loadAlignments("align-n.p")
    dictv = genutils.loadAlignments("align-v.p")
    dictr = genutils.loadAlignments("align-r.p")
    dicta = genutils.loadAlignments("align-a.p")
    dictAlignments.update(dictv)
    dictAlignments.update(dictr)
    dictAlignments.update(dicta)
    print("Size of dictAlignments:", len(dictAlignments))


    for wncode, alignedList in dictAlignments.items():
        # unpack all the wikt lemmas to a flat merged list
        mergedWktLemmas = []
        for v in alignedList:
            thisList = dictWkSynm.get(v.defkey, []) + dictWkTrans.get(v.defkey, [])
            mergedWktLemmas.extend( thisList )
            listOfDefKeysAligned.append(v.defkey)
            if v.defkey not in dictWkCountsByDefKey:
                dictWkCountsByDefKey[v.defkey] = collections.Counter([lem.lang for lem in thisList ])
        # select the items from the merged list which also
        # occur in the wn list
        # First, get the wn translations
        wnLemmas = dictWnTrans[wncode]
        overlapWkLangs = [lem.lang for lem in mergedWktLemmas if lem in wnLemmas]
        overlapSetWkLangs = [lem.lang for lem in set(mergedWktLemmas) if lem in wnLemmas]
        dictOverlapCounts[wncode] = collections.Counter(overlapWkLangs)
        dictSetOverlapCounts[wncode] = collections.Counter(overlapSetWkLangs)
        dictWkCounts[wncode] = collections.Counter([lem.lang for lem in mergedWktLemmas])
        dictWnCounts[wncode] = collections.Counter([lem.lang for lem in wnLemmas])



    # get the stats by lang based on the languages in wn
    # First, get the langs in wn
    wnLangs = list(getSetLangs(dictWnTrans))
    wkLangs = []   #getWkLangs(dictWkTrans, dictWkSynm)
    allLangs = sorted( set( wnLangs + wkLangs ) )
    print("Number of wkLangs: ", len(wkLangs), sorted(wkLangs))
    print("Number of wnLangs: ",len(wnLangs), sorted(wnLangs) )
    print("Number of allLangs: ",len(allLangs), sorted(allLangs) )

    grandTotalWkOverlaps = sum( [ sum(dictCount.values()) for wncode, dictCount in dictOverlapCounts.items() ])
    grandTotalWk = sum( [ sum(dictCount.values()) for wncode, dictCount in dictWkCounts.items() ])
    grandTotalWn = sum( [ sum(dictCount.values()) for wncode, dictCount in dictWnCounts.items() ])
    for lang in allLangs:
        #numWkSynsets = sum([ 1 for defkey in set(listOfDefKeysAligned) if dictWkCountsByDefKey[defkey].get(lang, 0) > 0 ] )
        numWkSynsets = sum([1 for defkey, dictCount in dictWkCountsByDefKey.items() if dictCount.get(lang, 0) > 0])
        numWkSenses = sum([dictCount.get(lang, 0) for defkey, dictCount in dictWkCountsByDefKey.items()])
        totalMatchedVsWk = sum([dictCount.get(lang, 0) for wncode, dictCount in dictOverlapCounts.items()])
        totalMatchedVsWn = sum([dictCount.get(lang, 0) for wncode, dictCount in dictSetOverlapCounts.items()])
        totalWk = sum([dictCount.get(lang, 0) for wncode, dictCount in dictWkCounts.items()])
        totalWn = sum( [dictCount.get(lang, 0) for wncode, dictCount in dictWnCounts.items()])
        if totalWn > 0:
          recall = float(format(totalMatchedVsWn/totalWn, '.5f'))
        else:
            recall = 0
        if totalWk > 0:
            precision = float(format(totalMatchedVsWk/totalWk, '.5f'))
        else:
            precision = 0

        if grandTotalWk > 0:
            lowerBound = grandTotalWkOverlaps-totalMatchedVsWk
            lowerBoundPct = float( format(lowerBound/grandTotalWkOverlaps, '.5f'))
        else:
            lowerBound = 0; lowerBoundPct=0
        dictResultStats[lang] = StatsRec(numMatchedVsWn=totalMatchedVsWn,
                                         numMatchedVsWk=totalMatchedVsWk,
                                         lowerBound=lowerBound,
                                         lowerBoundPct=lowerBoundPct,
                                         wnTotal=totalWn,
                                         wkTotal=totalWk,
                                         recall=recall,
                                         precision=precision,
                                         numSynsets=numWkSynsets,
                                         numSenses=numWkSenses)

    dictLangNames = getLangNames("langnames.tab")
    for lang in allLangs:
        v = dictResultStats[lang]
        print(lang, ",", dictLangNames[lang], ",",
                         v.numMatchedVsWn, ",",
                         v.numMatchedVsWk, ",",
                         v.lowerBound, ",",
                         v.lowerBoundPct, ",",
                         v.wnTotal, ",",
                         v.wkTotal, ",",
                         v.recall, ",",
                         v.precision, ",",
                         v.numSynsets, ",",
                         v.numSenses
              )
    return dictAlignments, dictWnTrans, dictWkTrans, dictWkSynm


def printAlignments(dictAlign, dictWnTrans, dictWkTrans, dictWkSynm, filename, numAlign):
    dictWkDef = genutils.loadWiktDefinitions()
    sortedKeys = sorted(dictAlign.keys())
    randomIndx = range(0, numAlign)
    random.seed(12345)
    randomIndx = random.sample(range(0, len(dictAlign)), numAlign)
    fh = open(filename, "w", encoding='utf-8')
    printCount = 0
    for k in randomIndx:
        v = dictAlignments[sortedKeys[k]]
        wncode = sortedKeys[k]
        printCount +=1
        fh.write("Record"+str(printCount)+"  wncode: "+wncode+"\n")
        fh.write(str(dictWnTrans[wncode]).replace("),", "),\n"))
        fh.write("\n")
        for wd in v:
            defkey = wd.defkey
            fh.write(str(wd))
            fh.write("\n")
            fh.write(str(dictWkDef[defkey]))
            fh.write("\n")
            fh.write("Synonyms:")
            fh.write("\n")
            if defkey in dictWkSynm:
                fh.write(str(dictWkSynm[defkey]).replace("),", "),\n"))
            else:
                fh.write("No synonyms\n")
            fh.write("\n")
            fh.write("Translations:"+"\n")
            if defkey in dictWkTrans:
                fh.write(str(dictWkTrans[defkey]).replace("),", "),\n"))
            else:
                fh.write("No translations\n")
            fh.write("\n")
            fh.write("\n")

    fh.close()




# main script from here ----

# get the Wordnet counts for synsets and senses
dictSynsetCounts, dictSenseCounts = getWnStats()
printCounters(dictSynsetCounts, dictSenseCounts, "Lang, WnSynsets, WnSenses")

# get statistics for wn-based alignment evaluation
# assumes that alignment pickled dictionaries in align-n.p, align-r.p,
# align-v.p and align-a.p are in the same directory as the script
dictAlignments, dictWnTrans, dictWkTrans, dictWkSynm = wnBasedEvaluate()
# print out a random sample of the alignments and match stats
printAlignments(dictAlignments, dictWnTrans, dictWkTrans, dictWkSynm, "align-results-sample.txt", 20)










