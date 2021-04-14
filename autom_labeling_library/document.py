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

from enum import Enum

class Document:
    
    def __init__(self, raw_text, document_raw_format):
        self.raw_text = raw_text
        self.document_raw_format = document_raw_format
        self.tokens = None
        self.autom_labels = None
        self.matches = None # matches select by the conflict resolving algorithm
        self.possible_matches = None # all possible matches
        self.gold_labels = None
        
class DocumentRawFormat(Enum):
    SIMPLE_TEXT = "simple_text"
    CONLL_TAB = "conll_tab"
    CONLL_SPACE = "conll_space"

