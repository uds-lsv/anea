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

from collections import Counter
from .formats import LabelConverter

class ErrorAnalysis:
    
    def __init__(self, outside_label="O"):
        self.outside_label = outside_label
    
    def analyse_errors(self, document, number_most_common_errors):
        assert document.tokens is not None
        assert document.autom_labels is not None
        assert document.gold_labels is not None
        assert len(document.tokens) == len(document.autom_labels)
        assert len(document.tokens) == len(document.gold_labels)
        
        precision_errors = Counter()
        recall_errors = Counter()
        label_converter = LabelConverter()
        for token, autom_label, gold_label in zip(document.tokens, document.autom_labels, document.gold_labels):
            
            # convert to IO format to ignore B- and I- prefixes, 
            # in most cases should not add useful information to this analyssis
            autom_label = label_converter.BIO2_to_IO(autom_label)
            gold_label = label_converter.BIO2_to_IO(gold_label)
            
            if autom_label != gold_label:
                error = Error(token, autom_label, gold_label)
                if autom_label == self.outside_label:
                    recall_errors[error] += 1
                else:
                    precision_errors[error] += 1
                
        return precision_errors.most_common(number_most_common_errors), recall_errors.most_common(number_most_common_errors)

class Error:
    
    def __init__(self, token, autom_label, gold_label):
        self.token = token
        self.autom_label = autom_label
        self.gold_label = gold_label
        
    def __eq__(self, other):
        if isinstance(other, Error):
            return self.token == other.token and self.autom_label == other.autom_label and self.gold_label == other.gold_label
        return False
        
    def __hash__(self):
        return hash(self.token) + hash(self.autom_label) + hash(self.gold_label)
        
    def __str__(self):
        return f"Error({self.token}|Pred:{self.autom_label}|Gold:{self.gold_label})"

