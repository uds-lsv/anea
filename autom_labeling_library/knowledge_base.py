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

import pickle
import json
import itertools

from .entity import EntityObject, EntityName
from .wikidata_api import search_subclasses
from .preprocessing import remove_diacritics

class WikiDataNameExtraction:
    
    def __init__(self, identifier, instance_of_property, depth, language_code, label, name=""):
        self._identifier = identifier
        self._instance_of_property = instance_of_property
        self._language_code = language_code
        self._depth = int(depth)
        self._label = label
        self._name = name  # a name (to show something nicer than the identifier)
        
        self._properties = {"active": True, "use_aliases": False, 
                            "remove_diacritics": False,
                            "filter_list": [], "minimum_length": -1,
                            "match_casing": "exact", 
                            "priority": 0, # if conclicts of entities with same length arrise, this priority decides which to use
                            "has_been_fully_extracted": False # marks if this Extraction has been run once over the whole knowledge base dump
                            }
        self._extracts = {"labels":[], "aliases":[]} # a map of two lists of EntityName objects, labels and aliases
        
        self._properties_changed = True
        
        if self._depth > 0:
            # this will query WikiData to get the subclasses for the entity
            # currently the number of subclasses is limited to 10000 to prevent timeouts
            self._all_instances = search_subclasses(self._instance_of_property, self._depth)
            import time  # TODO: Find a better way to circumvent the time out, at least not sleep every time
            time.sleep(2)
        else:
            self._all_instances = [self._instance_of_property]
    
    def get_identifier(self):
        return self._identifier
    
    def get_all_instances(self):
        return self._all_instances
        
    def set_identifier(self, identifier):
        self.identifier = identifier
        
    def set_identifier(self, identifier):
        self._identifier = identifier
        
    def get_depth(self):
        return self._depth
        
    def set_depth(self, new_depth):
        self._depth = new_depth
    
    def get_language_code(self):
        return self._language_code
        
    def get_instance_of_property(self):
        return self._instance_of_property
        
    def get_label(self):
        return self._label # TODO: Remove when transition is done
        
    def set_label(self, new_label):
        self._label = new_label # TODO: Remove when transition is done

    def set_name(self, name):
        self._name = name

    def get_name(self):
        """
        Returns the display name for this extraction. If no name
        is set (string length 0), then the identifier is returned
        :return: a string name
        """
        if len(self._name) > 0:
            return self._name
        else:
            return self._identifier

    def get_num_extracts(self):
        """ Returns the number of extracted entities. Does not count
            alias as separate extracts. Does not count splitted entity names
            as separate extracts.
        """
        if self._extracts == None:
            return -1
        return len(self._extracts["labels"]) # not counting aliases as these are a subset of the extracted entities
    
    def set_property(self, key, value):
        self._properties[key] = value
        self._properties_changed = True
        
    def get_property(self, key, default=None):
        if key not in self._properties:
            return default
        else:
            return self._properties[key]
        
    def add_entity_name(self, entity_obj, name, is_alias):
        """
        Add another EntityName object to the list of extracts
        """
        entity_name = EntityName(entity_obj, name, self)
        # TODO Make Thread safe
        if not is_alias:
            self._extracts["labels"].append(entity_name)
        else:
            self._extracts["aliases"].append(entity_name)
        
        self._properties_changed = True
    
    def _get_used_extracts(self):
        
        if self._extracts is None:
            print(f"None for {self.identifier}")
            raise Exception(f"is none {self.identifier}")
        
        if self._properties["use_aliases"]:
            return itertools.chain(self._extracts["labels"], self._extracts["aliases"])
        else:
            return self._extracts["labels"]
    
    def _tokenize_entity_names(self, entity_names, tokenizer):
        for entity_name in entity_names:
            entity_name.tokenized_name = tokenizer.tokenize(entity_name.name)
            entity_name.tokenized_name = [token for token in entity_name.tokenized_name if len(token) > 0] # some entitites have multiple whitespaces between tokens resulting in zero length tokens
    
    def _remove_diacritis(self, entity_names):
        # remove diacritics for all tokens
        for entity_name in entity_names:
            entity_name.tokenized_name = [remove_diacritics(token) for token in entity_name.tokenized_name]
    
    def get_extracts_for_matching(self, tokenizer, num_examples=-1):
        example_mode = num_examples != -1
        
        if not self._properties["active"] and not example_mode: # do not return empty list for examples
            return []
        
        # TODO optimize for less memory footprint, do functional generator approach
                
        selected_extracts = list(self._get_used_extracts())  #itertools.islice(selected_extracts,0,num_examples) 
        
        if num_examples > -1: # if num_examples > -1, we just want a couple of examples for the preview, otherwise full list
            selected_extracts = selected_extracts[:num_examples]# TODO fancier returns, dove-tailing labels and aliases, randomly picking, etc.  
        
        self._tokenize_entity_names(selected_extracts, tokenizer)
        
        print(self._properties.get("remove_diacritics", "Bling"))
        if self._properties.get("remove_diacritics"):
            print("removing diacricits")
            self._remove_diacritis(selected_extracts)
        
        if self._properties.get("split_tokens"):
            new_selected_extracts = []
            for entity_name in selected_extracts:
                if entity_name.token_length() > 1:
                    new_selected_extracts.extend(entity_name.create_split_token_objects())
            self._tokenize_entity_names(new_selected_extracts, tokenizer)
            selected_extracts.extend(new_selected_extracts)

        def matches_filter_list(entity_name):
            for filter_item in self._properties.get("filter_list"):
                if entity_name.matches_tokens(filter_item):
                    return True
            return False

        if self._properties.get("minimum_length") != -1:
            selected_extracts = filter(lambda extract: len(extract.name) >= self._properties.get("minimum_length"), selected_extracts)
        selected_extracts = filter(lambda extract: not matches_filter_list(extract), selected_extracts)
            
        if not example_mode:
            self._properties_changed = False
        
        return list(selected_extracts)

class WikiDataExtractor:
    
    def __init__(self, wikidata_path):
        self.wikidata_path = wikidata_path
        
    def extract(self, wiki_data_name_extractions, status=None):
        # TODO Parallelize
        with open(self.wikidata_path, "r") as input_file:
            
            for i, line in enumerate(input_file):
                
                if not status is None and i % 10000 == 0:
                    status.set_message(f"Extraction in progress. Checked {i} entries of the knowledge base")
                
                line = line[:-2] # remove newline and , after object definition
                
                if len(line) == 0:
                    continue
                
                try: 
                    json_obj = json.loads(line)  
                except Exception as e:
                    print(e)
                    continue
                
                for extraction in wiki_data_name_extractions:
                    # check if object is instance of this extraction id/property
                    if self.obj_is_instance_of(json_obj, extraction):
                        obj_identifier = json_obj["id"]
                        entity_obj = EntityObject(obj_identifier) 
                        label = self.get_label(json_obj, extraction.get_language_code())
                        aliases = self.get_aliases(json_obj, extraction.get_language_code())
                        
                        if not label is None:
                            extraction.add_entity_name(entity_obj, label, is_alias=False)
                                
                        if not aliases is None:
                            for alias in aliases:
                                extraction.add_entity_name(entity_obj, alias, is_alias=True)

                    # check if this object is the extraction id/property itself (e.g. Q5)
                    # use this to extract the name of the property
                    elif json_obj["id"] == extraction.get_instance_of_property():
                        name = self.get_label(json_obj, extraction.get_language_code())
                        if name is None:
                            name = self.get_label(json_obj, "en") # fallback to English
                        extraction.set_name(name)
        
        for extraction in wiki_data_name_extractions:
            extraction.set_property("has_been_fully_extracted", True)
    
    def get_label(self, obj, target_language):
        """ Get the name of the object in the specified language
        """
        if target_language in obj["labels"]:
            label = obj["labels"][target_language]["value"].strip()
            if len(label) > 0:
                return label
        return None

    def get_aliases(self, obj, target_language):
        """ Get alternative names in the specified language
        """
        if target_language in obj["aliases"]:
            aliases = []
            for alias in obj["aliases"][target_language]:
                alias = alias["value"].strip()
                if len(alias) > 0:
                    aliases.append(alias)
            if len(aliases) > 0:
                return aliases
        return None
        
    def get_property_of_obj(self, obj, prop_id):
        if not prop_id in obj["claims"]:
            return None
        
        props = obj["claims"][prop_id]
        prop_results = []
        for prop in props:
            if "datavalue" in prop["mainsnak"]:
                prop_results.append(prop["mainsnak"]["datavalue"]["value"]["id"])
        
        if len(prop_results) > 0:
            return prop_results
        else:
            return None

    def obj_is_instance_of(self, obj, other_extraction):
        props = self.get_property_of_obj(obj, "P31")
        if props is None:
            return False
        else:
            for idx in other_extraction.get_all_instances():
                if idx in props:
                    return True
            return False

