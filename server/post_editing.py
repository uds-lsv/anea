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

from .util import try_method_return_json, get_document_from_memory

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)

bp = Blueprint('post_editing', __name__, url_prefix='/post_editing')

@bp.route('/change_one_label/<document_type:document_type>', methods=('POST','GET'))
def manually_change_one_autom_label_json(document_type):
    """ Changes one specific entry of the labels of the 
        given document, changing it to the new given label.
        token_index and new_label value are sent via
        post. Background, json function.
    """

    def lambda_function():
        token_index = int(request.form['token_index'])
        new_label = request.form['new_label']

        document, redirect = get_document_from_memory(document_type)
        if document is None:
            raise Exception("Could not load document for manually changing label value.");

        document.autom_labels[token_index] = new_label

    return try_method_return_json(lambda_function, report_error_status=True)
    
@bp.route('/change_all_label_one_token/<document_type:document_type>', methods=('POST','GET'))
def manually_change_all_autom_label_for_one_token_json(document_type):
    """ Change all occurences of the given token with the given
        label to the given new_label in the given document. 
        token, current_label and new_label are sent via post.
        Background, json function.
    """
    print("Hii");
    def lambda_function():
        request_token_index = int(request.form['token_index'])
        request_new_label = request.form["new_label"]
        
        document, redirect = get_document_from_memory(document_type)
        if document is None:
            raise Exception("Could not load document for manually changing label value.");

        request_token = document.tokens[request_token_index]
        request_current_label = document.autom_labels[request_token_index]
    
        for i, (token, current_label) in enumerate(zip(document.tokens, document.autom_labels)):
            if token == request_token and request_current_label == current_label:
                document.autom_labels[i] = request_new_label

    return try_method_return_json(lambda_function, report_error_status=True)

