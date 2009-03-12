import datetime
import dateutil
import logging
log = logging.getLogger("jellyroll.providers.youtube")
import md5

from django.conf import settings
from django.db import transaction
from django.utils.encoding import smart_unicode, smart_str

from jellyroll.backends.item.models import Item
from jellyroll.backends.video.models import VideoSource, Video
from jellyroll.providers import utils, register_provider, gdata, GDataProvider

import gdata.youtube
import gdata.youtube.service


class YoutubeProvider(GDataProvider):
    """


    """
    def __init__(self):
        super(YoutubeProvider,self).__init__()

        self.register_model(Video)
        self.register_service_client(gdata.youtube.service.YouTubeService,Video)
        self.source = VideoSource.objects.get(name="YouTube")

    def source_id(self, model_cls, extra):
        return md5.new( smart_str(extra['url']) ).hexdigest()

    def update_video(self, client):
        video_list = self.incoming["video"] = list()
        feed = client.GetUserFavoritesFeed()
        for entry in feed.entry:
            obj = {}

            obj['url'] = entry.link[0].href
            obj['title'] = smart_unicode(entry.title.text)

            tags = list()
            # HACK: avoid the last category which appears to
            #       simply be a link to the schema for video objects?
            for category in entry.category[:-1]:
                tags.append( category.term )
            obj['tags'] = ' '.join( tags )

            obj['timestamp'] = dateutil.parser.parse(entry.published.text)
            obj['source'] = self.source

            video_list.append( obj )

register_provider( YoutubeProvider )
