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

import numpy as np

import keras
from keras.models import Model
from keras.callbacks import Callback
from keras.layers import Input, Dense, LSTM, GRU, Bidirectional, Dropout

from ner_datacode import DataCreation, Embedding, Evaluation
from experimentalsettings import ExperimentalSettings

# CHANGE CONFIG FILE HERE FOR DIFFERENT SETUPS
# CONFIG FILES ARE STORED IN THE ../config DIRECTORY
SETTINGS = ExperimentalSettings.load_json("ner_neural_03_et_2xdata_01") 

embedding = Embedding()
if SETTINGS["EMBEDDING"] == "glove":
    embedding.load_glove_840b()
elif SETTINGS["EMBEDDING"] == "fasttext-et":
    embedding.load_fasttext("et")
elif SETTINGS["EMBEDDING"] == "fasttext-en":
    embedding.load_fasttext("en")
elif SETTINGS["EMBEDDING"] == "fasttext-fy":
    embedding.load_fasttext("fy")
elif SETTINGS["EMBEDDING"] == "fasttext-cc-et":
    embedding.load_fasttext("et-cc")
elif SETTINGS["EMBEDDING"] == "fasttext-cc-en":
    embedding.load_fasttext("en-cc")
elif SETTINGS["EMBEDDING"] == "fasttext-cc-fy":
    embedding.load_fasttext("fy-cc")
elif SETTINGS["EMBEDDING"] == "fasttext-cc-es":
    embedding.load_fasttext("es-cc")
elif SETTINGS["EMBEDDING"] == "fasttext-cc-yo":
    embedding.load_fasttext("yo-cc")

embedding.use_specific_label_map(SETTINGS["LABEL_MAP"])

def load_and_preprocess_data(path_to_data, embedding, input_separator=SETTINGS["DATA_SEPARATOR"]):
    data_creation = DataCreation(input_separator=input_separator)
    instances = data_creation.load_connl_dataset(path_to_data, SETTINGS["CONTEXT_LENGTH"], remove_label_prefix=False)

    embedding.count_instances_without_target_embedding(instances)
    
    instances_embedded = embedding.instances_to_vectors(instances)
    
    return instances_embedded

def create_data_matrix(instances_embedded):
    x, y = embedding.instances_to_numpy_arrays(instances_embedded)
    return x, y
    
train = load_and_preprocess_data(SETTINGS["PATH_TRAIN"], embedding)
if SETTINGS["USE_NOISY"]:
    train_distant = load_and_preprocess_data(SETTINGS["PATH_TRAIN_DISTANT"], embedding)
dev = load_and_preprocess_data(SETTINGS["PATH_DEV"], embedding)
test = load_and_preprocess_data(SETTINGS["PATH_TEST"], embedding)

def create_model():
    input_shape = (SETTINGS["CONTEXT_LENGTH"]*2+1, embedding.embedding_vector_size)

    feature_input_layer = Input(shape=input_shape, name="input_text")
    dropout1 = Dropout(SETTINGS["DROPOUT_1"])(feature_input_layer)
    if SETTINGS["RNN_TYPE"] == "LSTM":
        rnn = LSTM(SETTINGS["RNN_SIZE"])
    elif SETTINGS["RNN_TYPE"] == "GRU":
        rnn = GRU(SETTINGS["RNN_SIZE"])
    bi_rnn_layer = Bidirectional(rnn, merge_mode='concat', name="bi-rnn")(dropout1)
    dropout2 = Dropout(SETTINGS["DROPOUT_2"])(bi_rnn_layer)
    dense_layer = Dense(SETTINGS["DENSE_SIZE"], activation=SETTINGS["DENSE_ACTIVATION"], name="dense")(dropout2)
    dropout3 = Dropout(SETTINGS["DROPOUT_3"])(dense_layer)
    softmax_output_layer = Dense(embedding.get_num_labels(), activation='softmax', name="softmax_out")(dropout3)
    
    model = Model(inputs=[feature_input_layer], outputs=softmax_output_layer)
    model.compile(loss=keras.losses.categorical_crossentropy, optimizer="adam", metrics=['accuracy'])
    
    return model

class F1scores(Callback):

    def __init__(self, data, model, name, log_file=None, save_best_model_weights_file=None):
        super(F1scores, self).__init__()
        self.data = data
        self.model = model
        self.name = name
        self.log_file = log_file
        self.save_best_model_weights_file = save_best_model_weights_file
        self.best_f1 = -1

    def on_epoch_end(self, batch, logs={}):
        data_x, _ = create_data_matrix(self.data)
        predictions = self.model.predict(data_x)
        predictions = embedding.predictions_to_labels(predictions)
    
        evaluation = Evaluation(separator=SETTINGS["DATA_SEPARATOR"])
        connl_evaluation_string = evaluation.create_conll_evaluation_format(self.data, predictions)
        evaluation_output = evaluation.evaluate_with_perl_script(connl_evaluation_string)
        f1 = evaluation.extract_f_score(evaluation_output)
        
        logs[self.name] = f1
        if f1 > self.best_f1:
            if self.save_best_model_weights_file is not None:
                print(f"Saving model because on {self.name} new f1 {f1} is better than old f1 {self.best_f1}.")
                self.model.save_weights(self.save_best_model_weights_file)
            self.best_f1 = f1
        else:
            print(f"No improvement over f1 on {self.name} (best: {self.best_f1}, current: {f1}).")
        return self.best_f1, evaluation_output

class Logger(Callback):

    def __init__(self, filename):
        super(Logger, self).__init__()
        self.filename = filename
        self.epoch = 1
        self.need_init = True

    def on_epoch_end(self, batch, logs={}):
        if self.need_init:
            with open(self.filename, 'w') as fout:
                fout.write('epoch,')
                fout.write(','.join(sorted(logs)))
                fout.write('\n')
            self.need_init = False

        s = f"{self.epoch},"
        for key in sorted(logs):
            s += f'{logs[key]},'
        s = s[0:len(s) - 1] + '\n'
        with open(self.filename, 'a') as fout:
            fout.write(s)
        self.epoch += 1

def train_and_evaluate():      
    model = create_model()   
    train_data = train
    
    if SETTINGS["USE_NOISY"]:
        train_data = list(train_distant)
        train_data.extend(train)
    
    train_x, train_y = create_data_matrix(train_data)
    
    storage_directory = "../logs/"
    best_model_path = storage_directory + SETTINGS["NAME"] + "_best_model_on_dev_weights.h5"
    valid_f1 = F1scores(dev, model, 'dev_f1', save_best_model_weights_file=best_model_path)
    log = Logger(storage_directory + SETTINGS["NAME"] + '_training.log')
    
    model.fit(x=train_x,
          y=train_y,
          batch_size=SETTINGS["BATCH_SIZE"],
          epochs=SETTINGS["EPOCHS"],
          verbose=0,
          shuffle=not SETTINGS["USE_NOISY"],
          callbacks=[valid_f1, log])
          
    model.load_weights(best_model_path)

    _, test_eval_output = F1scores(test, model,
                         'test_f1').on_epoch_end(None)
    with open(storage_directory + SETTINGS["NAME"] + "_test_f1_on_best_dev_model.txt", "w") as out_file:
        out_file.write(f"{test_eval_output}\n")
    
train_and_evaluate()

