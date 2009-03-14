import feedparser
import logging
log = logging.getLogger("jellyroll.contrib.code.providers")
import urllib
import logging

from django.utils.encoding import smart_unicode, smart_str

from jellyroll.core.models import Item
from jellyroll.contrib.code.models import CodeCommit, CodeRepository
from jellyroll.providers import Provider


class CodeRepositoryProvider(Provider):
    """
    ``Provider`` subclass that has baked-in processing facilities for 
    fetching updates from SCM systems via ``CodeRepository`` objects.

    """
    MODELS = [
        'code.CodeCommit',
        ]

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

