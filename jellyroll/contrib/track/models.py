from django.db import models
from jellyroll.core.models import Item


class Track(models.Model):
    """A track you listened to. The model is based on last.fm."""
    
    artist_name = models.CharField(max_length=250)
    track_name  = models.CharField(max_length=250)
    url         = models.URLField(blank=True, max_length=1000)
    track_mbid  = models.CharField("MusicBrainz Track ID", max_length=36, blank=True)
    artist_mbid = models.CharField("MusicBrainz Artist ID", max_length=36, blank=True)

    class Meta:
        app_label = 'jellyroll'
    
    def __unicode__(self):
        return "%s - %s" % (self.artist_name, self.track_name)

Item.objects.follow_model(Track)
