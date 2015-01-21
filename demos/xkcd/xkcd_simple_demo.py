#!/usr/bin/env python
import requests
import json
import csv


# This is a public key. If you have a developer account, please change it to your own key! It will be faster!
# Dev accounts are free and available at https://engine.priceonomics.com/login
API_KEY = '34ed16e6b5f645c5a3cba39c75ee80b2'
HEADERS = {
    'X-Access-Key': API_KEY
    }  # Our API key is sent in the header
OUTER_SCHEMA = {
    'async': False,
    'data': None
    }
API_TEMPLATE = 'https://api.engine.priceonomics.com/v1/apps/%s'
OUTPUT_FILE_NAME = 'xkcd_results_test.csv'


def api_request(app_endpoint, request_data):
    values = OUTER_SCHEMA.copy()
    values['data'] = request_data
    return requests.post(API_TEMPLATE % app_endpoint, headers=HEADERS, data=json.dumps(values)).json()


# Get the comic names and URLS
# First we get the HTML for the archive page
url = 'http://xkcd.com/archive'
data = {
    'url': url,
    'country': 'US',
    'obey_robots': True,
    'user_agent': 'Priceonomics loves XKCD/1.0'
    }
response = api_request('fetch', data)
html = response['data']['content'].encode('utf-8')  # Extract the HTML

# Then we extract the links
# links can filter links based on a Regex pattern!
data = {
    'url': url,
    'content': html,
    'pattern': r'^http://xkcd.com/[0-9]+/'
    }  # http://xkcd.com/208/
links_dict = api_request('links', data)
comics = {}
for link in links_dict['data']['links']:
        comics[link['url']] = link['text']
urls = sorted(comics.keys(), key=lambda x: int(x.split('/')[3]))               # Let's sort our URL list nicely.
print len(urls),  'URLs found'

# With the URLs we collected, we go and get the social data
social_results = []
for url in urls:
    print 'Collecting social data for:', url                                 # Print the URL to keep the user posted
    data = {
        'url': url.encode('utf-8')
        }
    result = api_request('social', data)      # Perform a call to the Priceonomics social API
    social_results.append(result)             # Store the result

# Parse all the stored results into a list of flat dicts
rows = []                                                                         # Somewhere to store our rows
for result in social_results:                                                     # For each result dict
    if result['error'] is not False:
        continue
    url = result['data']['url']
    row = {
        'url': url,                                                            # We start with the metadata
        'comic_name': comics[url],
        'timestamp': result['timestamp']
        }
    for provider, metrics in result['data']['stats'].items():                     # Then grab the provider and metrics
        if metrics is not None:                                                   # and if there are metrics
            for metric, value in metrics.items():
                row['%s_%s' % (provider, metric)] = value                                  # We collect them for our row
    row_fixed = {k: v.encode('utf-8') if type(v) is unicode else v for k, v in row.items()}
    # Convert all strings to UTF-8 as the csv module does not handle unicode well
    rows.append(row_fixed)                                                # We store this row with the rest of the rows.

# Finally, we dump our results to a CSV file
with open(OUTPUT_FILE_NAME, 'wb') as f:
    keys = [
        'url',
        'comic_name',
        'timestamp',
        'twitter_share_count',
        'reddit_comment_total',
        'reddit_score_total',
        'reddit_submission_count',
        'linkedin_share_count',
        'google+_share_count',
        'stumbleupon_views',
        'facebook_comment_count',
        'facebook_like_count',
        'facebook_share_count',
        'pinterest_share_count'
        ]
    dict_writer = csv.DictWriter(f, keys)
    dict_writer.writeheader()
    dict_writer.writerows(rows)
