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

import requests 
  
URL = "https://query.wikidata.org/sparql"

def search_subclasses(identifier, depth):
    query = ('PREFIX gas: <http://www.bigdata.com/rdf/gas#> '
             'SELECT ?item ?linkTo { '
             'SERVICE gas:service { '
            'gas:program gas:gasClass "com.bigdata.rdf.graph.analytics.SSSP" ; '
             f'gas:in wd:{identifier} ; '
             'gas:traversalDirection "Reverse" ; '
             'gas:out ?item ; '
             'gas:out1 ?depth ; '
             f'gas:maxIterations {depth} ; '
             'gas:maxVisited 10000 ; '
             'gas:linkType wdt:P279 .'
             '} OPTIONAL { ?item wdt:P279 ?linkTo }}')
    
    PARAMS = {'query':query, 'format': 'json'}
    r = requests.get(url = URL, params = PARAMS)
    data = r.json() 
    
    subclasses = [identifier]
    for item in data['results']['bindings']:
        value = item['item']['value']
        value = value.replace('http://www.wikidata.org/entity/', '')
        subclasses.append(value)
    return list(set(subclasses))
