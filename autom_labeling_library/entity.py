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

try:
    from fuzzywuzzy import fuzz
    FUZZY_THRESHOLD = 75
    FUZZY_THRESHOLD_LOWERCASED = 95
except ImportError:
    print('Install package \'fuzzywuzzy\' to enable fuzzy string matching (optional).')

class EntityObject:
    """
        Representing an entity in the underlying knowledge-base.
        E.g. 
    """
    
    def __init__(self, identifier):
        self.identifier = identifier
        
    def __str__(self):
        return "EntityObject({})".format(self.identifier)
    
class EntityName:
    """
        Representing a name/string that refers to an entity in the knowledge-base.
    """
    
    def __init__(self, entity_object, name, entity_extraction):
        self.entity_object = entity_object
        self.name = name # original name as extracted from the Knowledge Base
        self.tokenized_name = None # Is set by WikiDataNameExtraction when applying the properties
        #self.named_entity_type = named_entity_type # TODO Check constructor
        self.entity_extraction = entity_extraction # TODO Not all objects might have this set already
        # TODO do something fancier, use static SETTINGS object tokenization function
        # TODO do preprocessing on the names (e.g. stemming) when converting
        # to tokenization
    
    def get_label(self):
        return self.entity_extraction.get_label()
        
    def token_length(self):
        return len(self.tokenized_name)
        
    def create_split_token_objects(self):
        # needs to be tokenized first
        if hasattr(self, "entity_extraction"):
            return [EntityName(self.entity_object, token, self.entity_extraction) for token in self.tokenized_name]
               
    def matches_tokens(self, other_tokens):
        assert self.tokenized_name is not None, "tokenized_name has not been set"
        
        if len(self.tokenized_name) != len(other_tokens):
            return False
        
        match_casing_property = self.entity_extraction.get_property("match_casing") 
        if match_casing_property == "exact":
            matches_token_equality_function = EntityName.matches_token_equality_function_exact_casing
        elif match_casing_property == "ignore_first_character":
            matches_token_equality_function = EntityName.matches_token_equality_function_ignore_first_character_casing
        elif match_casing_property == "ignore_all":
            matches_token_equality_function = EntityName.matches_token_equality_function_ignore_all_casing
        elif match_casing_property == "fuzzy":
            matches_token_equality_function = EntityName.matches_token_equality_function_fuzzy
        
        for token, other_token in zip(self.tokenized_name, other_tokens):
            if not matches_token_equality_function(token, other_token):
                return False
        return True
        
    @staticmethod
    def matches_token_equality_function_exact_casing(this_token, other_token):
        return this_token == other_token
    
    @staticmethod
    def matches_token_equality_function_ignore_first_character_casing(this_token, other_token):
        return this_token[0].lower() == other_token[0].lower() and this_token[1:] == other_token[1:]
    
    @staticmethod
    def matches_token_equality_function_ignore_all_casing(this_token, other_token):
        return this_token.lower() == other_token.lower()
        
    @staticmethod
    def matches_token_equality_function_fuzzy(this_token, other_token):
        if fuzz.partial_ratio(this_token, other_token) >= FUZZY_THRESHOLD:
            return True
        return fuzz.ratio(this_token.lower(), other_token.lower()) >= FUZZY_THRESHOLD_LOWERCASED
    
    def __str__(self):
        return("EntityName({}-{}-{})".format(self.name, self.entity_object.identifier, self.get_label()))
        
    def __repr__(self):
        return self.__str__()

import string

class EntityNameCollection:
    
    def __init__(self, entity_names):
        self.entity_names = entity_names
        self._build_entity_name_index()
        pass

    def _build_entity_name_index(self):
        """
            For quicker look-up of possible entity_name matches, sort all
            EntityName objects by first token alphabetically (only 
            first token and lowercased). Then build
            a jump-list that allows to quickly return just a subset of all
            EntityName objects. Each letter of the alphabet obtains 
            one entry in the jump-list and is paired with the corresponding
            position of the first entry in the EntityName list that starts
            with this letter. Given a token that should be matched, only
            those EntityName objects need to be returned that start with this 
            letter.
            TODO: Implement a more flexible version with prefixes instead of
            just first letter.
        """
        if len(self.entity_names) == 0:
            raise Exception("There are no entity names on which to build a search index")
            
        self.entity_names.sort(key=lambda entity_name: entity_name.tokenized_name[0][0].lower())
        
        alphabet = list(string.ascii_lowercase)
        i = -1
        
        # fill jump list with markers to the end of the list first
        self.jump_list = []
        for letter in alphabet:
            self.jump_list.append((letter, len(self.entity_names)))
        self.jump_list.append(("-", len(self.entity_names)))
        
        for entity_idx, entity_name in enumerate(self.entity_names):
            try:
                first_letter = entity_name.tokenized_name[0][0].lower()
            except:
                raise Exception("Index building did not work for {} {}".format(entity_name, entity_name.tokenized_name))
            
            
            # letters < 'a' (e.g. comma or fullstop)
            if first_letter < alphabet[0]:
                continue
                
            if first_letter == alphabet[i]:
                continue
                        
            # next first letter is due
            while i < len(alphabet) and (first_letter > alphabet[i] or i == -1):
                i += 1
                
                # mark that the next letter starts at this position 
                # in the list of entity_names
                if i < len(alphabet):
                    assert self.jump_list[i][0] == alphabet[i] 
                    self.jump_list[i] = (alphabet[i],entity_idx)
                else: # end of alphabet, rest of non a-z letters come now
                    self.jump_list[-1] = ("-",entity_idx)
                
                 
        
            if i == len(alphabet):
                break
                
                

    
    def get_possible_entity_names(self, token):
        """
        Returns a list of EntityName objects that might match the given token.
        Many EntityName objects might not match, but no EntityName object
        that does match is left out.
        
        This implementation returns all EntityName objects that have
        the same first letter. Casing is ignored. If the token starts with
        a letter that is not part of a-z, either returns a list of < 'a'
        characters or a list of > 'z' characters.
        """
        try:
            first_letter = token[0].lower()
        except: 
            # An empty token should not happen. But in case something
            # broke in the tokenization, this is recoverable.
            print("Error: Empty token during matching!") # TODO: Make actual warning text or log
            if len(token) == 0:
                return []
        if first_letter < 'a':
            return self.entity_names[0:self.jump_list[0][1]]
        elif first_letter > 'z':
            return self.entity_names[self.jump_list[-1][1]:]
        else:
            jump_list_idx = ord(first_letter) - ord('a')

            entity_start_idx = self.jump_list[jump_list_idx][1]
            if jump_list_idx+1 < len(self.jump_list):
                entity_end_idx = self.jump_list[jump_list_idx+1][1]
                return self.entity_names[entity_start_idx:entity_end_idx]
            else:
                return self.entity_names[entity_start_idx:]
