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

from autom_labeling_library.entity import EntityNameCollection
from autom_labeling_library.matching import MatchingAlgorithm, MatchConflictGreedySolvingAlgorithm
from autom_labeling_library.formats import LabelCreator, CoNLLFormatCreator
from .memory import Memory, DocumentType
from .status import Status
from .util import try_method_return_json, create_tokenizer

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)

bp = Blueprint('autom_annotation', __name__, url_prefix='/autom_annotation')

@bp.route('/<document_type:document_type>', methods=('GET', 'POST'))
def index(document_type):
    """
    If no text has been uploaded, redirect to text upload.
    If text has been uploaded, show annotation result page.
    The actual annotation is done via Ajax in the background on that
    page as it might take a while (by calling the /autom_annotate_json 
    resource defined below).
    """
    document = Memory.get_instance().get_document(document_type)
    if not document:
        flash("A {} document needs to be uploaded or inputed before automatic annotation.".format(
                document_type), "warning")
        return redirect(url_for('text_input.index', document_type=document_type))
    
    at_least_one_entity_name = False
    for extraction in Memory.get_instance().get_extractions(only_loaded=True):
        if extraction.get_num_extracts() > 0:
            at_least_one_entity_name = True
            break
    
    if not at_least_one_entity_name:
        flash("Entity names need to be extracted for the automatic labeling process! Have you already extracted entitiy names? Have you loaded the necessary extractions?", "danger")
        return redirect(url_for('knowledge_base.list_extracts'))
    
    #if document.autom_labels is not None: # TODO Now that cache clearing for labels is deactivated, this does not make sense
    #    flash("This document has already been automatically annotated.", "warning")
        
    return render_template("autom_annotation/autom_annotation.html", document_type=document_type)

@bp.route('/autom_annotate_json/<document_type:document_type>', methods=('GET', 'POST'))
def autom_annotate_json(document_type):    
    def lambda_function():
        document = Memory.get_instance().get_document(document_type)
        annotate_text(document)

    return try_method_return_json(lambda_function, report_error_status=True)
    
def annotate_text(document): 
    Status.get_instance().set_state_processing()
    
    settings = Memory.get_instance().get_settings()
    if settings.use_language_specific_tokenizer_for_entity_names:
        entity_name_tokenizer = create_tokenizer(settings.spacy_tokenizer_language_code)
    else:
        entity_name_tokenizer = create_tokenizer("whitespace")
    
    Status.get_instance().set_message("Collecting entity names.")
    entity_names = []
    for extraction in Memory.get_instance().get_extractions(only_loaded=True):
        entity_names.extend(extraction.get_extracts_for_matching(tokenizer=entity_name_tokenizer))
    
    if len(entity_names) == 0:
        raise Exception("No entity names found. Could not annotate. Maybe no extractions are active?")
    
    Status.get_instance().set_message("Building entity name collection.")
    entity_name_collection = EntityNameCollection(entity_names)
   
    matching_algorithm = MatchingAlgorithm(entity_name_collection)
    tokens = document.tokens
    possible_matches = matching_algorithm.match_tokens(tokens, Status.get_instance())
    
    Status.get_instance().set_message("Solving conflicts.")
    conflict_solving_algorithm = MatchConflictGreedySolvingAlgorithm()
    matches = list(possible_matches) # copy because conflict resolving algorithm removes matches to resolve conflicts
    conflict_solving_algorithm.resolve_conflicts(matches)
    
    label_creator = LabelCreator()
    labels = label_creator.create(tokens, matches)
    
    document.autom_labels = labels
    document.matches = matches
    document.possible_matches = possible_matches

    Status.get_instance().set_state_idle()
