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

import io
import time

from autom_labeling_library.formats import LabelCreator, CoNLLFormatCreator
from .memory import Memory, DocumentType
from .util import get_document_from_memory

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, 
    jsonify, send_file
)

bp = Blueprint('text_output', __name__, url_prefix='/text_output')

@bp.route('/text_output_page/<document_type:document_type>', methods=('GET', 'POST'))
def text_output_page(document_type):
    document, redirect = get_document_from_memory(document_type)
    if document is None:
        return redirect
    
    # convert the match objects into a list that shows
    # for each token which EntityNames match
    match_output = None
    other_match_output = None
    if not document.matches is None:
        
        # the actual matches
        match_output = [None for _ in range(len(document.tokens))]
        for match in document.matches:
            matcher = [match.match_entity_name.name, match.match_entity_name.get_label(), match.match_entity_name.entity_object.identifier, match.match_entity_name.entity_extraction.get_identifier()]
            for i in range(match.match_start_pos, match.match_end_pos):
                match_output[i] = matcher
      
        # other matches, not taken by conflict-resolving-algorithm
        other_match_output = [[] for _ in range(len(document.tokens))]
        for match in document.possible_matches:
            if match in document.matches: # only those not taken
                continue
            matcher = [match.match_entity_name.name, match.match_entity_name.get_label(), match.match_entity_name.entity_object.identifier, match.match_entity_name.entity_extraction.get_identifier()]
            for i in range(match.match_start_pos, match.match_end_pos):
                other_match_output[i].append(matcher)

    return render_template('text_output/text_output_page.html', 
                               document_type=document_type,
                               tokens=document.tokens,
                               gold_labels=document.gold_labels,
                               autom_labels=document.autom_labels,
                               match_output=match_output,
                               other_match_output=other_match_output
                               )
                               
@bp.route('/text_download/<document_type:document_type>', methods=('GET', 'POST'))
def text_download(document_type):
    document, redirect = get_document_from_memory(document_type)
    if document is None:
        return redirect
        
    output_creator = CoNLLFormatCreator()
    output_text = output_creator.create(document.tokens, 
                                        gold_labels = document.gold_labels,
                                        autom_labels = document.autom_labels)
    output_text = output_text.encode("utf-8")
    output_file = io.BytesIO(output_text)
    
    return send_file(output_file, mimetype="text/plain", 
                     as_attachment=True, attachment_filename="document.conll",
                     cache_timeout=0,  # prevents caching, could be set to the actual upload/annotation time
                     last_modified=time.time())
    
                              
