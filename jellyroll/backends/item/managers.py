import datetime

from django.db import models
from django.db.models import signals
from django.db.models.loading import get_model
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode
from tagging.fields import TagField


class ItemManager(models.Manager):

    def __init__(self):
        super(ItemManager, self).__init__()
        self.models_by_name = {}
    
    def create_or_update(self, instance, timestamp=None, url=None, tags="", 
                         source="INTERACTIVE", source_id="", **kwargs):
        """
        Create or update an Item from some instance.

        """
        # If the instance hasn't already been saved, save it first. This
        # requires disconnecting the post-save signal that might be sent to
        # this function (otherwise we could get an infinite loop).
        if instance._get_pk_val() is None:
            try:
                signals.post_save.disconnect(self.create_or_update, sender=type(instance))
            except Exception, err:
                reconnect = False
            else:
                reconnect = True
            instance.save()
            if reconnect:
                signals.post_save.connect(self.create_or_update, sender=type(instance))
        
        # Make sure the item "should" be registered.
        if not getattr(instance, "jellyrollable", True):
            return
        
        # Check to see if the following fields are being updated, possibly 
        # pulling the timestamp from the instance.
        if hasattr(instance, "timestamp"):
            timestamp = instance.timestamp
        if timestamp is None:
            timestamp = datetime.datetime.now()
                    
        if not tags:
            for f in instance._meta.fields:
                if isinstance(f, TagField):
                    tags = getattr(instance, f.attname)
                    break

        if not url:
            if hasattr(instance,'url'):
                url = instance.url

        # Create the Item object.
        ctype = ContentType.objects.get_for_model(instance)
        item, created = self.get_or_create(
            content_type = ctype, 
            object_id = force_unicode(instance._get_pk_val()),
            defaults = dict(
                timestamp = timestamp,
                source = source,
                source_id = source_id,
                tags = tags,
                url = url,
            )
        )

        # Update the Item object.
        item.timestamp = timestamp
        item.source_id = source_id
        item.source = source
        item.tags = tags
        item.url = url
        item.save()

        return item

    # TODO: document this method
    def find(self, provider, model_cls, extra):
        """
        

        """
        item_model_cls = get_model('jellyroll','item')
        provider_cls = provider.__class__
        id = provider.source_id(model_cls,extra)
        return self.get_query_set().get(source=provider_cls.__name__, source_id=id)

    def follow_model(self, model):
        """
        Follow a particular model class, updating associated Items automatically.

        """
        self.models_by_name[model.__name__.lower()] = model
        signals.post_save.connect(self.create_or_update, sender=model)
        
    def get_for_model(self, model):
        """
        Return a QuerySet of only items of a certain type.

        """
        return self.filter(content_type=ContentType.objects.get_for_model(model))
        
    def get_last_update_of_model(self, model, **kwargs):
        """
        Return the last time a given model's items were updated. Returns the
        epoch if the items were never updated.

        """
        qs = self.get_for_model(model)
        if kwargs:
            qs = qs.filter(**kwargs)
        try:
            return qs.order_by('-timestamp')[0].timestamp
        except IndexError:
            return datetime.datetime.fromtimestamp(0)
