import urlparse

from django.db import models
from jellyroll.core.models import Item


class VideoSource(models.Model):
    """
    A place you might view videos. Basically just an encapsulation for the
    "embed template" bit.
    """
    name = models.CharField(max_length=200)
    home = models.URLField()
    embed_template = models.URLField()
    
    class Meta:
        app_label = 'jellyroll'

    def __unicode__(self):
        return self.name

class Video(models.Model):
    """A video you viewed."""
    
    source = models.ForeignKey(VideoSource, related_name="videos")
    title  = models.CharField(max_length=250)
    url    = models.URLField()

    class Meta:
        app_label = 'jellyroll'

    def __unicode__(self):
        return self.title
        
    def docid(self):
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(self.url)
        return query.split("=")[-1]
    docid = property(docid)
        
    def embed_url(self):
        return self.source.embed_template % self.docid
    embed_url = property(embed_url)

Item.objects.follow_model(Video)
