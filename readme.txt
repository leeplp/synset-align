To extract the data and obtain the alignments dictionary:
python3.5 dbywt_parser.py
(However, please change the filepaths for DBnary file and Wordnet file in dbywt_parser.py.)

Data files for running dbywt_parser.py:
The wordnet file can be downloaded from http://compling.hss.ntu.edu.sg/omw/wn-multix.db  (~490MB)
The DBnary file (for English) can be downloaded from http://kaiko.getalp.org/static/lemon/latest/en_dbnary_lemon.ttl.bz2
Links to the other language files are found on this page: http://kaiko.getalp.org/about-dbnary/download/

This should output pickled dictionary align-all.p .

=======================================================================================

To run the evaluation (which assumes the file "align-all.p" is in the same directory):
python3.5 evaluator.py

=======================================================================================
Note on language_codes.txt:
This does not contain the full list of language editions of DBnary.

=======================================================================================
References:

For a description of the algorithm, please refer to:

Francis Bond and Ryan Foster (2013)
Linking and extending an open multilingual wordnet. 
In 51st Annual Meeting of the Association for Computational Linguistics: ACL-2013. Sofia. pp 1352–1362