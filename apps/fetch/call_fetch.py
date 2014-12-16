#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urllib2 import Request, urlopen
import json

api_key = '34ed16e6b5f645c5a3cba39c75ee80b2'
endpoint_template = 'https://api.engine.priceonomics.com/v1/apps/%s'
fetch_endpoint = endpoint_template % 'fetch'

fetch_input = {
    'async': False,
    'data': {
        'url': 'http://www.cbc.ca/books/2014/12/so-anyway.html',
        'country': 'CA',
        'obey_robots': True,
        'user_agent': 'Polite Crawler/1.0'
    }
}

headers = {
  'X-Access-Key': api_key,
}

request = Request(fetch_endpoint, data=json.dumps(fetch_input), headers=headers)

response_body = urlopen(request).read()

fetch_output = json.loads(response_body)

