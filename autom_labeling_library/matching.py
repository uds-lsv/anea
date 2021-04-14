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

class Match:
    
    def __init__(self, match_start_pos, match_end_pos, match_entity_name):
        """
        match_start_pos: Start of the match (index starting with 0, included)
        match_end_pos: End of the match (excluded)
        """
        self.match_start_pos = match_start_pos
        self.match_end_pos = match_end_pos
        self.match_entity_name = match_entity_name
        
    def length(self):
        return self.match_end_pos - self.match_start_pos
        
    def __str__(self):
        return "Match({},{}:{})".format(self.match_entity_name, self.match_start_pos, self.match_end_pos)
    
    def __repr__(self):
        return self.__str__()

class MatchingAlgorithm:
    
    def __init__(self, entity_name_collection):
        self.entity_name_collection = entity_name_collection
        
    def match_tokens(self, tokens, status=None):
        matches = []
        
        for i in range(len(tokens)):
            if not status is None and i % 100 == 0:
                status.set_message("Performing matching. Checked {}% of the text.".format(int(i/len(tokens)*100)))
            
            for entity_name in self.entity_name_collection.get_possible_entity_names(tokens[i]): # Only use a subset of all entities (those that start with the same letter as the current token)
                if entity_name.token_length() > len(tokens) - i: # Near end of document, rest of tokens can be shorter than entity
                    continue
                    
                if entity_name.matches_tokens(tokens[i:i+entity_name.token_length()]): # check if entity name matches this token (and the following if entity name is longer than one token)
                    matches.append(Match(i, i+entity_name.token_length(), entity_name))
                    
        return matches
    
class MatchConflictGreedySolvingAlgorithm:
    """
        Solves the conflicts arrising from
        overlapping matches.
        This greedy implementation goes from start
        to end. If for a match, one or more other
        matches overlap, it takes the longest match.
    """
    
    def resolve_conflicts(self, matches):
        """ Resolves the conflicts in the given matches list.
            List is changed in places. List of matches must
            be sorted by match.match_start_pos.
        """
                
        i = 0 # using explicit index, because matches are changed inplace
        while i < len(matches):
            current_match = matches[i]
            
            conflicting = []
            conflict_end_pos = current_match.match_end_pos
            j = i+1
            # each match that starts at a position within the current_match
            # overlaps with current_match/is conflicting.
            # matches[j].match_start_pos > current_match.match_start_pos
            # is guaranteed because list of matches must be sorted.
            while j < len(matches) and matches[j].match_start_pos < conflict_end_pos:
                conflicting.append(matches[j])
                # one of the conflicting matches can itself conflict with other matches
                # include all in this conflicting. E.g. if current_match is "A", it conflicts
                # with "A B" and then "B" is added as well.
                conflict_end_pos = max(matches[j].match_end_pos, conflict_end_pos)
                j += 1
            
            # if there are conflicts
            if len(conflicting) > 0:

                # find longest match
                conflicting.append(current_match)
                longest_match_length = max([match.length() for match in conflicting])
                longest_matches = [match for match in conflicting if match.length() == longest_match_length]

                if len(longest_matches) == 1:
                    longest_match = longest_matches[0]
                else:
                    longest_match = max(longest_matches, key=lambda match: match.match_entity_name.entity_extraction.get_property("priority"))

                # longest match is saved from deletion
                conflicting.remove(longest_match) 
                
                # remove the conflicting matches
                for conflict in conflicting:
                    matches.remove(conflict)
            
            i += 1 
