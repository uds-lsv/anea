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

from enum import Enum

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)

class Status:
        
    @staticmethod
    def get_instance():
        return Status.instance
        
    def __init__(self):
        Status.instance = self
        
        self.state = StatusState.IDLE
        self.message = ""
        
    def set_message(self, message):
        self.message = message
        
    def clear_message(self):
        self.message = ""
        
    def set_state_processing(self):
        self.state = StatusState.PROCESSING
        
    def set_state_error(self):
        self.state = StatusState.ERROR
        
    def set_state_idle(self):
        self.clear_message()
        self.state = StatusState.IDLE
        
    
class StatusState(Enum):
    PROCESSING = "processing"
    ERROR = "error"
    IDLE = "idle"


bp = Blueprint('status', __name__, url_prefix='/status')

@bp.route('/', methods=('GET', 'POST'))
def status():    
    status = Status.get_instance()
    
    return jsonify({"state": status.state.value, 
                    "message": status.message})
    
@bp.route('/clear', methods=('GET', 'POST'))
def clear():    
    status = Status.get_instance()
    status.clear_message()
    status.set_state_idle();
    
    return jsonify({"state": status.state.value, 
                    "message": status.message})
