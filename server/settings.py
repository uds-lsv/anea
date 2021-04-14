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

import os

from autom_labeling_library.preprocessing import Preprocessing
from .memory import Memory

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/', methods=('GET', 'POST'))
def index():  
    
    if request.method == 'POST':
        settings = Memory.get_instance().get_settings()
        
        worked = True
        
        wikidata_path = request.form['wikidata_path'].strip()
        
        if not wikidata_path or len(wikidata_path) == 0:
            flash("No path to the Wikidata dump given.", "danger")
            worked = False
            
        elif not os.path.isfile(wikidata_path): # TODO More checks if this is actually the correct file
            flash("Path to the Wikidata dump is not a valid file on the server.", "danger")
            worked = False
        
        tokenizer_language = request.form['tokenizer_language'].strip()
        
        if not tokenizer_language or len(tokenizer_language) == 0:
            flash("No tokenizer language code given.", "danger")
            worked = False
        
        elif not Preprocessing.is_valid_language(tokenizer_language):
            flash(f"Tokenizer/Lemmatizer language is not supported. Supported are {Preprocessing.get_valid_languages()}", "danger")
            worked = False
        
        else:
            # Test if Preprocessing works. Can fail if language pack or external library is not installed.
            # Will flash a warning accordingly.
            from .text_input import tokenize_text
            tokenize_test_result = tokenize_text("this is a test", tokenizer_language, lemmatize=False)
            if tokenize_test_result is None:
                worked = False
    
        use_language_specific_tokenizer_for_entity_names = request.form['language_specific_tokenizer_for_entity_names'].strip()
        if use_language_specific_tokenizer_for_entity_names == "true":
            use_language_specific_tokenizer_for_entity_names = True
        else:
            use_language_specific_tokenizer_for_entity_names = False
        
        if "lemmatize" in request.form and request.form["lemmatize"] == "true":
            if tokenizer_language == "whitespace":
                flash("Can not use lemmatization for 'whitespace' language code setting. A supported language needs to be specified in the tokenization settings.", "danger")
                worked = False
                
            lemmatize = True
        else: # if checkbox is unchecked, the "lemmatize" element is not part of the post
            lemmatize = False
            
        if "remove_diacritics" in request.form and request.form["remove_diacritics"] == "true":
            remove_diacritics = True
        else: # if checkbox is unchecked, the "remove_diacritics" element is not part of the post
            remove_diacritics = False
    
        if worked:
            settings.wikidata_path = wikidata_path
            settings.spacy_tokenizer_language_code = tokenizer_language # TODO Rename now that more tokenizers are supported
            settings.use_language_specific_tokenizer_for_entity_names = use_language_specific_tokenizer_for_entity_names
            settings.lemmatize = lemmatize
            settings.remove_diacritics = remove_diacritics
            Memory.get_instance().save_settings()
            Memory.get_instance().invalidate_tokenization_cache()
            flash("Settings saved.", "success")
        else:
            flash("Saving settings did not work.", "danger")
    
    return render_template("settings/settings.html", 
                            settings=Memory.get_instance().get_settings(),
                            supported_languages=", ".join(Preprocessing.get_valid_languages()))

