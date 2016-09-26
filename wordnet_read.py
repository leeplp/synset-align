import re
import sys
import hashlib
import logging
import log_util as logutil
import gen_utils
from collections import namedtuple
import math
import sqlite3
from gen_utils import uprint
from ds import WnDByTransRecord, WnSenseDef



logger = logging.getLogger(__name__)
logger = logutil.logConfigure(__name__, logFileName="log_wordnet.txt", inputLogLevel="debug")

# Make connection to an SQLite database file
def connect(sqlite_file):
	try:
		conn = sqlite3.connect(sqlite_file)
		return conn
	except sqlite3.Error as e:
		logger.exception("Error %s", e.args[0])
		print("Error "+ e.args[0])
		return None



# Commit changes and close connection to the database
def close(conn):
   # conn.commit()
   if conn:
    conn.close()




def getWnTrans(dbFilePath):
    """ Gets the wordnet translations.  To get the lemma for the synsets,
	    we join two tables: sense, word.
	"""

    conn = connect(dbFilePath)

    dictWnTrans = {}

    if conn:

        sqlString = "SELECT s.synset, w.lemma, w.pos, s.lang "+\
                    "FROM 'sense' s, 'word' w "+\
                    "WHERE s.wordid=w.wordid AND s.lang=w.lang AND s.confidence=1"

        cur = conn.cursor()
        cur.execute(sqlString)
        resList = cur.fetchall()
        if resList:
            logger.info("Number of rows retrieved for WnSenseDef: "+str(len(resList)))
            for i in range(0, len(resList)):
                key, lemma, pos, lang = resList[i]
                if pos=="s":
                    pos = "a"
                newRecord = WnDByTransRecord(lemma=lemma.lower(), pos=pos, lang=lang, ignore=0)
                if key in dictWnTrans:
                    dictWnTrans[key].append(newRecord)
                else:
                    dictWnTrans[key] = [newRecord]
        else:
            logger.debug("Nothing was returned in execution of the SQL query.")
        conn.close()

    close(conn)

    return dictWnTrans


def getWnSenseDefs(dbFilePath):
    """ Gets the wordnet sense definitions.
	"""

    conn = connect(dbFilePath)

    dictWnSenseDef = {}

    if conn:

        sqlString = "SELECT synset, lang, def "+\
                    "FROM synset_def "+\
                    "WHERE lang='eng'"

        cur = conn.cursor()
        cur.execute(sqlString)
        resList = cur.fetchall()
        if resList:
            print("Number of rows retrieved for WnSenseDef: "+str(len(resList)))
            for i in range(0, len(resList)):
                key, lang, definition = resList[i]
                newRecord = WnSenseDef(wncode=key, lang=lang, definition=definition)
                dictWnSenseDef[key] = newRecord
        else:
            logger.debug("Nothing was returned in execution of the SQL query.")

    close(conn)

    return dictWnSenseDef










