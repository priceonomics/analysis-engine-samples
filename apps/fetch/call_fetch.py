#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urllib2 import Request, urlopen
import json

# public api key
api_key = '34ed16e6b5f645c5a3cba39c75ee80b2'

# define the application endpoint
endpoint_template = 'https://api.engine.priceonomics.com/v1/apps/%s'
fetch_endpoint = endpoint_template % 'fetch'

# the outer portion of the fetch_input is common to all applications. the inner
# portion which specifies the url, country, etc is specific to fetch. note that
# only the url field is actually required for the call to complete, but the
# other fields allow for more control over how the request is executed.
fetch_input = {
    'async': False,
    'data': {
        'url': 'http://www.cbc.ca/books/2014/12/so-anyway.html',
        'country': 'CA',
        'obey_robots': True,
        'user_agent': 'Polite Crawler/1.0'
    }
}

# pass along the api key in the X-Access-Key header
headers = {
  'X-Access-Key': api_key,
}

# define the request and transform fetch_input from a python dict to json text
request = Request(fetch_endpoint, data=json.dumps(fetch_input), headers=headers)

# make the request and read the data returned in the resonse
response_body = urlopen(request).read()

# parse the response as json into a python dict
fetch_output = json.loads(response_body)

