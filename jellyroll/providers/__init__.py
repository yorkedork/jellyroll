import os
import glob
import logging
log = logging.getLogger("jellyroll.provider")
import feedparser
import datetime
import logging
import urllib

from django.conf import settings
from django.db import transaction
from django.utils.encoding import smart_unicode, smart_str

from jellyroll.backends.item.models import Item
from jellyroll.backends.code.models import CodeCommit, CodeRepository
from jellyroll.providers import utils

try:
    set
except NameError:
    from sets import Set as set     # Python 2.3 fallback


class ProviderException(Exception): 
    """
    The base class for all proccessing exceptions that occur
    within the Provider code path.

    """
    pass

class Provider(object):
    """ 
    The base class for the Jellyroll Provider subsystem.

    """
    PROVIDERS = {}

    def __init__(self):
        self.registered_classes = {}
        self.handler_funcs = {}
        self.updater_funcs = {}
        self.call_queue = {}
        self.incoming = {}

    # Abstract methods
    def enabled(self):
        """
        This method is a guard that determines whether or not this provider runs
        when jellyroll management commands are run.

        """
        raise NotImplementedError()

    def source_id(self, model_cls, extra):
        """
        This method is optionally used in the base ``handle_item`` method by
        ''ItemManager.find`` to determine if an instance exists for the
        given data. If this method is not implemented in the derived class, the
        ``handle_item`` method will simply use the value of ``created`` passed to it.

        This method should return a unique(?) hash given ``extra``, which is a data-
        object representative of a ``model_cls`` instance.

        """
        raise NotImplementedError()

    def get_update_data(self, model_cls, model_str):
        """
        This method should return an object suitable for use in the ``update_foo`` methods
        defined in subclasses.

        """
        raise NotImplementedError()

    def get_last_updated(self, model_cls, **kwargs):
        """
        This method should return a datetime object representing the date (and time) 
        associated with the last item bound with the model instance given by 
        ``model_cls`` created by this provider.

        """
        raise NotImplementedError()

    # Core methods
    def register_model(self, model_cls, priority=0):
        """
        Registers a ``Provider`` instance with a particular model.

        """
        log.debug( "Registering %s with %s at priority %d" % (model_cls,self.__class__,priority) )
        model_str = model_cls.__name__.lower()

        self.registered_classes[model_str] = model_cls
        self.call_queue[model_str] = priority

        try:
            self.handler_funcs[ model_str ] = \
                getattr(self,'_'.join(['handle',model_str]))
        except AttributeError:
            self.handler_funcs[ model_str ] = self.handle_default

        self.updater_funcs[ model_str ] = \
            getattr(self,'_'.join(['update',model_str]))

    def get_default_fields(self, model_cls):
        """
        This method is called to determine a list of field names (strings) to
        use as keys for ``defaults`` in ``model_cls.get_or_create``.

        """
        primary_key = model_cls()._meta.pk.name
        fields = [ field for field in model_cls()._meta.fields if field.name != primary_key ]
        return fields

    def run_update(self):
        """
        This method is the public entry-point.

        """
        self.update_main()
        self.handle_main()

    def update_main(self):
        """
        This method is responsible for populating the ``self.incoming`` dictionary.

        Keys should be given in the form of ``str(model_class).lower()``. If you would
        like to change the behaviour of ``update`` you should instead override the
        ```` method.

        """
        update_queue = self.updater_funcs.keys()
        if self.call_queue:
            update_queue.sort( cmp=lambda x,y: cmp(self.call_queue[x],self.call_queue[y]) )

        for model_str in update_queue:
            #func = transaction.commit_on_success(self.updater_funcs[model_str])
            func = self.updater_funcs[model_str]
            func( self.get_update_data(self.registered_classes[model_str],model_str) )

    def handle_main(self):
        """
        This method is responsible for handler functions for models registered with
        this ``Provider`` class.

        """
        handle_queue = self.updater_funcs.keys()
        if self.call_queue:
            handle_queue.sort( cmp=lambda x,y: cmp(self.call_queue[x],self.call_queue[y]) )

        for model_str in handle_queue:
            func = transaction.commit_on_success(self.handler_funcs[model_str])
            cls = self.registered_classes[model_str]
            for element in self.incoming[model_str]:
                try:
                    func( element, cls )
                except Exception, e:
                    log.error( "Encountered exception while processing for %s for %s: %s" % \
                                   (element,model_str,str(e)))

    def handle_default(self, obj, cls):
        """
        This method is a fallback implementation of the ``handle_<model>`` method.

        This method assumes that ``cls`` is a subclass of ``django.db.models.Model``.

        """
        # TODO: add exception handling if we encounter something that isn't derived 
        #       from django.db.models.Model so that users will find it easier to 
        #       avoid ignorance.
        defaults = {}
        primary_key = cls()._meta.pk.name

        for field in iter( self.get_default_fields(cls) ):
            defaults[field.name] = obj[field.name]

        _obj, created = (None, False)
        if primary_key in obj:
            _obj, created = cls.objects.get_or_create(
                pk = obj[primary_key],
                defaults = defaults
            )
        else:
            try:
                _obj = Item.objects.find(self,cls,obj).object
            except Item.DoesNotExist:
                created = True
                _obj = cls()
            except NotImplementedError:
                log.error("Neither the primary key for %s nor the method source_id for %s were "
                          "found. Processing with the default implementation of the method "
                          "handle_default cannot continue. Please implement either of these two "
                          "options to enable processing %s." % (cls,self.__class__,cls))
                return

        for field in iter( self.get_default_fields(cls) ):
            setattr(_obj,field.name,defaults[field.name])

        self.pre_handle_item( _obj, obj, created )
        item = self.handle_item( _obj, obj, created )
        self.post_handle_item( item, _obj, obj, created )

    def pre_handle_item(self, model_instance, data, created):
        """
        This method is executed before ``handle_item`` with the data object ``data``.

        The default implementation verifies that the data object contains
        the following keys: timestamp, url and tags, giving them default
        values if they do not already exist.

        """
        if 'timestamp' not in data:
            data['timestamp'] = None
        if 'url' not in data:
            data['url'] = None
        if 'tags' not in data:
            data['tags'] = ''

        if created:
            self.pre_handle_item_created(model_instance,data)
        else:
            self.pre_handle_item_updated(model_instance,data)

    def pre_handle_item_created(self, model_instance, data):
        """
        This method is called before ``handle_item`` if ``model_instance``
        has just been created.

        """
        pass

    def pre_handle_item_updated(self, model_instance, data):
        """
        This method is called before ``handle_item`` if ``model_instance``
        has previously been created.

        """
        pass

    def handle_item(self, model_instance, data, created):
        """
        This method is responsible for creating an ``Item`` instance given a
        ``django.db.models.Model`` instance ``obj`` which ``Item`` is 'following'.

        """
        item = None
        provider_cls = self.__class__
        model_cls = model_instance.__class__

        if hasattr(self,'source_id'):
            try:
                item = Item.objects.find(self,model_cls,data)
            except Item.DoesNotExist:
                item = Item.objects.create_or_update(
                    instance = model_instance,
                    timestamp = data['timestamp'],
                    source = provider_cls.__name__,
                    source_id = self.source_id(model_cls,data),
                    url = data['url'],
                    tags = data['tags'],
                )
        elif created:
            item = Item.objects.create_or_update(
                instance = model_instance,
                timestamp = data['timestamp'],
                source = provider_cls.__name__,
                source_id = self.source_id(model_cls,data),
                url = data['url'],
                tags = data['tags'],
            )

        #log.debug( "Created item for instance %s: %s" % (model_instance,item ) )
        return item

    def post_handle_item(self, item_instance, model_instance, data, created):
        """
        This method is executed after ``handle_item`` with (possibly recently created)
        ``Item`` instance ``item_instance``, the (possibly recently created) backend model
        ``model_instance`` and the data object ``data``.

        """
        if created:
            self.post_handle_item_created(item_instance,model_instance,data)
        else:
            self.post_handle_item_updated(item_instance,model_instance,data)

    def post_handle_item_created(self, item_instance, model_instance, data):
        """
        This method is called after ``handle_item`` if ``model_instance``
        has just been created.

        """
        pass

    def post_handle_item_updated(self, item_instance, model_instance, data):
        """
        This method is called after ``handle_item`` if ``model_instance``
        has previously been created.

        """
        pass

class StructuredDataProvider(Provider):
    """
    ``Provider`` subclass that has baked-in processing facilities
    for fetching updates via structured data on a given model.

    """
    def __init__(self):
        super(StructuredDataProvider,self).__init__()

        self.DATA_INTERFACES = {}
        self.DATA_URLS = {}
        self.DATA_PROCESSORS = {
            'xml': utils.getxml,
            'json': utils.getjson,
            'rss': feedparser.parse,
            }
        self.DATA_ITERATORS = {
            'xml': lambda x:x.getiterator,
            'json': lambda x:x,
            'rss': lambda x:x.entries,
            }

    def get_custom_data_interface_instance(self, interface_cls):
        """
        An optional callback to have control over how registered ``DATA_INTERFACE``
        elements are instanciated.

        """
        raise NotImplementedError()

    def register_custom_data_interface(self, interface_instance, model_cls):
        """
        Registers the custom (user-defined) data interface ``interface_instance`` to
        be passed to the ``update_<model>`` methods. 

        ``interface_instance`` should be callable: i.e., it should define __call__ 
        to implement the data object generation functionality.

        This method will override all data URLs that have been registered with 
        this ``model_cls``.

        """
        model_str = str(model_cls.__name__).lower()
        log.debug( "Registering interface %s with %s" % (interface_instance.__class__,model_str) )
        self.DATA_INTERFACES[model_str] = interface_instance

    def register_data_url(self, model_cls, url, format, alias=None):
        """
        Registers a url for structured data concerning instances of a particular model.

        """
        model_str = str(model_cls.__name__).lower()
        log.debug( "Registering data url %s with %s" % (url,model_str) )
        if model_str not in self.DATA_URLS and alias:
            self.DATA_URLS[model_str] = {}

        if alias: self.DATA_URLS[model_str][alias] = (url,format)
        else:     self.DATA_URLS[model_str] = (url,format)

    def get_update_data(self, model_cls, model_str):
        """
        This method returns a data object, or, if ``self.DATA_INTERFACES[model_str]``
        is defined, a callable that implements custom behaviour to generate this 
        data object.

        """
        if model_str in self.DATA_INTERFACES:
            try:
                return self.get_custom_data_interface_instance(
                    self.DATA_INTERFACES[model_str]
                    )
            except NotImplementedError:
                return self.DATA_INTERFACES[model_str]

        for model, content in self.DATA_URLS.iteritems():
            if type(content) == type(dict()):
                data_dict = {}
                for alias, data_tuple in content.iteritems():
                    processor = self.DATA_PROCESSORS[data_tuple[1]]
                    data_dict[alias] = self.DATA_ITERATORS[data_tuple[1]](
                        processor(data_tuple[0])
                        )
                return data_dict
            else:
                processor = self.DATA_PROCESSORS[content[1]]
                return self.DATA_ITERATORS[content[1]](
                    processor(content[0])
                    )

try:
    import gdata
except ImportError:
    gdata = None

class GDataProvider(Provider):
    """
    ``Provider`` subclass that has baked-in processing facilities for 
    fetching object data via Google's GData API.

    """
    def __init__(self):
        super(GDataProvider,self).__init__()

        self.DATA_INTERFACES = {}

    def enabled(self):
        ok = hasattr(settings, 'GOOGLE_USERNAME') and hasattr(settings, 'GOOGLE_PASSWORD') and gdata
        if not ok:
            log.warn('The GData provider is not available because the '
                     'GOOGLE_USERNAME and/or GOOGLE_PASSWORD settings are '
                     'undefined.')
        return ok

    def register_service_client(self, interface_cls, model_cls):
        model_str = str(model_cls.__name__).lower()
        log.debug( "Registering service client %s with %s" % (interface_cls,model_str) )
        self.DATA_INTERFACES[model_str] = interface_cls

    def get_update_data(self, model_cls, model_str):
        client = self.DATA_INTERFACES[model_str]()
        client.ClientLogin(settings.GOOGLE_USERNAME,settings.GOOGLE_PASSWORD)
        return client

class CodeRepositoryProvider(Provider):
    """
    ``Provider`` subclass that has baked-in processing facilities for 
    fetching updates from SCM systems via ``CodeRepository`` objects.

    """
    def __init__(self):
        super(CodeRepositoryProvider,self).__init__()
        self.register_model(CodeCommit)

    def source_id(self, model_cls, extra):
        return "%s:r%s" % (smart_str(extra['repository'].url),
                          smart_str(extra['revision']))

    def get_last_updated(self, model_cls, **kwargs):
        return Item.objects.get_last_update_of_model(
            model_cls, source_id__startswith=kwargs['repository'].url)

    def get_update_data(self, model_cls, model_str):
        return CodeRepository.objects.filter(type=self.REPOSITORY_TYPE)

    def update_codecommit(self, repositories):
        self.incoming["codecommit"] = list()
        for repository in repositories:
            last_update_date = self.get_last_updated(CodeCommit,repository=repository)
            log.info("Updating changes from %s since %s", repository.url, last_update_date)

            func = getattr(self,'_'.join([ 'update_codecommit',self.REPOSITORY_TYPE ]))
            func(repository,last_update_date,self.incoming["codecommit"])

#
# Module Functions
#

def register_provider(provider_cls):
    """
    Registers ``provider_cls`` with the provider subsystem.

    """
    (app, provider) = ( 
        provider_cls.__module__,
        provider_cls.__name__,
        )
    if provider_cls not in Provider.PROVIDERS:
        Provider.PROVIDERS[app] = provider

def active_providers():
    """
    Return a dict of {name: module} of active, enabled providers.

    """
    providers = {}
    for provider in settings.JELLYROLL_PROVIDERS:
        try:
            mod = __import__(provider, '', '', [], -1)
            mod = __import__(provider, '', '', [ Provider.PROVIDERS[provider] ], -1)
            provider_cls = getattr(mod,Provider.PROVIDERS[provider])
        except ImportError, e:
            log.error("Couldn't import provider %r: %s" % (provider, e))
            raise
        if provider_cls().enabled():
            providers[provider] = provider_cls

    return providers

def update(providers):
    """
    Update a given set of providers. If the list is empty, it means update all
    of 'em.

    """
    active = active_providers()
    if providers is None:
        providers = active.keys()
    else:
        providers = set(active.keys()).intersection(providers)
        
    for provider in providers:
        log.debug("Updating from provider %r", provider)
        try:
            provider_cls = active[provider]
        except KeyError:
            log.error("Unknown provider: %r" % provider)
            continue

        log.info("Running '%s.update()'", provider)
        try:
            provider_cls().run_update()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception, e:
            log.error("Failed during '%s.update()'", provider)
            log.exception(e)
            continue

        log.info("Done with provider %r", provider)
