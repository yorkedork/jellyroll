import urllib
import urlparse

from django.conf import settings
from django.db import models
from django.utils import simplejson
from jellyroll.backends.item.models import Item


CC_LICENSES = (
    ('http://creativecommons.org/licenses/by/2.0/',         'CC Attribution'),
    ('http://creativecommons.org/licenses/by-nd/2.0/',      'CC Attribution-NoDerivs'),
    ('http://creativecommons.org/licenses/by-nc-nd/2.0/',   'CC Attribution-NonCommercial-NoDerivs'),
    ('http://creativecommons.org/licenses/by-nc/2.0/',      'CC Attribution-NonCommercial'),
    ('http://creativecommons.org/licenses/by-nc-sa/2.0/',   'CC Attribution-NonCommercial-ShareAlike'),
    ('http://creativecommons.org/licenses/by-sa/2.0/',      'CC Attribution-ShareAlike'),
)

class Photoset(models.Model):
    """

    """
    # Key Flickr info
    photoset_id = models.CharField(unique=True, primary_key=True, max_length=50)
    farm_id     = models.PositiveSmallIntegerField(null=True)
    server_id   = models.PositiveSmallIntegerField()
    secret      = models.CharField(max_length=30, blank=True)

    # Main metadata
    title           = models.CharField(max_length=250)
    description     = models.TextField(blank=True)
    url             = models.URLField()

    class Meta:
        app_label = 'jellyroll'

    def _get_photo_count(self):
        return self.photos.count()
    count = property(_get_photo_count)

    def _get_farm(self):
        if self.farm_id:
            return ''.join(["farm",str(self.farm_id),"."])
        return ''
    farm = property(_get_farm)

    def __unicode__(self):
        return self.title

Item.objects.follow_model(Photoset)

class Photo(models.Model):
    """
    A photo someone took. This person could be you, in which case you can
    obviously do whatever you want with it. However, it could also have been
    taken by someone else, so in that case there's a few fields for storing the
    object's rights.
    
    The model is based on Flickr, and won't work with anything else :(
    """
    
    # Key Flickr info
    photo_id    = models.CharField(unique=True, primary_key=True, max_length=50)
    farm_id     = models.PositiveSmallIntegerField(null=True)
    server_id   = models.PositiveSmallIntegerField()
    secret      = models.CharField(max_length=30, blank=True)

    # Rights metadata
    taken_by    = models.CharField(max_length=100, blank=True)
    cc_license  = models.URLField(blank=True, choices=CC_LICENSES)
    
    # Main metadata
    title           = models.CharField(max_length=250)
    description     = models.TextField(blank=True)
    comment_count   = models.PositiveIntegerField(max_length=5, default=0)
    photoset        = models.ForeignKey(Photoset, blank=True, null=True, related_name="photos")
    
    # Date metadata
    date_uploaded = models.DateTimeField(blank=True, null=True)
    date_updated  = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = 'jellyroll'
    
    # EXIF metadata
    _exif = models.TextField(blank=True)
    def _set_exif(self, d):
        self._exif = simplejson.dumps(d)
    def _get_exif(self):
        if self._exif:
            return simplejson.loads(self._exif)
        else:
            return {}
    exif = property(_get_exif, _set_exif, "Photo EXIF data, as a dict.")
    
    def _get_farm(self):
        if self.farm_id:
            return ''.join(["farm",str(self.farm_id),"."])
        return ''
    farm = property(_get_farm)

    def __unicode__(self):
        return self.title
    
    def url(self):
        return "http://www.flickr.com/photos/%s/%s/" % (self.taken_by, self.photo_id)
    url = property(url)
        
    def timestamp(self):
        return self.date_uploaded
    timestamp = property(timestamp)
    
    ### Image URLs ###
    
    def get_image_url(self, size=None):
        if size in list('mstbo'):
            return "http://%sstatic.flickr.com/%s/%s_%s_%s.jpg" % \
                (self.farm, self.server_id, self.photo_id, self.secret, size)
        else:
            return "http://%sstatic.flickr.com/%s/%s_%s.jpg" % \
                (self.farm, self.server_id, self.photo_id, self.secret)
    
    image_url       = property(lambda self: self.get_image_url())
    square_url      = property(lambda self: self.get_image_url('s'))
    thumbnail_url   = property(lambda self: self.get_image_url('t'))
    small_url       = property(lambda self: self.get_image_url('m'))
    large_url       = property(lambda self: self.get_image_url('b'))
    original_url    = property(lambda self: self.get_image_url('o'))
    
    ### Rights ###
    
    def license_code(self):
        if not self.cc_license:
            return None
        path = urlparse.urlparse(self.cc_license)[2]
        return path.split("/")[2]
    license_code = property(license_code)
    
    def taken_by_me(self):
        return self.taken_by == getattr(settings, "FLICKR_USERNAME", "")
    taken_by_me = property(taken_by_me)
    
    def can_republish(self):
        """
        Is it OK to republish this photo, or must it be linked only?
        """
        
        # If I took the photo, then it's always OK to republish.
        if self.taken_by_me:
            return True
        
        # If the photo has no CC license, then it's never OK to republish.
        elif self.license_code is None:
            return False
        
        # If the settings flags this site as "commercial" and it's an NC
        # license, then no republish for you.
        elif getattr(settings, "SITE_IS_COMMERCIAL", False) and "nc" in self.license_code:
            return False
        
        # Otherwise, we're OK to republish it.
        else:
            return True
    can_republish = property(can_republish)
    
    def derivative_ok(self):
        """Is it OK to produce derivative works?"""
        return self.can_republish and "nd" not in self.license_code
    derivative_ok = property(derivative_ok)
    
    def must_share_alike(self):
        """Must I share derivative works?"""
        return self.can_republish and "sa" in self.license_code
    must_share_alike = property(must_share_alike)

Item.objects.follow_model(Photo)
