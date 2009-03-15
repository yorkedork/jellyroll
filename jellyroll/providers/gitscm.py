import re
import time
import logging
log = logging.getLogger("jellyroll.providers.gitscm")
import datetime
import shutil
import tempfile
import git

from unipath import FSPath as Path
from django.db import transaction
from django.utils.encoding import smart_unicode

from jellyroll.core.models import Item
from jellyroll.contrib.code.models import CodeRepository, CodeCommit
from jellyroll.contrib.code.providers import CodeRepositoryProvider
from jellyroll.providers import utils, register_provider


class GitSCMProvider(CodeRepositoryProvider):
    """


    """
    class Meta(CodeRepositoryProvider.Meta):
        repository_type = "git"
        modules         = ('git',)

    def create_local_repo(self, repository):
        working_dir = tempfile.mkdtemp()
        g = git.Git(working_dir)

        log.debug("Cloning %s into %s", repository.url, working_dir)
        res = g.clone(repository.url)

        # This is pretty nasty.
        m = re.match('^Initialized empty Git repository in (.*)', res)
        repo_location = Path(m.group(1).rstrip('/'))
        if repo_location.name == ".git":
            repo_location = repo_location.parent
        return working_dir, git.Repo(repo_location)

    def update_codecommit_git(self, repository, last_update_date, commit_list):
        # Git chokes on the 1969-12-31 sentinal returned by 
        # get_last_update_of_model, so fix that up.
        if last_update_date.date() == datetime.date(1969, 12, 31):
            last_update_date = datetime.datetime(1970, 1, 1)

        working_dir, repo = self.create_local_repo(repository)
        commits = repo.commits_since(since=last_update_date.strftime("%Y-%m-%d"))
        log.debug("Handling %s commits", len(commits))

        for commit in reversed(commits):
            if commit.author.email == repository.username:
                log.debug("Handling [%s] from %s", commit.id[:7], repository.url)

                # stored as UTC
                timestamp = datetime.datetime.fromtimestamp(time.mktime(commit.committed_date))
                if utils.JELLYROLL_ADJUST_DATETIME:
                    timestamp = utils.utc_to_local_timestruct(commit.committed_date)

                obj = {}
                obj['revision'] = commit.id
                obj['repository'] = repository
                obj['message'] = smart_unicode(commit.message)
                obj['timestamp'] = timestamp
                
                commit_list.append( obj )

        log.debug("Removing working dir %s.", working_dir)
        shutil.rmtree(working_dir)

register_provider(GitSCMProvider)
