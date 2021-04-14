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
from flask import jsonify, has_request_context, flash
from autom_labeling_library.preprocessing import Preprocessing
from .status import Status
from .memory import Memory


def try_method_return_json(method, report_error_status=False):
    """
        Runs the given method with a try block.
        If it succeeds, return a JSON object
        with success=true. Otherwise,
        returns a JSON object with success=false and
        debug information.
        
        If report_error_status is True, updates the Status singleton.
    """
    try:
        method()
        return jsonify({"successful": True})
    except Exception as e:
        print("Exception occured. The stacktrace: " + traceback.format_exc())
        if report_error_status:
                Status.get_instance().set_state_error()
                Status.get_instance().set_message(f"Exception occurred in background process: {str(e)} - {traceback.format_exc()}")
        return jsonify({"successful": False, 
                        "error_msg": str(e), 
                        "stacktrace": traceback.format_exc().replace("\n", "<br />")})

def get_document_from_memory(document_type):
    document = Memory.get_instance().get_document(document_type)
    if not document:
        flash("A {} document needs to be uploaded or inputed before it can be shown.".format(
                document_type), "warning")
        return None, redirect(url_for('text_input.index'))
    
    return document, None

def create_tokenizer(language_code):
    """
        Tries to create a tokenizer. Reports errors if this fails.
    """
    try:
        tokenizer = Preprocessing.create_tokenizer(language_code)
    except Exception as e:
        error_message = f"Could not load the tokenizer for language {language_code}. You might not have installed " + \
                  "the necessary, external tokenization library. Please, " + \
                  "see the documentation for more details." + \
                  f"The actual error was: '{e} - {traceback.format_exc()}'"
        if has_request_context():
            flash(error_message, "danger")
            return None
        else:
            raise Exception(error_message)
    return tokenizer
    

