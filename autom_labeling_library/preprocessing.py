# Copyright 2020 Saarland University, Spoken Language Systems LSV 
# Author: Michael A. Hedderich, Lukas Lange, Dietrich Klakow
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# THIS CODE IS PROVIDED *AS IS*, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
# WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
# MERCHANTABLITY OR NON-INFRINGEMENT.
#
# See the Apache 2 License for the specific language governing permissions and
# limitations under the License.

import importlib.util
import unicodedata

# not all version might have Spacy installed
if not importlib.util.find_spec("spacy") is None:
    import spacy
    from spacy.tokens import Doc

# not all version might have Spacy installed
if not importlib.util.find_spec("estnltk") is None:
    from estnltk import Text

def remove_diacritics(token):
    nfkd_form = unicodedata.normalize('NFKD', token)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

class Preprocessing:
    
    @staticmethod
    def is_valid_language(language):
        return language in Preprocessing.get_valid_languages()
    
    @staticmethod
    def get_valid_languages():
        return SpacyTokenizer.get_valid_languages() + ["et", "whitespace"]
        
    @staticmethod
    def create_tokenizer(language):
        """ Creates a tokenizer that splits a given text into tokens.
            Optionally can also do Lemmatization
        """
        if SpacyTokenizer.is_valid_language(language):
            return SpacyTokenizer(language)
            
        elif language == "et":
            return EstnltkTokenizer() 
            
        elif language == "whitespace":
            return WhitespaceTokenizer()
    
    @staticmethod
    def create_lemmatizer(language):
        """ Creates a Lemmatizer that lemmatizes
            a list of tokens.
        """
        if SpacyTokenizer.is_valid_language(language):
            return SpacyLemmatizer(language)
        elif language == "et":
            return EstnltkTokenizer() # Tokenizer can also Lemmatize

class SpacyTokenizer:
    
    def __init__(self, language):
        self.language = language
        self.spacy_inst = spacy.load(language)
    
    @staticmethod
    def is_valid_language(language):
        return language in SpacyTokenizer.get_valid_languages()
    
    @staticmethod
    def get_valid_languages():
        return ["en", "de", "es", "pt", "fr", "it", "nl", "el", "xx"]
    
    def tokenize(self, text, lemmatize=False):     
        doc = self.spacy_inst(text)
        if lemmatize:
            return [token.lemma_ for token in doc]
        else:
            return [token.text for token in doc]
            
class SpacyLemmatizer:
    """ Lemmatizer from Spacy. Spacy usually expects a sentence and not
        a list of (already tokenized) words. Therefore, the 
        SpacyIdentityTokenizer is used.
    """
    
    def __init__(self, language):
        self.language = language
        self.spacy_inst = spacy.load(language)
        self.spacy_inst.tokenizer = SpacyIdentityTokenizer(self.spacy_inst.vocab)
        
    def lemmatize(self, tokens):
        doc = self.spacy_inst(tokens)
        return [token.lemma_ for token in doc]

class SpacyIdentityTokenizer(object):
    """ This is a Tokenizer for Spacy that takes as
        input a list of tokens (in contrast to the usual string)
        and returns a Spacy document with this list of tokens
        as tokens.
        Allows to run the Spacy pipeline on already, externally
        tokenized text.
    """
    def __init__(self, vocab):
        self.vocab = vocab

    def __call__(self, words):
        spaces = [True] * len(words)
        return Doc(self.vocab, words=words, spaces=spaces)
        
class EstnltkTokenizer:
    
    def __init__(self):
        from estnltk import Text
        
    def tokenize(self, text, lemmatize=False):
        text = Text(text).analyse('morphology')
        layer = text.morph_analysis
        if lemmatize:
            tokens = [layer[i, "lemma"][0] for i in range(len(layer))]
        else:
            tokens = [layer[i, "text"] for i in range(len(layer))]
        return tokens

    def lemmatize(self, tokens):
        lemmatized_tokens = []
        for token in tokens:
            text = Text(token).analyse('morphology')
            layer = text.morph_analysis
            lemmatized_tokens.append(layer[0, "lemma"][0])
        if len(tokens) != len(lemmatized_tokens):
            raise Exception("Lemmatization did more tokenizing than it should.") # TODO Replace TokensTagger with one that only does whitespace tokenization, see https://github.com/estnltk/estnltk/blob/version_1.6/tutorials/brief_intro_to_text_layers_and_tools.ipynb
        return lemmatized_tokens

class WhitespaceTokenizer:
    
    def tokenize(self, text, lemmatize=False):
        if lemmatize == True:
            raise Exception("Whitespace tokenizer does not support lemmatization.")
        return text.split()
