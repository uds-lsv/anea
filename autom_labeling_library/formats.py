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

from .document import Document, DocumentRawFormat

class LabelCreator:
    """ Given a list of tokens and Match objects,
        creates a list of (token, label) pairs.
        Supports IO ('ORG') and BIO-2 ('I-ORG, B-ORG') format
    """
    def __init__(self, annotation_type="BIO-2", outside_label="O"):
        self.annotation_type = annotation_type
        self.outside_label = outside_label
    
    
    def create(self, tokens, matches):              
        current_match = None
        next_match_pos = 0
        labels = []
        
        if len(matches) == 0:
            next_match_pos = -1
            
        for pos, token in enumerate(tokens):
            
            # if this token is the first token of the next match
            if next_match_pos != -1 and pos == matches[next_match_pos].match_start_pos:
                current_match = matches[next_match_pos]
                next_match_pos += 1
                
                # if no more matches
                if next_match_pos == len(matches):
                    next_match_pos = -1
                    
                label = self._get_label(current_match, True)
            
            # if this token is within a match
            elif not current_match is None and pos < current_match.match_end_pos:
                label = self._get_label(current_match, False)
                
                # if this is the last token of this match
                if pos == current_match.match_end_pos-1:
                    current_match = None
            
            # outside of a match
            else:
                label = self.outside_label
            
            labels.append(label)
        
        return labels
        
    def _get_label(self, match, first_token_of_match):
        """
        Returns a named entity label for the given Match object. 
        Set first_token_of_match to True, if this is the
        first token of that entity (e.g. "Albert" in "Albert Einstein").
        """
        label = match.match_entity_name.get_label()

        if label == 'O':
            return label
        
        if self.annotation_type == "BIO-2":
            if first_token_of_match:
                return "B-" + label
            else: 
                return "I-" + label
        
        elif self.annotation_type == "IO":
            return label
        
        else:
            raise Exception("Annotation type {} not supported.".format(self.annotation_type))


class LabelConverter:
    """ Converts labels from and to different formats. E.g. BIO-2 to IO
    """
    
    def __init__(self, outside_label="O"):
        self.outside_label = outside_label
    
    def BIO2_to_IO(self, label):
        if label == self.outside_label:
            return label
        if label.startswith("B-") or label.startswith("I-"):
            return label[2:]
        raise Exception(f"Label {label} is not in BIO2 format")

class CoNLLFormatCreator:
    """ Given a list of tokens and Match objects,
        creates a string in the CoNLL format (one token and
        corresponding label per line).
    """
    
    def __init__(self, annotation_type="BIO-2", outside_label="O", 
                separator="\t", new_line="\n"):
        self.label_creator = LabelCreator(annotation_type, outside_label)
        self.separator = separator
        self.new_line = new_line
    
    def create(self, tokens, gold_labels=None, autom_labels=None):               
        output = ""
        for i, token in enumerate(tokens):
            output += "{}".format(token)
            if gold_labels is not None:
                output += "{}{}".format(self.separator, gold_labels[i])
            if autom_labels is not None:
                output += "{}{}".format(self.separator, autom_labels[i])
            output += self.new_line
            
        return output

class CoNLLFormatParser:
    """
        Given the raw text in the CoNLL format (one token per line 
        and optionally different labels (POS, etc.)
        with the last label being the gold-label, returns a Document object 
        containing tokens (and gold-labels if given).
    """
    
    def __init__(self, new_line="\n"):
        self.new_line = new_line

    def parse(self, raw_text, raw_format, label_type="gold"):
        if raw_format == DocumentRawFormat.CONLL_SPACE:
            separator = " "
        elif raw_format == DocumentRawFormat.CONLL_TAB:
            separator = "\t"
        else:
            raise Exception(f"Raw format {raw_format} not supported for CoNLL parsing.")
         
        lines = raw_text.split(self.new_line)
        
        tokens = []
        labels = []
        
        for line in lines:
            line = line.strip()
        
            # skip begin of document indicator (used in some files)
            if line.startswith("-DOCSTART-"):
                continue
            
            # skip empty line / end of sentence marker (used in some files) 
            if len(line) == 0:
                continue
            
            # Skip marker (used in some files)
            if line == "--": 
                continue
                
            elements = line.split(separator)
            
            tokens.append(elements[0])
            if len(elements) > 1:
                labels.append(elements[-1])
        
        document = Document(raw_text, raw_format)
        document.tokens = tokens
        
        if len(labels) > 0:
            
            if len(tokens) != len(labels):
                raise Exception("Number of tokens ({}) != number of labels ({}).".format(
                                len(tokens), len(labels)))
            else:
                if label_type == "gold":
                    document.gold_labels = labels
                elif label_type == "autom":
                    document.autom_labels = labels
                else:
                    raise Exception("Label type {} is not supported.".format(label_type))
        
        return document
        
    def _io_to_bio(self, labels):
        
        in_entity = False
        for i, label in enumerate(labels):
            if label == "O":
                in_entity = False
            else:
                if not in_entity: # first token of entity
                    labels[i] = "B-" + label
                    in_entity = True
                else:
                    labels[i] = "I-" + label
                
