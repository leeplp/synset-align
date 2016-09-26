import sys
import pickle
import ds


def uprint(*objects,  sep=' ', end='\n', file=sys.stdout):
    enc = file.encoding
    if enc == 'UTF-8':
        print( *objects, sep=sep, end=end, file=file)
    else:
        f = lambda obj: str(obj).encode(enc, errors='backslashreplace').decode(enc)
        print(*map(f, objects), sep=sep, end=end, file=file)


def loadWiktTranslations():
    with open( "dictWkTrans.p", "rb" ) as f:
        dictWkTrans = pickle.load( f )
        f.close()
    return dictWkTrans

def loadWiktSynonyms():
    with open( "dictWkSynm.p", "rb" ) as f:
        dictWkSynm = pickle.load( f )
        f.close()
    return dictWkSynm

def loadWnTranslations():
    with open( "dictWnTrans.p", "rb" ) as f:
        dictWnTrans = pickle.load( f )
        f.close()
    return dictWnTrans

def loadWiktDefinitions():
    with open( "dictWkDef.p", "rb" ) as f:
        dictWkDef = pickle.load( f )
        f.close()
    return dictWkDef


def dumpWiktTranslations(dictWkTrans):
    with open( "dictWkTrans.p", "wb" ) as f:
        pickle.dump( dictWkTrans, f  )
        f.close()
    return "dictWkTrans.p"

def dumpWiktSynonyms(dictWkSynm):
    with open( "dictWkSynm.p", "wb" ) as f:
        pickle.dump( dictWkSynm, f )
        f.close()
    return "dictWkSynm.p"

def dumpWnTranslations(dictWnTrans):
    with open( "dictWnTrans.p", "wb" ) as f:
        pickle.dump( dictWnTrans, f )
        f.close()
    return "dictWnTrans.p"

def dumpWiktDefinitions(dictWkDef):
    with open( "dictWkDef.p", "wb" ) as f:
        pickle.dump( dictWkDef, f )
        f.close()
    return "dictWkDef.p"

def dumpAlignments(dictAlign, fileName):
    with open(fileName, "wb") as f:
        pickle.dump(dictAlign, f)
        f.close()
    return fileName

def loadAlignments(fileName):
    with open(fileName, "rb") as f:
        dictAlign = pickle.load(f)
        f.close()
    return dictAlign
