#!/usr/bin/env python

import datetime
import sys
import threading
import Queue
import time

import gevent
import requests
import ujson as json
from lxml import html
from sqlalchemy.orm import Session
from sqlalchemy import exc

from datamodel import BuzzfeedIndex, BuzzfeedArticle, BuzzfeedSource, BuzzfeedLink, engine

api_key = '34ed16e6b5f645c5a3cba39c75ee80b2' # public API key, register an account for a private key with higher limits and better performance
endpoint_template = 'https://api.engine.priceonomics.com/v1/apps/%s'

class APIException(Exception):
    pass

class BuzzfeedException(Exception):
    pass

class QueueConsumer(threading.Thread):
    def __init__(self, queue, id, crawl_index):
        self.queue = queue
        self.id = id
        self.crawl_index = crawl_index
        super(QueueConsumer, self).__init__()
        self._stop = threading.Event() # this is a flag to indicate that the thread should stop after its current iteration

    def end(self):
        # set the stop flag so that we can exit gracefully
        if not self._stopped():
            print 'stopping thread...'
            self._stop.set()

    def _stopped(self):
        # check whether the stop flag has been triggered
        return self._stop.isSet()

    def join(self, timeout=None):
        # override the join() function to trigger the end of the thread
        self.end()
        super(QueueConsumer, self).join(timeout)

    def run(self):
        # this function gets run once the thread is started and contains the main thread loop for consuming tasks from the queue and processing them
        print 'starting thread...'
        self.set_up()

        # main thread loop runs until the stop flag is set
        while not self._stopped():
            try:
                # get item from the queue and process it
                item = self.queue.get_nowait()
                self.process(item)
            except Queue.Empty:
                # whoops, queue is empty, let's wait a short period of time and try again
                time.sleep(0.1)
                continue
            except APIException as e:
                # whoops, the API gave an unexpected error. let's put the job back on the queue and try again later
                print 'Encoutered APIException, putting item back on the queue %s: %s\n%s' % (e.__class__.__name__, e, item)
                self.queue.put(item)
            except Exception as e:
                # whoops, the thread loop encountered an unexpected error. this error probably won't resolve itself (unlike API errors), so just give up on this task
                print 'QueueConsumer failed to process item due to exception %s: %s\n%s' % (e.__class__.__name__, e, item)

        self.tear_down()

    def set_up(self):
        # make sure we have a database session for each thread
        self.session = Session(engine)

    def tear_down(self):
        # close the database session when the thread finishes
        self.session.close()

    def process(self, item):
        # process the queue item according to whatever function is specified in the task
        func = getattr(self, item['function'])
        func(item)

    def api_request(self, app_slug, data, async=False):
        # generic function for synchronously invoking any app on the analysis engine
        request_headers = {
            'X-Access-Key':  api_key,
        }

        request_input = {
            'async': async,
            'data': data,
        }

        response = requests.post(endpoint_template % app_slug, headers=request_headers, data=json.dumps(request_input))

        if response.status_code != 200:
            print response.text
            raise APIException('Received %d HTTP error from the API.' % response.status_code)

        return response.json()['data']

    def archive(self, item):
        # crawl and handle archive pages
        input_data = {
            'url': item['url'],
            'country': 'US',
            'obey_robots': True,
        }

        response_data = self.api_request('fetch', input_data)
        if response_data['response'] == 599:
            # this happens from time to time with Fetch. still got some bugs to work out!
            raise APIException('Fetchcore screwed up.')
        if response_data['response'] >= 400:
            # BuzzFeed has failed us
            raise BuzzfeedException('Received %d HTTP error from Buzzfeed.' % response_data['response'])
        
        # parse the HTML into a tree for analysis
        tree = html.fromstring(response_data['content'].encode('utf-8'))
        tree.make_links_absolute(item['url'])

        # get a list of all articles listed on the page
        articles = tree.xpath('//ul[contains(@class, "flow")]/li/a')
        articles_and_items = []

        # for each article, extract useful information, create a database item, and create a queue task
        for a in articles:
            title = a.text_content().strip()
            url = a.get('href')
            new_item = {
                'function': 'article',
                'url': str(url),
            }
            article = BuzzfeedArticle(
                crawl_index=self.crawl_index,
                posted=item['date'],
                title=title,
                url=str(url),
            )
            self.session.add(article)

            articles_and_items.append((article, new_item))

        # write the new rows to the database
        try:
            self.session.commit()
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            print 'Failed to commit BuzzfeedArticles to database - %s: %s' % (e.__class__.__name__, e)
            return

        # put the new tasks on the queue (which we only want to do if the database commit went okay)
        for article,new_item in articles_and_items:
            new_item['article_id'] = article.id
            self.queue.put(new_item)
        

    def article(self, item):
        # crawl and handle article pages
        input_data = {
            'url': item['url'],
            'country': 'US',
            'obey_robots': True,
        }

        response_data = self.api_request('fetch', input_data)
        if response_data['response'] == 599:
            # this happens from time to time with Fetch. still got some bugs to work out!
            raise APIException('Fetchcore screwed up.')
        if response_data['response'] >= 400:
            # BuzzFeed has failed us
            raise BuzzfeedException('Received %d HTTP error from Buzzfeed.' % response_data['response'])

        # parse the HTML into a tree for analysis
        tree = html.fromstring(response_data['content'].encode('utf-8'))
        tree.make_links_absolute(item['url'])

        # get a list of all attribution strings on the article page
        attribution_elements = tree.xpath('//*[contains(@class, "sub_buzz_source_via") or contains(@class, "sub_buzz_grid_source_via")]')

        # get the database row corresponding to the article we're currently crawling
        article = self.session.query(BuzzfeedArticle).filter(BuzzfeedArticle.id == item['article_id']).scalar()
        input_data = {
            'url': item['url'],
        }

        # send a social request to get sharing stats for this article
        response_data = self.api_request('social', input_data)
        article.social = response_data
        self.session.add(article)

        sources_and_links = []

        # for each attribution element, extract the source text and links
        for e in attribution_elements:
            links = e.xpath('.//a/@href')
            source_text = e.text_content().strip()
            source = BuzzfeedSource(
                crawl_index=self.crawl_index,
                text=source_text,
                article_id=item['article_id'],
            )
            self.session.add(source)
            sources_and_links.append((source, links))

        # commit the sources to the database
        try:
            self.session.commit()
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            print 'Failed to commit BuzzfeedSources to database - %s: %s' % (e.__class__.__name__, e)
            return

        # for each link in each source, create a link database item
        for source,links in sources_and_links:
            for link in links:
                buzzfeed_link = BuzzfeedLink(
                    crawl_index=self.crawl_index,
                    source_id=source.id,
                    url=str(link),
                )
                self.session.add(buzzfeed_link)

        # commit the links to the database
        try:
            self.session.commit()
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            print 'Failed to commit BuzzfeedLinks to database - %s: %s' % (e.__class__.__name__, e)
            return
        
if __name__ == '__main__':
    # number of simultaneous threads to use to query the Analysis Engine
    num_threads = 5

    # how far back to go in BuzzFeed's archive
    duration = datetime.timedelta(weeks=1)
    frequency = datetime.timedelta(days=1)

    today = datetime.datetime.utcnow()
    end_date = today - frequency
    start_date = end_date - duration

    # BuzzFeed has a convenient archive path
    buzzfeed_archive_template = 'http://www.buzzfeed.com/archive/%d/%d/%d'

    # let's use a simple FIFO queue for handing out tasks to our crawl threads
    queue = Queue.Queue()
    session = Session(engine)

    # create a crawl index so we can track everything from we add to the database from this crawl
    crawl_index = BuzzfeedIndex()
    session.add(crawl_index)
    session.commit()

    # generate crawl tasks and put them on the queue
    date = start_date
    while date < end_date:
        job = {
            'function': 'archive',
            'url': buzzfeed_archive_template % (date.year, date.month, date.day),
            'date': datetime.date(year=date.year, month=date.month, day=date.day),
        }
        queue.put(job)
        date += frequency

    # create and start threads
    threads = [QueueConsumer(queue, i, crawl_index.crawl_index) for i in range(num_threads)]
    for t in threads:
        t.start()

    # wait for the queue to be empty before moving on and joining threads
    while queue.qsize() > 0:
        time.sleep(1.0)
        sys.stdout.flush()

    print 'Queue appears to be empty, sleeping for 30 seconds before joining threads.'
    time.sleep(30)

    # we call the join method on all threads simultaneously because 
    # iterating through a loop would be synchronous (have to wait for
    # each thread to exit in succession), which is terribly slow for 
    # any tasks with moderate latency.  it's better to just tell them
    # all to end at once, so we use lightweight greenlets for that.
    gthreads = [gevent.spawn(lambda x: x.join(), t) for t in threads]
    gevent.joinall(gthreads)

    session.close()
