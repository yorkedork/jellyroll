import time
import logging
log = logging.getLogger("jellyroll.providers.svn")
import datetime
import md5

from django.db import transaction
from django.utils.encoding import smart_unicode, smart_str

from jellyroll.core.models import Item
from jellyroll.contrib.code.models import CodeRepository, CodeCommit
from jellyroll.contrib.code.providers import CodeRepositoryProvider
from jellyroll.providers import utils, register_provider

try:
    import pysvn
except ImportError:
    pysvn = None


class SubversionProvider(CodeRepositoryProvider):
    """
    

    """
    REPOSITORY_TYPE = "svn"

    def enabled(self):
        ok = pysvn is not None
        if not ok:
            log.warn("The SVN provider is not available because the pysvn module "
                     "isn't installed.")
        return ok

    def update_codecommit_svn(self, repository, last_update_date, commit_list):
        # TODO: investigate issues with last_update_date, etc.
        rev = pysvn.Revision(pysvn.opt_revision_kind.date, time.mktime(last_update_date.timetuple()))
        c = pysvn.Client()

        for revision_entry in reversed(c.log(repository.url, revision_end=rev)):
            revision = revision_entry.revision
            if revision_entry.author == repository.username:
                log.debug("Handling [%s] from %s" % (revision.number, repository.url))
                timestamp = datetime.datetime.fromtimestamp(revision_entry.date)
                
                obj = {}
                obj['revision'] = str(revision.number)
                obj['repository'] = repository
                obj['message'] = smart_unicode(revision_entry.message)
                obj['timestamp'] = timestamp
                
                commit_list.append( obj )

register_provider(SubversionProvider)
