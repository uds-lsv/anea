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

import copy
import subprocess

import numpy as np
from gensim.models import KeyedVectors
import fasttext

import conlleval

class Instance:
    
    def __init__(self, word, label, left_context, right_context):
        self.word = word
        self.label = label
        self.left_context = left_context
        self.right_context = right_context
        
    def __str__(self):
        return "{} ({}) [{},{}]".format(self.word, self.label, self.left_context, self.right_context)
    

class DataCreation:
    
    def __init__(self, input_separator=" ", padding_word_string="<none>"):
        self.input_separator = input_separator
        self.padding_word_string = padding_word_string
    
    def remove_label_prefix(self, label):
        """ CoNLL2003 distinguishes between I- and B- labels,
            e.g. I-LOC and B-LOC. Drop this distinction to
            reduce the number of labels/increase the number
            of instances per label.
        """
        if label.startswith("I-") or label.startswith("B-"):
            return label[2:]
        else:
            return label
        
    def pad_before(self, a_list, target_length):
        return (target_length - len(a_list)) * [self.padding_word_string] + a_list

    def pad_after(self, a_list, target_length):
        return a_list + (target_length - len(a_list)) * [self.padding_word_string]
    
    def load_connl_dataset(self, path, context_length, remove_label_prefix=False):
        with open(path, mode="r", encoding="utf-8") as input_file:
            lines = input_file.readlines()
        
        tokens = []
        labels = []
        for line in lines:
            line = line.strip()
        
            # skip begin of document indicator (used in some files)
            if line.startswith("-DOCSTART-"):
                continue
            
            # skip empty line / end of sentence marker (used in some files) 
            if len(line) == 0:
                continue
            
            # Skip marker (used in some files)
            if line == "--": 
                continue
                
            elements = line.split(self.input_separator)
            
            tokens.append(elements[0])
            # Take last element of this line as label, in between there might be e.g. the POS tag which we ignore here
            if len(elements) > 1: 
                labels.append(elements[-1])
            else:
                raise Exception(f"Line {line} did not provide a label. Elements are {elements}")
        
        assert len(tokens) == len(labels)
        
        instances = []
        for i, (token, label) in enumerate(zip(tokens, labels)):
            if remove_label_prefix:
                label = self.remove_label_prefix(label)

            left_context = tokens[max(0,i-context_length):i]
            right_context = tokens[i+1:i+1+context_length]

            left_context = self.pad_before(left_context, context_length)
            right_context = self.pad_after(right_context, context_length)
            instances.append(Instance(token, label, left_context, right_context))
        
        return instances
    
class Embedding:
    
    def __init__(self, padding_word_string="<none>", padding_word_vector=np.zeros(300), unknown_word_vector=np.zeros(300)):
        self.padding_word_string = padding_word_string
        self.padding_word_vector = padding_word_vector
        self.unknown_word_vector = unknown_word_vector
            
    def load_glove_840b(self):
        print("Loading embedding Glove840B")
        self.embedding_model = KeyedVectors.load_word2vec_format("/nethome/mhedderich/noise-prj/conll03/data/glove/glove.840B.300d.w2v_binary_format", binary=True)
        self.embedding_vector_size = 300
    
    def load_fasttext(self, language):
        print(f"Loading FastText for {language}")
        if language == "et":
            embedding_name = "wiki.et.bin"
        elif language == "en":
            embedding_name = "wiki.en.bin"
        elif language == "fy":
            embedding_name = "wiki.fy.bin"
        elif language == "et-cc":
            embedding_name = "cc.et.300.bin"
        elif language == "en-cc":
            embedding_name = "cc.en.300.bin"
        elif language == "fy-cc":
            embedding_name = "cc.fy.300.bin"
        elif language == "es-cc":
            embedding_name = "cc.es.300.bin"
        elif language == "yo-cc":
            embedding_name = "cc.yo.300.bin"

        embedding = fasttext.load_model(f"../data/fasttext/{embedding_name}")
        self.embedding_model = FastTextWrapper(embedding)
        self.embedding_vector_size = 300
    
    def use_connl_normalized_labels(self):
        self.label_name_to_label_idx_map = {"O": 0, "PER": 1, "ORG": 2, "LOC": 3, "MISC": 4}
        self._compute_label_idx_to_label_name_map()
    
    def use_conll_iob_labels(self):
        self.use_conll_bio_labels()
    
    def use_connl_bio_labels(self):
        self.label_name_to_label_idx_map = {"O": 0, "B-PER": 1, "I-PER": 2, "B-ORG": 3, "I-ORG": 4, 
                                            "B-LOC": 5, "I-LOC": 6, "B-MISC": 7, "I-MISC": 8}
        self._compute_label_idx_to_label_name_map()
        
    def use_specific_label_map(self, label_name_to_label_idx_map):
        self.label_name_to_label_idx_map = label_name_to_label_idx_map
        self._compute_label_idx_to_label_name_map()
       
    def _compute_label_idx_to_label_name_map(self):
        self.label_idx_to_label_name_map = {v:k for k,v in self.label_name_to_label_idx_map.items()}
    
    def get_num_labels(self):
        return len(self.label_name_to_label_idx_map)
    
    def label_name_to_label_idx(self, label):
        return self.label_name_to_label_idx_map[label]
    
    def label_idx_to_label_name(self, label_idx):
        return self.label_idx_to_label_name_map[label_idx]
    
    def label_name_to_vector(self, label):
        vector = np.zeros(self.get_num_labels())
        vector[self.label_name_to_label_idx_map[label]] = 1
        return vector
        
    def word_to_embedding(self, word):
        if word == self.padding_word_string:
            return self.padding_word_vector
        elif word in self.embedding_model:
            return self.embedding_model[word]
        else:
            return self.unknown_word_vector
    
    def labels_to_vectors(self, instances):
        """ Only convert labels """
        for instance in instances:
            instance.label_emb = self.label_name_to_vector(instance.label)
    
    def instance_to_vectors(self, instance):
        instance.word_emb = self.word_to_embedding(instance.word)
        instance.label_emb = self.label_name_to_vector(instance.label)
        instance.left_context_emb = [self.word_to_embedding(word) for word in instance.left_context]
        instance.right_context_emb = [self.word_to_embedding(word) for word in instance.right_context]
        
    def instances_to_vectors(self, instances):
        instances_with_vectors = copy.deepcopy(instances)
        for instance in instances_with_vectors:
            self.instance_to_vectors(instance)
            
        return instances_with_vectors
    
    def count_instances_without_target_embedding(self, instances):
        filtered_instances = [instance for instance in instances if instance.word in self.embedding_model]
        num_removed = len(instances) - len(filtered_instances)
        print("{} ({}%) instances where the target word is not in the embedding".format(num_removed, num_removed/len(instances)))
        
        ner_instances = [instance for instance in instances if instance.label != "O"]
        filtered_instances = [instance for instance in ner_instances if instance.word in self.embedding_model]
        num_removed = len(ner_instances) - len(filtered_instances)
        print("{} ({}%) instances with label != O where the target word is not in the embedding".format(num_removed, num_removed/len(ner_instances)))
    
    def instances_to_numpy_arrays(self, instances):
        xs = []
        ys = []
        for instance in instances:
            x = []
            x.extend(instance.left_context_emb)
            x.append(instance.word_emb)
            x.extend(instance.right_context_emb)
            xs.append(x)
            ys.append(instance.label_emb)
        xs = np.asarray(xs)
        ys = np.asarray(ys)
        return xs, ys
    
    @staticmethod
    def predictions_to_one_hot(predictions):
        labels = np.argmax(predictions, axis=-1)
        return np.eye(len(predictions[0]))[labels]
    
    def predictions_to_labels(self, predictions):
        label_idxes = np.argmax(predictions, axis=-1)
        return [self.label_idx_to_label_name(label_idx) for label_idx in label_idxes]

class FastTextWrapper:
    """ Wraps FastText to behave like a Gensim model,
        i.e. to allow access like model["word"]
    """
    
    def __init__(self, fasttext_model):
        self.fasttext_model = fasttext_model
    
    def __getitem__(self, word):
        return self.fasttext_model.get_word_vector(word)
    
    def __contains__(self, word):
        # FastText can create embeddings for all words. So
        # there are no OOVs for which the zero embedding
        # needs to be used (For the OOVs in the sense of
        # words that were not seen during training, one
        # needs to check it differently. But this is not
        # needed here).
        return True
    
    
    
class Evaluation:
    
    def __init__(self, separator=" "):
        self.separator = separator

    def check_word_orders(self, instances, words):
        for instance, word in zip(instances, words):
            assert(instance.word == word)
    
    def create_conll_evaluation_format(self, instances, words, prediction_labels):
        # CoNLL evaluation script (in perl) expects the format "word true_label predicted_label"
        assert len(instances) == len(prediction_labels)
        # sometimes, the order which our dataloader loads data differs from the sequential order of instance.
        # To make sure that we have the same order, we check the orders. (maybe it is not necessary?)
        self.check_word_orders(instances, words)

        output = ""
        for instance, prediction_label in zip(instances, prediction_labels):
            output += "{}{}{}{}{}\n".format(instance.word, self.separator, instance.label, self.separator, prediction_label)
        return output
    
    def evaluate_evaluation_string(self, connl_evaluation_string):            
        counts = conlleval.evaluate(connl_evaluation_string.split('\n'), {'delimiter': self.separator})
        return conlleval.report(counts)
    
    @staticmethod
    def extract_f_score(evaluation_output):
        """ Extracts from the output given by the CoNLL Perl script
            the value corresponding to the total F1 score.
        """
        line = evaluation_output.split("\n")[1]
        return float(line[-5:])
    
    def simple_evaluate(self, instances, prediction_labels):
        """ Returns just the f-score (for all NER types)
            Predictions is a label ("MISC", "ORG", etc. not a class vector!)
        """
        connl_evaluation_string = self.create_connl_evaluation_format(instances, prediction_labels)
        evaluation_output = self.evaluate_with_perl_script(connl_evaluation_string)
        return Evaluation.extract_f_score(evaluation_output)
