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

from autom_labeling_library import evaluation as evaluation_code # not object oriented because external code; renaming to avoid name conflict
from autom_labeling_library.analysis import ErrorAnalysis
from .memory import Memory, DocumentType

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)

bp = Blueprint('evaluation', __name__, url_prefix='/evaluation')

@bp.route('/<document_type:document_type>', methods=('GET', 'POST'))
def evaluation(document_type):
    document = Memory.get_instance().get_document(document_type)
    
    precheck_fail = precheck(document, document_type)
    if precheck_fail:
        return precheck_fail
    
    overall_metrics, per_tag_metrics = evaluate(document)
    
    return render_template("evaluation/evaluation.html", document_type=document_type, 
                                                         overall_metrics=overall_metrics,
                                                         per_tag_metrics=per_tag_metrics)
                                                         
@bp.route('/analysis/<document_type:document_type>/<int:num_errors>', methods=('GET', 'POST'))
def analysis(document_type, num_errors):
    document = Memory.get_instance().get_document(document_type)
    
    precheck_fail = precheck(document, document_type)
    if precheck_fail:
        return precheck_fail
    
    precision_errors, recall_errors = analyse(document, num_errors)
    
    return render_template("evaluation/analysis.html", document_type=document_type,
                                                       precision_errors=precision_errors,
                                                       recall_errors=recall_errors,
                                                       num_errors=num_errors)
    # TODO Implement analysis here
    

def precheck(document, document_type):
    if not document:
        flash("A {} document needs to be uploaded or inputed before evaluation.".format(
                document_type), "warning")
        return redirect(url_for('text_input.index', document_type=document_type))
        
    if document.gold_labels is None:
        flash(f"The {document_type} document has no gold labels.", "danger")
        return redirect(url_for('text_input.document_types'))
    
    if document.autom_labels is None:
        flash(f"The {document_type} document has not yet been automatically annotated.", "warning")
        return redirect(url_for("autom_annotation.index", document_type=document_type))

    return None

def evaluate(document):
    counts = evaluation_code.evaluate(document.gold_labels, document.autom_labels)
    return evaluation_code.metrics(counts)
    
def analyse(document, num_errors):
    error_analysis = ErrorAnalysis()
    precision_errors, recall_errors = error_analysis.analyse_errors(document, num_errors)
    return precision_errors, recall_errors
