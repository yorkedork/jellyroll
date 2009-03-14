import datetime
import logging
log = logging.getLogger("jellyroll.providers.flickr")
import urllib
import md5

from django.conf import settings
from django.db import transaction
from django.utils.encoding import smart_unicode

from jellyroll.core.models import Item
from jellyroll.contrib.photo.models import Photo, Photoset
from jellyroll.providers import utils, register_provider, StructuredDataProvider

try:
    set
except NameError:
    from sets import Set as set     # Python 2.3 fallback


class FlickrError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
    def __str__(self):
        return 'FlickrError %s: %s' % (self.code, self.message)

class FlickrClient(object):
    def __init__(self, api_key, method='flickr'):
        self.api_key = api_key
        self.method = method
        
    def __getattr__(self, method):
        return FlickrClient(self.api_key, '%s.%s' % (self.method, method))
        
    def __repr__(self):
        return "<FlickrClient: %s>" % self.method
        
    def __call__(self, **params):
        params['method'] = self.method
        params['api_key'] = self.api_key
        params['format'] = 'json'
        params['nojsoncallback'] = '1'
        url = "http://flickr.com/services/rest/?" + urllib.urlencode(params)
        json = utils.getjson(url)
        if json.get("stat", "") == "fail":
            raise FlickrError(json["code"], json["message"])
        return json

class FlickrProvider(StructuredDataProvider):
    MODELS = [
        'photo.Photo',
        'photo.Photoset',
        ]

    def __init__(self):
        super(FlickrProvider,self).__init__()

        self.register_model(Photo,priority=0)
        self.register_model(Photoset,priority=1)

        data_interface = FlickrClient(settings.FLICKR_API_KEY)
        self.register_custom_data_interface(data_interface,Photo)
        self.register_custom_data_interface(data_interface,Photoset)

    def enabled(self):
        ok = (hasattr(settings, "FLICKR_API_KEY") and
              hasattr(settings, "FLICKR_USER_ID") and
              hasattr(settings, "FLICKR_USERNAME"))
        if not ok:
            log.warn('The Flickr provider is not available because the '
                     'FLICKR_API_KEY, FLICKR_USER_ID, and/or FLICKR_USERNAME settings '
                     'are undefined.')
        return ok

    def source_id(self, model_cls, extra):
        if model_cls == Photo:
            return ':'.join( ['flickr',extra['photo_id']] )
        elif model_cls == Photoset:
            return ':'.join( ['flickr',extra['photoset_id']] )

    def convert_exif(self, exif):
        converted = {}
        for e in exif["photo"]["exif"]:
            key = smart_unicode(e["label"])
            val = e.get("clean", e["raw"])["_content"]
            val = smart_unicode(val)
            converted[key] = val
        return converted

    def convert_tags(self, tags):
        return " ".join(set(t["_content"] for t in tags["tag"] if not t["machine_tag"]))

    def get_default_fields(self, model_cls):
        if model_cls == Photo:
            fields = super(FlickrProvider,self).get_default_fields(model_cls)
            return [ field for field in fields if field.name != '_exif' ]
        elif model_cls == Photoset:
            return super(FlickrProvider,self).get_default_fields(model_cls)

    def update_photo(self, flickr):
        last_update_date = Item.objects.get_last_update_of_model(Photo)
        log.debug("Last update date: %s", last_update_date)

        licenses = licenses = flickr.photos.licenses.getInfo()
        licenses = dict((l["id"], smart_unicode(l["url"])) for l in licenses["licenses"]["license"])

        page = 1
        keep_working = True
        photo_list = self.incoming["photo"] = list()
        while True:
            log.debug("Fetching page %s of photos", page)
            resp = flickr.people.getPublicPhotos(user_id=settings.FLICKR_USER_ID, extras="license,date_taken", 
                                                 per_page="500", page=str(page))
            photos = resp["photos"]
            if page > photos["pages"]:
                log.debug("Ran out of photos; stopping.")
                return

            for photodict in photos["photo"]:
                timestamp = utils.parsedate(str(photodict["datetaken"]))
                if timestamp < last_update_date:
                    log.debug("Hit an old photo (taken %s; last update was %s); stopping.", 
                              timestamp, last_update_date)
                    break

                obj = {}
                obj['photo_id'] = smart_unicode(photodict["id"])
                obj['cc_license'] = licenses[photodict["license"]]
                obj['secret'] = smart_unicode(photodict["secret"])

                info = flickr.photos.getInfo(photo_id=obj['photo_id'], secret=obj['secret'])["photo"]

                obj['server_id'] = utils.safeint(info["server"])
                obj['farm_id'] = utils.safeint(info["farm"])
                obj['taken_by'] = smart_unicode(info["owner"]["username"])
                obj['title'] = smart_unicode(info["title"]["_content"])
                obj['description'] = smart_unicode(info["description"]["_content"])
                obj['comment_count'] = utils.safeint(info["comments"]["_content"])
                obj['date_uploaded'] = datetime.datetime.fromtimestamp(utils.safeint(info["dates"]["posted"]))
                obj['date_updated'] = datetime.datetime.fromtimestamp(utils.safeint(info["dates"]["lastupdate"]))

                obj['tags'] = self.convert_tags(info["tags"])
                obj['timestamp'] = timestamp
                obj['photoset'] = None

                photo_list.append( obj )
            page += 1

    def update_photoset(self, flickr):
        resp = flickr.people.getInfo(user_id=settings.FLICKR_USER_ID)
        person = resp["person"]
        base_url = smart_unicode(person["photosurl"]["_content"])

        resp = flickr.photosets.getList(user_id=settings.FLICKR_USER_ID)
        sets = resp["photosets"]
        photoset_list = self.incoming["photoset"] = list()
        for photosetdict in sets["photoset"]:

            obj = {}
            obj['photoset_id'] = smart_unicode(photosetdict["id"])
            obj['timestamp'] = datetime.datetime.now()
            obj['url'] = "%s/sets/%s/" % (base_url, obj['photoset_id'])
            obj['secret'] = smart_unicode(photosetdict["secret"])
            obj['server_id'] = utils.safeint(photosetdict["server"])
            obj['farm_id'] = utils.safeint(photosetdict["farm"])
            obj['title'] = smart_unicode(photosetdict["title"]["_content"])
            obj['description'] = smart_unicode(photosetdict["description"]["_content"])

            photoset_list.append( obj )

    def pre_handle_item_created(self, model_instance, data):
        if model_instance.__class__ == Photo:
            data_interface = self.DATA_INTERFACES['photo']
            model_instance.exif = self.convert_exif(
                data_interface.photos.getExif(
                    photo_id=data['photo_id'], secret=data['secret']))
            model_instance.save()

    def post_handle_default(self, model_instance, model_str, model_cls, data, created):
        if model_instance.__class__ == Photoset:
            data_interface = self.DATA_INTERFACES['photoset']
            page = 1
            while True:
                resp = data_interface.photosets.getPhotos(
                    user_id=settings.FLICKR_USER_ID, photoset_id=model_instance.photoset_id,
                    extras="license,date_taken",  per_page="500", page=str(page), media="photos")

                photos = resp["photoset"]
                if page > photos["pages"]:
                    return

                for photodict in photos["photo"]:
                    try:
                        photo = Photo.objects.get(photo_id=smart_unicode(photodict["id"]))
                        model_instance.photos.add(photo)
                    except Photo.DoesNotExist:
                        log.debug( "Photo object corresponding to the record %s could not be found for photoset %s" % \
                                       (photodict,model_instance) )

                page += 1

register_provider( FlickrProvider )
