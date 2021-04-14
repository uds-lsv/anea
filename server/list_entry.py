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

from autom_labeling_library.knowledge_base import WikiDataNameExtraction
from autom_labeling_library.entity import EntityName, EntityObject
from .memory import Memory
from .knowledge_base import valid_extract_input_specification

import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

bp = Blueprint('list_entry', __name__, url_prefix='/list_entry')

@bp.route('/', methods=('GET', 'POST'))
def index():    
    return redirect(url_for('list_entry.list_entry_form'))

@bp.route('/list_entry_form', methods=('GET', 'POST'))
def list_entry_form():
    """
        Form to manually enter a list of EntityNames
    """
    
    if request.method == 'POST':
        manual_list = request.form['manual_list']
        instance_of_property = "manual_entry"
        label = request.form['label'].strip()
        language_code = request.form['language_code'].strip()
        
        if not valid_extract_input_specification(instance_of_property, 0, language_code, label):
            return redirect(url_for('list_entry.list_entry_form'))
        
        #identifier = Memory._get_new_extraction_identifier(language_code, label, "manual_entry")
        extraction = WikiDataNameExtraction(None, instance_of_property, 0, language_code, label) # identifier set by Memory
        Memory.get_instance().add_extraction_entry(extraction)
        
        entity_object = EntityObject("Manual Entry")
        for line in manual_list.split("\n"):
            name = line.strip()
            extraction.add_entity_name(entity_object, name, is_alias=False)
        
        extraction.set_property("has_been_fully_extracted", True)
        Memory.get_instance().updated_extractions([extraction])
        
        flash("Added manualy entered list.", "success")
        return redirect(url_for('knowledge_base.list_extracts'))
        
    return render_template('list_entry/list_entry_form.html')
 
