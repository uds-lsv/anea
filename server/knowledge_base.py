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

import time
import io
import re

from autom_labeling_library.knowledge_base import WikiDataNameExtraction, WikiDataExtractor
from .memory import Memory, ExtractionEntryState
from .status import Status
from .util import try_method_return_json, create_tokenizer

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file
)

bp = Blueprint('knowledge_base', __name__, url_prefix='/knowledge_base')

valid_instance_of_property_pattern = re.compile("Q[0-9]+")
valid_named_entity_label_pattern = re.compile("[a-zA-Z0-9_-]+")

@bp.route('/', methods=('GET', 'POST'))
def index():    
    return redirect(url_for('knowledge_base.extract_from_knowledge_base_form'))

@bp.route('/extract', methods=('GET', 'POST'))
def extract_from_knowledge_base():
    if request.method == 'POST':
        # for each rule, a instance_of_property, depth, language_code and a label are given
        num_rules = int(len(request.form)/4) 
        
        extractions = []
        for i in range(num_rules):
            # in the form each rule is spread over three input fields
            # that all have the same number at the end of the name
            input_instance_of_property = request.form["instance_of_property{}".format(i)]
            input_depth = request.form["depth{}".format(i)]
            input_language_code = request.form["language_code{}".format(i)]
            input_named_entity_label = request.form["label{}".format(i)]
            
            # catch empty depth field
            if input_depth == '':
                input_depth = 0
            
            if len(input_instance_of_property) > 0 and \
               len(input_language_code) > 0 and \
               len(input_named_entity_label) > 0:
                
                if not valid_extract_input_specification(input_instance_of_property, input_depth, input_language_code, input_named_entity_label):
                    return redirect(url_for('knowledge_base.extract_from_knowledge_base_form'))
                    
                identifier = None # identifier will be set by Memory
                extractions.append(WikiDataNameExtraction(identifier, input_instance_of_property, input_depth, 
                                    input_language_code, input_named_entity_label))
        
        if len(extractions) < 1:
            flash("Could not parse the rules to extract. Maybe no values were entered into the form?", "danger")
            return redirect(url_for('knowledge_base.extract_from_knowledge_base_form'))
        
        for extraction in extractions:
            Memory.get_instance().add_extraction_entry(extraction)
            
        return render_template("knowledge_base/extraction.html", 
                        time_retrieval_start=time.strftime("%H:%M"))
                        
    else:
        flash("Define the rules to be extracted first. During the "
              + " extraction, the page should not be refreshed or reloaded.", 
              "warning")
              
        return redirect(url_for('knowledge_base.extract_from_knowledge_base_form'))

@bp.route('/extract_done', methods=('GET', 'POST'))
def extract_done():
    return render_template("knowledge_base/extraction_done.html");

def valid_extract_input_specification(instance_of_property, depth, language_code, named_entity_label):
    """ Checks if the input for the extraction is valid. Both to help
        the user get correct input and to sanitize it to avoid
        attacks as the values are used to generate filenames.
    """
    
    pattern_match = valid_instance_of_property_pattern.match(instance_of_property)
    if instance_of_property != "manual_entry" and instance_of_property != "stopwords" and( pattern_match is None or pattern_match.span()[1] != len(instance_of_property) ):
        flash(f"The value of the instance of property must start with Q and then be followed by one or more digits (e.g. Q123). Currently, it is '{instance_of_property}'.", "danger")
        return False
        
    if len(language_code) != 2 or language_code.lower() != language_code:
        flash(f"The language code must consist of two lowercase letters (e.g. en). Currently, it is '{language_code}'.", "danger")
        return False
        
    pattern_match = valid_named_entity_label_pattern.match(named_entity_label)
    if pattern_match is None or pattern_match.span()[1] != len(named_entity_label):
        flash(f"The label must only consist of the characters a-z (upper or lowercased) or the special characters - or _ (e.g. LOC or feature_film). Currently it is '{named_entity_label}'.", "danger")
        return False    

    try: 
        depth_as_int = int(depth)
        if depth_as_int < 0:
            flash(f"The depth must be an integer >= 0. Currently it is '{depth}'.", "danger")
            return False
    except:
        flash(f"The depth must be an integer >= 0. Currently it is '{depth}'.", "danger")
        return False
        
    return True
        
@bp.route('/extract_form', methods=('GET', 'POST'))
def extract_from_knowledge_base_form():
    return render_template("knowledge_base/extraction_form.html")

@bp.route('/extract_json', methods=('GET', 'POST'))
def extract_from_knowledge_base_json():
    
    def lambda_function():
        # get all WikiDataNameExtraction objects that have not been filled, yet.
        Status.get_instance().set_state_processing()
        
        new_extractions = [extraction for extraction in Memory.get_instance().get_extractions(only_loaded=True)
                            if not extraction.get_property("has_been_fully_extracted")]
        extractor = WikiDataExtractor(Memory.get_instance().get_settings().wikidata_path)
        extractor.extract(new_extractions, Status.get_instance())
        
        Memory.get_instance().updated_extractions(new_extractions)
        Status.get_instance().set_state_idle()
    
    return try_method_return_json(lambda_function, report_error_status=True)
    
@bp.route('/list_extracts', methods=('GET', 'POST'))
def list_extracts():
    settings = Memory.get_instance().get_settings() # TODO Doubled code with autom_annotation.py, refactor
    if settings.use_language_specific_tokenizer_for_entity_names:
        entity_name_tokenizer = create_tokenizer(settings.spacy_tokenizer_language_code)
    else:
        entity_name_tokenizer = create_tokenizer("whitespace")
    
    extraction_entries = Memory.get_instance().get_extraction_entries()
    all_example_extracts = []
    for extraction_entry in extraction_entries:
        if extraction_entry.state == ExtractionEntryState.LOADED:
            example_extracts = extraction_entry.extraction.get_extracts_for_matching(entity_name_tokenizer, 20)
            all_example_extracts.append(example_extracts)
        elif extraction_entry.state == ExtractionEntryState.LOADING:
            all_example_extracts.append([])
        elif extraction_entry.state == ExtractionEntryState.NOT_LOADED:
            all_example_extracts.append([])
    
    extractions = [extraction_entry.extraction for extraction_entry in extraction_entries]
    extraction_states = [extraction_entry.state for extraction_entry in extraction_entries]
    return render_template("knowledge_base/list_extractions.html", 
                           extractions=extractions,
                           extraction_states=extraction_states,
                           example_extracts=all_example_extracts) 

@bp.route('/load_extract/', methods=('GET', 'POST'))
def load_all_extracts():
    return load_extract("")

@bp.route('/load_extract/<string:extraction_identifier>', methods=('GET', 'POST'))
def load_extract(extraction_identifier):
    """ A full extraction identifier (e.g. "en-ORG-Q5")
        or a substring of an extraction identifier to match (e.g. "en-ORG" or "en")
    """
    
    def lambda_function():
        extraction_identifier_stripped = extraction_identifier.strip()
        extraction_entries = Memory.get_instance().get_extraction_entries()
        for entry in extraction_entries:
            # either no limitation entered, then matching all or matching full or substring
            if len(extraction_identifier_stripped) == 0 or extraction_identifier_stripped in entry.identifier:
                if entry.state == ExtractionEntryState.NOT_LOADED: # some might already have been loaded but still match, but that is fine
                    entry.load_extraction(Memory.get_instance(), load_configuration=False, load_extracts=True)
        
        Memory.get_instance().invalidate_autom_annotation_cache()
                
    return try_method_return_json(lambda_function, report_error_status=False)

@bp.route('/unload_extract/', methods=('GET', 'POST'))
def unload_all_extracts():
    return unload_extract("")

@bp.route('/unload_extract/<string:extraction_identifier>', methods=('GET', 'POST'))
def unload_extract(extraction_identifier):
    """ A full extraction identifier (e.g. "en-ORG-Q5")
        or a substring of an extraction identifier to match (e.g. "en-ORG" or "en")
    """
    
    def lambda_function():
        extraction_identifier_stripped = extraction_identifier.strip() # re-assign necessary due to context change
        extraction_entries = Memory.get_instance().get_extraction_entries()
        for entry in extraction_entries:
            # either no limitation entered, then matching all or matching full or substring
            if len(extraction_identifier_stripped) == 0 or extraction_identifier_stripped in entry.identifier:
                if entry.state == ExtractionEntryState.LOADED: # some might not be loaded but still match, but that is fine
                    entry.unload_extraction(Memory.get_instance())
                    
        Memory.get_instance().invalidate_autom_annotation_cache()
        
    return try_method_return_json(lambda_function, report_error_status=True)

@bp.route('/change_extraction_property_json/<string:extraction_identifier>', methods=('GET', 'POST'))
def change_extraction_property(extraction_identifier):
    if request.method == 'POST':
        return try_method_return_json(lambda: change_extraction_property(extraction_identifier), report_error_status=False)


def change_extraction_property(extraction_identifier):
        extraction = Memory.get_instance().get_extraction_from_identifier(extraction_identifier)
        form = request.form
        
        if "active" in form and form["active"] == "true":
            property_active = True
        else: # if checkbox is unchecked, the "active" element is not part of the post
            property_active = False
            
        if "use_aliases" in form and form["use_aliases"] == "true":
            property_use_aliases = True
        else: # if checkbox is unchecked, the "active" element is not part of the post
            property_use_aliases = False
            
        if "split_tokens" in form and form["split_tokens"] == "true":
            property_split_tokens = True
        else: # if checkbox is unchecked, the "active" element is not part of the post
            property_split_tokens = False
            
        if "remove_diacritics" in form and form["remove_diacritics"] == "true":
            property_remove_diacritics = True
        else: # if checkbox is unchecked, the "active" element is not part of the post
            property_remove_diacritics = False
            
        if form["match_casing"] in ["exact", "ignore_first_character", "ignore_all", 
                                    "fuzzy"]:
            property_match_casing = form["match_casing"]
        else:
            raise Exception("Match casing property unknown")
        
        if len(form["minimum_length"]) == 0: # empty field
            property_minimum_length = -1
        else:
            try:
                property_minimum_length = int(form["minimum_length"])
            except:
                raise Exception("Minimum length is not a number.")

            if not(property_minimum_length == -1 or property_minimum_length > 0):
                raise Exception("Minimum length must be -1 (no length filter) or > 0")
                
        if len(form["priority"]) == 0: # empty field
            property_priority = 0
        else:
            try:
                property_priority = int(form["priority"])
            except:
                raise Exception("Setting 'Priority' is not a number.")
        
        new_label = form["label"].strip()
        if len(new_label) == 0: # empty field
            raise Exception("Label must not be empty.")
        
        print(f"Saved {property_remove_diacritics}")
        extraction.set_property("active", property_active)
        extraction.set_property("use_aliases", property_use_aliases)
        extraction.set_property("split_tokens", property_split_tokens)
        extraction.set_property("remove_diacritics", property_remove_diacritics)
        extraction.set_property("match_casing", property_match_casing)
        extraction.set_property("minimum_length", property_minimum_length)
        extraction.set_property("priority", property_priority)
        
        extraction.set_property("filter_list", _parse_filter_list(form["filter_list"]))
        
        if new_label != extraction.get_label():
            extraction.set_label(new_label)
            Memory.get_instance().update_extraction_identifier(extraction)

        Memory.get_instance().updated_extractions([extraction], changed_config=True,
                                                                changed_extracts=False)
        
        
                                                                      
def _parse_filter_list(filter_list_form_input):
    inputs = filter_list_form_input.split("\n")
    filter_list = []
    for input_line in inputs:
        input_line = [token.strip() for token in input_line.split(" ") if len(token.strip()) > 0]
        filter_list.append(input_line)
    return filter_list
    
@bp.route('/download_extraction/<string:extraction_identifier>', methods=('GET', 'POST'))
def download_extraction(extraction_identifier):
    stripped_extraction_identifier = extraction_identifier.strip()
    extraction_entry = Memory.get_instance().get_extraction_entry_from_identifier(stripped_extraction_identifier)
    
    if extraction_entry.state == ExtractionEntryState.NOT_LOADED:
        raise Exception(f"Extraction {stripped_extraction_identifier} can not be downloaded because it has not been loaded.")
    
    settings = Memory.get_instance().get_settings() # TODO Doubled code with autom_annotation.py, refactor
    if settings.use_language_specific_tokenizer_for_entity_names:
        entity_name_tokenizer = create_tokenizer(settings.spacy_tokenizer_language_code)
    else:
        entity_name_tokenizer = create_tokenizer("whitespace")
    
    extracts = extraction_entry.extraction.get_extracts_for_matching(entity_name_tokenizer)
    output_file = io.BytesIO()
    output_file.write(f"# Extraction {stripped_extraction_identifier}\n#Timestamp: {time.strftime('%Y-%m-%d %H:%M')}\n".encode("utf-8"))
    for extract in extracts:
        output_file.write("{}\t{}\t{}\n".format(extract.name, extract.tokenized_name, extract.entity_object).encode("utf-8"))

    filename = f"extracts_{stripped_extraction_identifier}.tsv" # stripped_extraction_identifier should be a valid identifier, otherwise .get_extraction would have thrown an Exception. Therefore should be safe to use this for a filename.
    return send_file(io.BytesIO(output_file.getvalue()), mimetype="text/plain",  # TODO Do something better than BytesIO of BytesIO
                     as_attachment=True, attachment_filename=filename,
                     cache_timeout=0,  # prevents caching, could be set to the actual upload/annotation time
                     last_modified=time.time())
