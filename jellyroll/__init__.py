import os
import glob
import logging
log = logging.getLogger("jellyroll")
import datetime
import logging
import urllib

from django.conf import settings
from jellyroll.providers import get_registered_provider, _providers_cache

try:
    set
except NameError:
    from sets import Set as set     # Python 2.3 fallback


"""
Blah, blah, blah

"""
def active_providers():
    """
    Return a dict of {name: module} of active, enabled providers.

    """
    providers = {}
    for provider in settings.JELLYROLL_PROVIDERS:
        try:
            mod = __import__(provider, '', '', [], -1)
            mod = __import__(provider, '', '', [ get_registered_provider(provider) ], -1)
            provider_cls = getattr(mod, get_registered_provider(provider))
        except ImportError, e:
            log.error("Couldn't import provider %r: %s" % (provider, e))
            raise

        if provider_cls().enabled():
            providers[provider] = provider_cls
        else:
            log.debug( "Provider %s will not be enabled." % provider )

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
