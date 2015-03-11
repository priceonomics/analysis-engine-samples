#!/usr/bin/env pytho

import requests
from copy import deepcopy
import json
import time
import csv
import sys

# public api key
api_key = '34ed16e6b5f645c5a3cba39c75ee80b2'
url_template = 'https://api.engine.priceonomics.com/v1/apps/%s'

if len(sys.argv) < 2:
    print 'Usage: ./call_keywords_csv.py [input_file]'
    print 'Output will be in "keywords.csv"'
    sys.exit(1)

filename = sys.argv[1]

print 'Analyzing "%s" for keywords...' % filename

with open(filename) as f:
    content = f.read()

input_keywords = {
    'content': content,
}

input_outer = {
    'async':False,
    'data':None,
}

headers = {
    'X-Access-Key': api_key,
}

input_full = deepcopy(input_outer)
input_full['data'] = input_keywords

t0 = time.time()
r = requests.post(url_template % 'keywords', headers=headers, data=json.dumps(input_full))

output_full = r.json()

with open('keywords.csv', 'w') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)

    for i,k in enumerate(output_full['data']['keywords']):
        keyword, relevance = k['keyword'], k['relevance']
        writer.writerow([keyword.encode('utf-8'), relevance])
