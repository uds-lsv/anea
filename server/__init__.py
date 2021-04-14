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
import sys

from flask import Flask, redirect, render_template

from .memory import Memory, DocumentTypeConverter, document_type_to_readable_name
from .status import Status

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev'
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    Memory(app) # initalize static Memory instance
    Status()
    
    # allow conversion of DocumentTypeEnum to String and back
    app.url_map.converters['document_type'] = DocumentTypeConverter
    # Insert conversion of DocumentTypEnum to readable representation into template system
    @app.context_processor
    def document_type_processor():
        return dict(document_type_to_readable_name=document_type_to_readable_name)
        
    
    sys.stderr = open(os.path.join(app.instance_path, "error.log"), 'a') # additional error log file, outputs might be buffered and only written to log after the server is stopped
    
    @app.route('/')
    def hello():
        return render_template("startpage.html")
    
    from . import knowledge_base
    app.register_blueprint(knowledge_base.bp)
    
    from . import list_entry
    app.register_blueprint(list_entry.bp)
    
    from . import stopwords
    app.register_blueprint(stopwords.bp)
        
    from . import text_input
    app.register_blueprint(text_input.bp)
    
    from . import text_output
    app.register_blueprint(text_output.bp)
    
    from . import autom_annotation
    app.register_blueprint(autom_annotation.bp)
    
    from . import post_editing
    app.register_blueprint(post_editing.bp)
    
    from . import evaluation
    app.register_blueprint(evaluation.bp)
    
    from . import settings
    app.register_blueprint(settings.bp)
    
    from . import status
    app.register_blueprint(status.bp)
    
    from . import helping
    app.register_blueprint(helping.bp)
    

    return app


