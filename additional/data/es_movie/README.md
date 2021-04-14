# es-movie

The texts for this dataset were collected from articles 
on the Spanish website https://www.20minutos.es/cine/ (the
movie category). The specific news outlet was picked 
because their articles are published under the creative commons license.
The corresponding links to the original articles can be found in the data.

The text was tokenized using the Spanish Spacy tokenizer and then 
manually labeled. All mentions of movies and movie series (e.g. "Lord
of the Rings") were labeled as MOVIE. Cases were a token refered to the
main protagonist and not the movie itself (of the same name) were not 
labeled as movie (e.g. Spiderman). The BIO-2 schema was used.

Following the license of the original texts, we publish this data under
Creative Commons Attribution-ShareAlike 3.0 Unported.

The following files are provided

* es-movie_first1500tokens.train are 1500 tokens labeled for training
* es-movie.test are 4124 tokens labeled for testing
* es-movie_unlabeled.txt are 14894 unlabeled tokens to apply a distant supervision/automatic annotation technique on it
* es-movie_unlabeled_autom-annotated.txt the previous file, but with additional, automatically obtained labels
