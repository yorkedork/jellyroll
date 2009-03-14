import datetime
import logging
log = logging.getLogger("jellyroll.providers.twitter")
import dateutil
import md5
import re

from httplib2 import HttpLib2Error
from django.conf import settings
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.functional import memoize
from django.utils.http import urlquote
from django.utils.encoding import smart_str, smart_unicode

from jellyroll.core.models import Item
from jellyroll.contrib.message.models import Message
from jellyroll.contrib.utils.models import ContentLink
from jellyroll.providers import register_provider, utils, StructuredDataProvider

RECENT_STATUSES_URL = "http://twitter.com/statuses/user_timeline/%s.rss"
USER_URL = "http://twitter.com/%s"
USER_LINK_TPL = "<a href='%s' title='%s'>%s</a>"
TAG_RE = re.compile(r'(?P<tag>\#\w+)')
USER_RE = re.compile(r'(?P<username>@\w+)')
RT_RE = re.compile(r'RT\s+(?P<username>@\w+)')
USERNAME_RE = re.compile(r'^%s:'%settings.TWITTER_USERNAME)
URL_RE = re.compile( # modified from django.forms.fields.url_re
    r'https?://'
    r'(?:(?:[A-Z0-9-]+\.)+[A-Z]{2,6}|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/\S+|/?)', re.IGNORECASE)


class TwitterProvider(StructuredDataProvider):
    """


    """
    MODELS = [
        'message.Message',
        'util.ContentLink',
        ]

    def __init__(self):
        super(TwitterProvider,self).__init__()

        self.register_model(Message)
        self.register_data_url(Message,RECENT_STATUSES_URL%settings.TWITTER_USERNAME,"xml")

    def enabled(self):
        ok = hasattr(settings, 'TWITTER_USERNAME')
        if not ok:
            log.warn('The Twitter provider is not available because the TWITTER_USERNAME is not set')
        return ok

    def source_id(self, model_cls, extra):
        return md5.new(smart_str(extra['message']) + \
                       smart_str(extra['url']) + \
                       str(extra['timestamp'])).hexdigest()

    def update_message(self, data_iterator_func):
        last_update_date = Item.objects.get_last_update_of_model(Message)
        log.debug("Last update date: %s", last_update_date)

        statuses = self.incoming['message'] = list()
        for status in data_iterator_func("item"):

            message = smart_unicode(status.find("title").text)
            timestamp = dateutil.parser.parse(status.find('pubDate').text)
            if utils.JELLYROLL_ADJUST_DATETIME:
                timestamp = utils.utc_to_local_datetime(timestamp)

            obj = {}
            obj['message'], obj['links'], obj['tags'] = self.parse_message(message)
            obj['timestamp']                          = timestamp
            obj['url']                                = smart_unicode(status.find("link").text)

            statuses.append( obj )

    def post_handle_default(self, item_instance, model_str, model_instance, data, created):
        if not created or 'links' not in data:
            return

        for link in data['links']:
            l = ContentLink(
                url = link,
                identifier = link,
                )
            l.save()
            model_instance.links.add(l)

    #
    # Private API
    #
    def transform_retweet(self, matchobj):
        TWITTER_RETWEET_TXT = "Forwarding from %s: "
        if hasattr(settings,'TWITTER_RETWEET_TXT'):
            TWITTER_RETWEET_TXT = settings.TWITTER_RETWEET_TXT

        if '%s' in TWITTER_RETWEET_TXT:
            return TWITTER_RETWEET_TXT % matchobj.group('username')
        return TWITTER_RETWEET_TXT

    def transform_user_ref_to_link(self, matchobj):
        user = matchobj.group('username')[1:]
        link = USER_URL % user
        return USER_LINK_TPL % \
            (link,user,''.join(['@',user]))

    def parse_message(self, message_text):
        """
        Parse out some semantics for teh lulz.
        
        """
        links = list()
        tags = ""

        # remove newlines
        message_text = message_text.replace('\n','')
        # remove URLs referenced in message content
        # TODO: fix ungainly code below
        links = [ link for link in URL_RE.findall(message_text) ]
        link_ctr = 1
        link_dict = {}
        for link in URL_RE.finditer(message_text):
            link_dict[link.group(0)] = link_ctr
            link_ctr += 1
        generate_link_num = lambda obj: "[%d]"%link_dict[obj.group(0)]
        message_text = URL_RE.sub(generate_link_num,message_text)
        # remove leading username
        message_text = USERNAME_RE.sub('',message_text)
        # check for RT-type retweet syntax
        message_text = RT_RE.sub(self.transform_retweet,message_text)
        # replace @user references with links to their timeline
        message_text = USER_RE.sub(self.transform_user_ref_to_link,message_text)
        # extract defacto #tag style tweet tags
        tags = ' '.join( [tag[1:] for tag in TAG_RE.findall(message_text)] )
        message_text = TAG_RE.sub('',message_text)

        return (message_text.strip(),links,tags)

    if not hasattr(settings,'TWITTER_TRANSFORM_MSG') or \
       not settings.TWITTER_TRANSFORM_MSG:

        log.info("Disabling message transforms")
        TwitterProvider.parse_message = lambda self, msg: ( msg, list(), "" )

register_provider( TwitterProvider )
