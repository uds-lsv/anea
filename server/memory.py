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
import os
import pickle
import copy
from threading import Lock

from werkzeug.routing import BaseConverter

from autom_labeling_library.document import DocumentRawFormat

class Memory:
    """
    A Memory that stores objects in RAM so that they can be accessed
    between separate calls to the server. Also caches certain objects
    to save computation.
    
    Some very expensive to compute objects (namely the WikiDataNameExtraction
    objects are stored on disc and loaded on startup). All other objects
    are recomputed on start or when given by the user (and then cached).
    
    As the caching adds certain dependencies, objects should be 
    accessed and changed via the getter/setter/updated methods
    and not directly.
    """
        
    @staticmethod
    def get_instance():
        return Memory.instance
        
    def __init__(self, app):
        Memory.instance = self
        
        self._app = app
        
        self._extraction_entries = [] 
        
        self._documents = None # loaded from disk or created empty if does not exist yet
        self._settings = None # loaded from disk or created default if does not exist yet
        
        self._lock_extraction_saving = Lock() # During saving, the extractions are temporarly set to null to store them in two separate files. Use lock to prevent errors when saving twice at the same time. TODO Refactor to not setting to null
        
        self._load_from_disk()
    
    def _load_from_disk(self):
        self._load_settings()
        self._load_documents()
        self._load_extractions()
    
    def _load_settings(self):
        file_path = os.path.join(self._app.instance_path, "settings.pkl")
        if os.path.isfile(file_path):
            with open(file_path, "rb") as input_file:
                self._settings = pickle.load(input_file)
        else:
            self._settings = Settings.create_default_settings(default_directory=self._app.instance_path)
            self.save_settings()
        
    def save_settings(self):
        with self._app.open_instance_resource("settings.pkl", "wb") as output_file:                
            pickle.dump(self._settings, output_file)
    
    def get_settings(self):
        return self._settings
    
    def _load_documents(self):
        file_path = os.path.join(self._app.instance_path, "documents.pkl")
        self._documents = {}
        
        if os.path.isfile(file_path):
            with open(file_path, "rb") as input_file:
                document_information = pickle.load(input_file)
                
            from .text_input import process_input_text
            for document_type, document_raw_format, document_raw_text in document_information:
                process_input_text(document_raw_text, document_raw_format, document_type)
    
    def _save_documents(self):
        # do not store whole document objects as it contains references
        # to EntityName objects, etc. Difficult to store.
        to_store = []
        for document_type, document in self._documents.items():
            to_store.append([document_type, document.document_raw_format, document.raw_text])
        
        with self._app.open_instance_resource("documents.pkl", "wb") as output_file:                
            pickle.dump(to_store, output_file)
            
    def raw_documents_changed(self):
        """ Only storing raw document data """
        self._save_documents()
    
    def get_extractions(self, only_loaded=True):
        """ Return the WikiDataNameExtraction objects.
            Some extraction objects might be empty 
            (i.e. len(extraction.extracts)==0) because
            they have been created by the user but not
            yet run the extraction process.
        """
        extractions = []
        for extraction_entry in self._extraction_entries:
            if only_loaded and extraction_entry.state != ExtractionEntryState.LOADED:
                continue
            extractions.append(extraction_entry.extraction)
        return extractions
        
    def get_extraction_entries(self):
        return self._extraction_entries
    
    def _load_extractions(self):
        # load all extraction objects
        all_files = os.listdir(self._app.instance_path)
        self._extraction_entries = [] # get the identifiers for the extraction objects
        for f in all_files:
            if f.startswith("extraction_") and f.endswith("_config.pkl"):
                identifier = f[len("extraction_"):-len("_config.pkl")] # get the identifier in the filename
                self._extraction_entries.append(ExtractionEntry(identifier))
        
        for extraction_entry in self._extraction_entries:
            extraction_entry.load_extraction(self, load_configuration=True, load_extracts=False) # only load configuration for quicker start up
        self._sort_extraction_entries() 
    
    def _save_extraction(self, extraction_identifier, save_config = True, save_extracts = True):
        """
            Saves the specified extraction specified by the given extraction_identifier
            to disc. The extraction object must be part of self._extractions.
            Pickles the object into
            a file. Each extraction object gets its
            own file to be able to update them independently.
        """
        self._lock_extraction_saving.acquire()
        
        file_name_config, file_name_extracts = self._get_extraction_filename(extraction_identifier)
        
        # temporarily separate WikiDataNameExtraction object and its
        # extracts to store them separately
        extraction = self.get_extraction_from_identifier(extraction_identifier)
        extracts = extraction._extracts
        extraction._extracts = None # TODO: Implement saving in special method to not having to do that
        
        if save_config:
            with self._app.open_instance_resource(file_name_config, "wb") as output_file:
                pickle.dump(extraction, output_file)
                
        if save_extracts:
            with self._app.open_instance_resource(file_name_extracts, "wb") as output_file:
                pickle.dump(extracts, output_file)
        
        extraction._extracts = extracts
        
        self._lock_extraction_saving.release()
        
    def _get_extraction_filename(self, extraction_identifier, absolute=False):
        """ 
            Returns the config and extracts filename for a given identifier
        """
        file_name_config = "extraction_{}_config.pkl".format(extraction_identifier)
        file_name_extracts = "extraction_{}_extracts.pkl".format(extraction_identifier)
        
        if absolute:
            file_name_config = os.path.join(self._app.instance_path, file_name_config)
            file_name_extracts = os.path.join(self._app.instance_path, file_name_extracts)
            
        return file_name_config, file_name_extracts
        
    def get_extraction_from_identifier(self, identifier):
        """ Returns the extraction that has this (assumed unique)
            identifier.
        """
        return self.get_extraction_entry_from_identifier(identifier).extraction
    
    def update_extraction_identifier(self, extraction):
        """ The properties of an extraction might be changed in a way that
            it needs a new identifier (e.g. if the label is changed).
            This method gets a new identifier and renames the stored files correspondingly.
        """
        old_identifier = extraction.get_identifier()
        new_identifier = self._get_new_extraction_identifier(extraction.get_language_code(),
                                                         extraction.get_label(),
                                                         extraction.get_instance_of_property())
        if old_identifier == new_identifier:
            raise Exception(f"Old identifier {old_identifier} is equal to the new one. Should not have tried to update it.")
        
        # update extraction entry
        for extraction_entry in self._extraction_entries:
            if extraction_entry.identifier == old_identifier:
                assert extraction_entry.extraction == extraction
                extraction_entry.identifier = new_identifier
        
        old_file_name_config, old_file_name_extracts = self._get_extraction_filename(old_identifier, absolute=True)
        new_file_name_config, new_file_name_extracts = self._get_extraction_filename(new_identifier, absolute=True)
        
        os.rename(old_file_name_config, new_file_name_config)
        os.rename(old_file_name_extracts, new_file_name_extracts)   
        
        self._sort_extraction_entries()  
        
        extraction.set_identifier(new_identifier)   
        
    def get_extraction_entry_from_identifier(self, identifier):
        """ Returns the extraction entry that has this (assumed unique)
            identifier.
        """
        for extraction_entry in self._extraction_entries:
            if extraction_entry.identifier == identifier:
                assert extraction_entry.identifier == extraction_entry.extraction.get_identifier()
                return extraction_entry
        raise Exception(f"No extraction with identifier {identifier} found in the list of extractions")
    
    def _sort_extraction_entries(self):
        """ Sorts the extraction entries to the assumed order.
        """
        self._extraction_entries.sort(key=lambda extraction_entry: extraction_entry.identifier) # sorting important to ensure correct working of get new identifier function

    
    def add_extraction_entry(self, new_extraction):
        """ Add another extraction object to the 
            Memory. Will save the object to disc.
            Invalidates cached tokens_and_labels.
        """
        assert new_extraction.get_identifier() is None, "Identifier of new extraction has already been set in the past"
        identifier = self._get_new_extraction_identifier(new_extraction.get_language_code(),
                                                         new_extraction.get_label(),
                                                         new_extraction.get_instance_of_property())
        new_extraction.set_identifier(identifier)
        new_extraction_entry = ExtractionEntry(identifier)
        new_extraction_entry.extraction = new_extraction
        new_extraction_entry.state = ExtractionEntryState.LOADED
        self._extraction_entries.append(new_extraction_entry)
        self._sort_extraction_entries() #TODO: Make this one method with the previous and replace all similar uses in this file
        self._save_extraction(identifier)
        self.invalidate_autom_annotation_cache()
        
    def _get_new_extraction_identifier(self, language_code, named_entity, instance_of_property):
        """
            Returns a possible identifier for an extraction with the given 
            "instance_of_property", "language_code" and "named_entity". Will
            have the format [language_code][named_entity][instance_of_property][X]
            where X is a counter starting at 1 depending how many of this
            type have already been created.
        """
        x = 1

        if instance_of_property == "stopwords": 
            new_identifier = f"{language_code}-{instance_of_property}-{x}"
        else:
            new_identifier = f"{language_code}-{named_entity}-{instance_of_property}-{x}"
        
        # assumes that self._extractions is sorted by identifier
        for extraction_entry in self._extraction_entries:
 
            if extraction_entry.identifier == new_identifier:
                x += 1
                if instance_of_property == "stopwords": 
                    new_identifier = f"{language_code}-{instance_of_property}-{x}"
                else:
                    new_identifier = f"{language_code}-{named_entity}-{instance_of_property}-{x}"
       
        return new_identifier
    
    def updated_extractions(self, updated_extractions, 
                            changed_config = True, changed_extracts = True):
        """
            Tell the Memory system that the 
            given extraction objects have changed. Will
            trigger an update of the saved extraction objects.
            Invalidates cached tokens_and_labels.
        """
        for extraction in updated_extractions:
            self._save_extraction(extraction.get_identifier(), save_config=changed_config, 
                                             save_extracts=changed_extracts)
                    
        self.invalidate_autom_annotation_cache()        
    
    def get_document(self, document_key):
        if document_key in self._documents:
            return self._documents[document_key]
        else:
            return None
        
    def set_document(self, document_key, document):
        assert document_key in DocumentType, "Unsupported document type {}".format(document_key)
        self._documents[document_key] = document
    
    def invalidate_tokenization_cache(self):
        self._load_documents()
    
    def invalidate_autom_annotation_cache(self, documents=None):
        """ Invalidation of automatic annotation.
            Currently deactivated as the user might do manual 
            changes and these would then be lost.
        """
        if documents == None:
            documents = self._documents.values()
        
        # Deactivated caching invalidation 
        # for document in documents:
        #     document.autom_labels = None
        #     document.matches = None

class DocumentType(Enum):   
# TODO Move to own file
    UNLABELED_INPUT = "unlabeled_input"
    DEVELOPMENT = "development"
    TEST = "test"

class DocumentTypeConverter(BaseConverter):

    def to_python(self, value):
        return DocumentType(value)

    def to_url(self, value):
        return str(value.value)

def document_type_to_readable_name(document_type):
    if document_type == DocumentType.UNLABELED_INPUT:
        return "Unlabeled Text"
    if document_type == DocumentType.DEVELOPMENT:
        return "Development Text"
    if document_type == DocumentType.TEST:
        return "Fine-Tuning Text"
        
class Settings:
    # TODO Move this to settings.py
    @staticmethod
    def create_default_settings(default_directory):
        settings = Settings()
        settings.wikidata_path = os.path.join(default_directory, "wikidata_dump.json")
        settings.spacy_tokenizer_language_code = "whitespace"
        settings.use_language_specific_tokenizer_for_entity_names = False
        settings.lemmatize = False
        settings.remove_diacritics = False
        return settings
                
class ExtractionEntry:
    """ Represents a WikiDataNameExtraction in the Memory.
        Implements loading and storing of the Extraction.
        Can load the configuration and the extracts of an Extraction
        separately to allow quicker starting time (by only loading
        configurations first) and a smaller memory footprint
        (by not loading the extractions for unsed Extraction objects)
    """
    
    def __init__(self, identifier):
        self.identifier = identifier
        self.extraction = None
        self.state = ExtractionEntryState.NOT_LOADED
        
    
    def load_extraction(self, memory, load_configuration, load_extracts):
        """ Loads (unpickles) the saved extraction object
        """        
        if load_configuration:
            assert self.extraction is None, f"Configuration of Extraction {self.identifier} has already been loaded"
            
            file_name_config = "extraction_{}_config.pkl".format(self.identifier)
            with memory._app.open_instance_resource(file_name_config, "rb") as input_file:
                self.extraction = pickle.load(input_file)   
                self.extraction._extracts = None # override default initalization  
                assert self.extraction.get_identifier() == self.identifier              
        
        if load_extracts:
            assert not self.extraction is None, f"Configuration of Extraction {self.identifier} has not been loaded, yet"
            assert self.extraction._extracts is None
            assert self.state != ExtractionEntryState.LOADED
            assert self.state != ExtractionEntryState.LOADING # TODO Is here proper error handling necessary?
            file_name_extracts = "extraction_{}_extracts.pkl".format(self.identifier)    
            with memory._app.open_instance_resource(file_name_extracts, "rb") as input_file:
                self.state = ExtractionEntryState.LOADING
                extracts = pickle.load(input_file)
                assert not extracts is None 
                self.extraction._extracts = extracts
            
            # TODO: Do not pickle the old extraction object in the first place
            # that is linked here. Different extraction objects due to the 2step pickling process
            for entity_name in self.extraction._extracts["labels"]:
                entity_name.entity_extraction = self.extraction
            for entity_name in self.extraction._extracts["aliases"]:
                entity_name.entity_extraction = self.extraction
                
            self.extraction._properties_changed = True # Force tokenization
            self.state = ExtractionEntryState.LOADED

            if self.extraction._extracts is None:
                raise Exception(f"Failed to load extracts for {self.identifier}")
            
    def unload_extraction(self, memory):
        assert not self.extraction._extracts is None
        self.extraction._extracts = None
        self.state = ExtractionEntryState.NOT_LOADED


class ExtractionEntryState(Enum):
    """ State that defines if the extracts of an extraction have already been loaded
    """
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    
