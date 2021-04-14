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

import traceback

from autom_labeling_library.preprocessing import Preprocessing, remove_diacritics
from autom_labeling_library.document import Document, DocumentRawFormat
from autom_labeling_library.formats import CoNLLFormatParser
from .memory import Memory, DocumentType, document_type_to_readable_name
from .util import create_tokenizer

import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for,
    has_request_context
)

bp = Blueprint('text_input', __name__, url_prefix='/text_input')

@bp.route('/', methods=('GET', 'POST'))
def index():    
    return redirect(url_for('text_input.document_types'))

@bp.route('/document_types', methods=('GET', 'POST'))
def document_types():
    document_types_and_documents = [(document_type, 
        Memory.get_instance().get_document(document_type)) for
        document_type in [DocumentType.UNLABELED_INPUT, DocumentType.TEST]]
        
    return render_template("text_input/document_types.html",
                            document_types_and_documents = document_types_and_documents)

@bp.route('/text_input_form/<document_type:document_type>', methods=('GET', 'POST'))
def text_input_form(document_type):
    """
        Text input form
    """
    
    annotated_text = None
    # if text was sent via form
    if request.method == 'POST':
        worked = True
        
        raw_text = request.form['text_input']
        raw_format = request.form['raw_format']
        
        if "label_type" in request.form:
                label_type = request.form["label_type"]
        else:
            raise Exception("Label type not specified")
        
        if not raw_text or len(raw_text) == 0:
            flash("No text given.", "warning")
            worked = False
            
        else:
            raw_text = raw_text.strip()
            worked = process_input_text(raw_text, raw_format, document_type, label_type)
            Memory.get_instance().raw_documents_changed()
                                                   
        if worked:
            return redirect(url_for('text_output.text_output_page', 
                                    document_type=document_type))
    
    # display text input form
    return render_template('text_input/text_input_form.html', 
                           document_type=document_type)
                           
@bp.route('/text_upload_form/<document_type:document_type>', methods=('GET', 'POST'))
def text_upload_form(document_type):
    if request.method == 'POST':
        worked = True
        
        raw_format = request.form['raw_format']
        
        if "label_type" in request.form:
                label_type = request.form["label_type"]
        else:
            raise Exception("Label type not specified")
        
        if 'file' not in request.files or len(request.files['file'].filename) == 0:
            flash('No file was given.', "warning")
            worked = False
        else:
            uploaded_file = request.files['file']
            # TODO Check Mime type if it is string
            lines = [line.decode() for line in uploaded_file.readlines()]
            raw_text = "\n".join(lines)
            
            worked = process_input_text(raw_text, raw_format, document_type, label_type)
            Memory.get_instance().raw_documents_changed()
        
        if worked:
            return redirect(url_for('text_output.text_output_page', 
                                    document_type=document_type))
                                    
    return render_template('text_input/text_upload_form.html', document_type=document_type)  

def process_input_text(input_text, document_raw_format, document_type, label_type="gold"):
    """
    Processes the given text. Checks whether tokenization/parsing
    worked and stores the resulting document in the corresponding 
    document_type memory. The processing depends on the 
    document_raw_format (tokenize_text or parse_conll)
    """
    document_raw_format = DocumentRawFormat(document_raw_format)
    if document_raw_format == DocumentRawFormat.SIMPLE_TEXT:
        document = tokenize_text(input_text)
    elif document_raw_format == DocumentRawFormat.CONLL_SPACE or \
        document_raw_format == DocumentRawFormat.CONLL_TAB:
        document = parse_conll(input_text, document_raw_format, label_type)
    else:
        flash("Document raw format {} unknown.".format(document_raw_format), "danger")
        return False        
            
    if not document:
        flash("Failed to process the input.", "danger")
        return False
        
    if Memory.get_instance().get_settings().remove_diacritics:
        document.tokens = [remove_diacritics(token) for token in document.tokens]
    
    if (document_type == DocumentType.DEVELOPMENT or 
        document_type == DocumentType.TEST) and \
        document.gold_labels is None:
            flash("Uploaded {} data needs gold labels but none were provided. Maybe the wrong format was selected? Have you checked whether the columns are separated by a space or a tab?".format(
                    document_type_to_readable_name(document_type)), "danger")
            return False
                    
    Memory.get_instance().set_document(document_type, document)
    return True

def tokenize_text(input_text, language_code=None, lemmatize=None):
    if language_code is None:
        language_code = Memory.get_instance().get_settings().spacy_tokenizer_language_code
    if lemmatize is None:
        lemmatize = Memory.get_instance().get_settings().lemmatize
        
    tokenizer = create_tokenizer(language_code)

    if tokenizer is None:
        return None
    
    document = Document(input_text, DocumentRawFormat.SIMPLE_TEXT)
    document.tokens = tokenizer.tokenize(input_text, lemmatize=lemmatize)
    return document

def parse_conll(input_text, raw_format, label_type):
    parser = CoNLLFormatParser()
    language_code = Memory.get_instance().get_settings().spacy_tokenizer_language_code
    lemmatize = Memory.get_instance().get_settings().lemmatize
    
    if lemmatize:
        try:
            lemmatizer = Preprocessing.create_lemmatizer(language_code)
        except Exception as e:
            error_message = f"Could not load the lemmatizer for language {language_code}. You might not have installed " + \
                      "the necessary, external tokenization library. Please, " + \
                      "see the documentation for more details." + \
                      f"The actual error was: '{e} - {traceback.format_exc()}'"
            if has_request_context():
                flash(error_message, "danger")
            else:
                raise Exception(error_message)
            return None
    try:
        document = parser.parse(input_text, raw_format, label_type)
        if lemmatize:
            document.tokens = lemmatizer.lemmatize(document.tokens)
    except Exception as e:
        error_message = "Failed to parse the document in CoNLL format. The error " + \
              "was: '{}' Stacktrace: {}".format(e, traceback.format_exc())
        if has_request_context():
            flash(error_message, "danger")
        else:
            raise Exception(error_message)
        return None
    return document
