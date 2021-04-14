# eng.finegrained-loc

This data is based on the English data of the  CoNLL-2003 NER shared 
task (Tjong et al.: Introduction to the conll-2003 shared task: 
Language-independent named entity recognition, 2003).

All location labels (LOC) are labeled with more specific, fine-grained labels, 
namely CITY, COUNTRY, CONTINENT and OTHER. The BIO-2 schema was used.

CITY includes both cities and towns, but not regions or parts of a city.

COUNTRY includes existing countries as well as proposed countries (Republic
of Padania) and no longer existing countries. Countries or states
that are part of larger countries were labeled as OTHER (e.g.
the state of Florida as part of the USA or England as part of the UK). 
City-states were labeled as countries (e.g. the Vatican).

Tokens that were incorrectly labeled in the original CoNLL data as location
were labeled as OTHER to keep consistent and exactly relabel all the LOC
labels (e.g. the token "Let's" and the token "Santander" which referred to
the bank and not the city).

Apart from the already mentioned cases, OTHER contains entities like
seas and regions.

The copyright of the tokens remains by the original copyright holders
of the CoNLL dataset. We distribute the labels under Creative Commons 
Attribution-ShareAlike 4.0 International. Due to the separate copyright, 
the labels are unfortunately published without the tokens.

The tokens and labels can be joint simply by merging the tokens of
the English CoNLL-2003 NER dataset with the labels from the given files. 
Each token corresponds to one label. The label files
do not contain the empty lines from the token files. You can
double-check if the merging was correct by testing if each new label 
exactly corresponds to a LOC label in the original
CoNLL file.

The labels in file eng.finegrained-loc_first1500tokens.train correspond
to the first 1500 tokens from the CoNLL file eng.train. The file
eng.finegrained-loc.testb corresponds to the file eng.testb.
