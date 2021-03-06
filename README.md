# ANEA: Distant Supervision for Low-Resource Named Entity Recognition

ANEA is a tool to automatically annotate named entities in unlabeled text based on entity lists for the use as distant supervision.

Distant supervision allows obtaining labeled training corpora for low-resource settings where only limited hand-annotated data exists. However, to be used effectively, the distant supervision must be easy to gather. ANEA is a tool to automatically annotate named entities in texts based on entity lists. It spans the whole pipeline from obtaining the lists to analyzing the errors of the distant supervision. A tuning step allows the user to improve the automatic annotation with their linguistic insights without labelling or checking all tokens manually.

An example of the workflow can be seen in this [video](https://www.youtube.com/watch?v=eXwho2Pq6Eg). For more details, take a look at our [paper](https://arxiv.org/abs/2102.13129) (accepted at PML4DC @ ICLR'21). For the additional material of the paper, please check the subdirectory *additional* of this repository.


## Installation
ANEA should run on all major operating systems. We recommend the installation via conda or [miniconda](https://docs.conda.io/en/latest/miniconda.html):

```
git clone https://github.com/uds-lsv/anea

conda create -n anea python=3.7
conda activate anea
pip install spacy==2.2.4 Flask==1.1.1 fuzzywuzzy==0.18.0
```

For tokenizationa and lemmatization, a spacy language pack needs to be installed. Run the following command with the corresponding language code, e.g. en for English. Check https://spacy.io/usage for supported languages
```
python -m spacy download en
```

Download the Wikidata JSON dump from https://dumps.wikimedia.org/wikidatawiki/entities/ and extract it to the *instance* directory (this may take a while).

## Running
After the installation, you can run ANEA using the following commands on the command line

```
conda activate anea
./run.sh
```

Then open the browser and go to the address *http://localhost:5000/* If you run it for the first time, you should configure ANEA at the *Settings* tab. 

The ANEA (server) tool can run on a different machine than the browser of the user. It is just necessary that the user's computer can access the port 5000 on the machine that the ANEA server is running on (e.g. via ssh port forwarding or opening the correspoding port on the firewall).

## Support for Other Languages

ANEA uses Spacy for language preprocessing (tokenization and lemmatization). It currently supports English, German, French, Spanish, Portuguese, Italian, Dutch, Greek, Norwegian Bokm??l and Lithuanian. For Estonian, [EstNLTK](https://github.com/estnltk/estnltk}), version 1.6, is supported by ANEA. In that case, ANEA needs to be installed with Python 3.6. 

Text can also be preprocessed using external tools and then uploaded as whitespace tokenized text or in the CoNLL format (one token per line).

Other external preprocessing libraries can be added directly to ANEA by implementing a new Tokenizer class in autom_labeling_library/preprocessing.py (you can take a look at EstnltkTokenizer as an example) and adding it to the Preprocessing class. If you encounter any issues, just contact us.

## Citation

If you use this tool, please cite us:

```
@article{hedderich21ANEA,
  author    = {Michael A. Hedderich and
               Lukas Lange and
               Dietrich Klakow},
  title     = {{ANEA:} Distant Supervision for Low-Resource Named Entity Recognition},
  journal   = {CoRR},
  volume    = {abs/2102.13129},
  year      = {2021},
  url       = {https://arxiv.org/abs/2102.13129},
  archivePrefix = {arXiv},
  eprint    = {2102.13129},
}
```

## Development, Support & License

If you encounter any issues or problems when using ANEA, feel free to raise an issue on Github or contact us directly (mhedderich [at] lsv.uni-saarland [dot] de). We welcome contributes from other developers. 

ANEA is licensed under the Apache License 2.0.




