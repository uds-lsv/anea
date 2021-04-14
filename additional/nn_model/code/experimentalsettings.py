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

import json

class ExperimentalSettings:
    """
    A class to store the settings or configurations of an experiment. 
    Mimics a dictionary but configuration
    settings are final after the ExperimentalSettings object is configured.
    First set all configurations, then call finalize. This will store
    the configuration in a file. Afterwards, the values from
    the configuration can be accessed.
    """
    
    def __init__(self, name):
        """
        name: Name of the file that stores the configuration
                once finalize() is called (.config is added).
        """
        self.settings = {"NAME":name}
        self.name = name
        self.finalized = False
    
    def __getitem__(self, key):
        """
        Can only be called once the object is finalized.
        """
        if self.finalized:
            return self.settings[key]
        else:
            raise Exception("ExperimentalSettings object has to be finalized before it can be read from.")
    
    def __setitem__(self, key, value):
        """
        Can only be called as long as the object is not finalized.
        """
        if not self.finalized:
            self.settings[key] = value
        else:
            raise Exception("ExperimentalSettings object is already finalized. Can no longer change.")
    
    def __contains__(self, key):
        """
        Can only be called once the object is finalized.
        """
        if self.finalized:
            return key in self.settings
        else:
            raise Exception("ExperimentalSettings object has to be finalized before it can be read from.")
    
    def finalize(self):
        """
        Writes the configuration to a file to make sure it is 
        persistently stored. Then allows to read from the file
        and blocks changes to the values.
        """
        # TODO: Check if file already exists?
        # TODO: Add date to filename?
        # TODO: Possibility to add "measurements" after finalization
        self.to_file()
        self.finalized = True
    
    def to_file(self):
        """ Save in old format to the corresponding config file
        """
        with open("../config/" + self.name + ".config", 'w') as f: # TODO Do not make this path hard coded
            for key in sorted(self.settings):
                f.write("{}: {}\n".format(key, self.settings[key]))
                
    def save_json(self):
        """ Save in new format (JSON) to the corresponding config file
        """
        with open("../config/" + self.name + ".json", 'w') as f:
            f.write(json.dumps(self.settings, indent=4, sort_keys=True))
    
    @staticmethod
    def load_json(name):
        print("Loading ExperimentalSettings {}".format(name))
        with open("../config/" + name + ".json", 'r') as f:
            file_content = f.read()
            settings = json.loads(file_content)
            
            if settings["NAME"] != name:
                raise ValueError("Name in json is specified as {} while the name is loaded from a file called {}".format(settings["NAME"], name))
            
            new_settings_object = ExperimentalSettings(name)
            new_settings_object.settings = settings
            new_settings_object.finalized = True
            return new_settings_object
 
