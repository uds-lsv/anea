# Neural NER Model for Low-Resource Settings

This is the implementation of a Bi-GRU classifier for NER using FastText embeddings.

## Model Parameters
We did a preliminary study to find good settings for a low-resource scenario. This was performed on held-out CoNLL03 data. To easily apply the model to many different languages, we used pretrained fastText embeddings trained on Wikipedia and CommonCrawl. They are available in [157 languages](https://fasttext.cc/docs/en/crawl-vectors.html). For the network architecture, we settled on a bidirectional Gated Recurrent Unit with a state size of 300 and a context size of one token to each side.  In the preliminary experiments, this smaller architecture performed better in the low-resource setting than more complex ones with a larger context, a Bi-LSTM or the LSTM-CRF architecture by Lample et al. (2016). The output is transformed using a ReLU layer of size 100 and then classified using a Softmax layer. Dropout of 0.2 is applied between all layers. The model was trained for 50 epochs with a batch size of 50 and Adam as optimizer. On the high-resource, full CoNLL03 dataset ($>$250k labeled tokens), both baselines achieve an F1 score of 87.

## Running the Model

The implementation is done in Python 3.7 and requires the the libraries keras, numpy, gensim and fasttext. The model is executed by running 

```
cd code
python ner_neural.py
```

The config directory contains the configurations for the different datasets and kinds of distant supervision. In ner_neural.py, you can change the configuration file used. Results are saved in the logs directory.

