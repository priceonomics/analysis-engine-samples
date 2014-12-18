#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urllib2 import Request, urlopen
import json

# public api key
api_key = '34ed16e6b5f645c5a3cba39c75ee80b2'

# define the application endpoint
endpoint_template = 'https://api.engine.priceonomics.com/v1/apps/%s'
social_endpoint = endpoint_template % 'social'

# the outer portion of the social_input is common to all applications. the inner
# portion only specifies the url and is specific to social.
social_input = {
    'async': False,
    'data': {
        'url': 'http://priceonomics.com/how-much-does-it-cost-to-book-your-favorite-band/',
    }
}

# pass along the api key in the X-Access-Key header
headers = {
  'X-Access-Key': api_key,
}

# define the request and transform social_input from a python dict to json text
request = Request(social_endpoint, data=json.dumps(social_input), headers=headers)

# make the request and read the data returned in the resonse
response_body = urlopen(request).read()

# parse the response as json into a python dict
social_output = json.loads(response_body)

