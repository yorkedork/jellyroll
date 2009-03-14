Prerequisites
-------------

* Django 1.0
* PIL
* dateutil
* django-tagging, SVN r149+

Optional
--------

* pytz (1)


Disclaimer
----------

This fork of ``jellyroll`` is on some level experimental, in that I can't guarantee it'll
pass a "worksforme" test. By all means, it should, but it may not.

This particular issue will rectified soon.

Changes
-------

Recently, the provider and model/backend subsystem of this fork of jellyroll has been more or less refactored. 

1. What you can do:
  * access the same old providers in ``jellyroll.providers``
  * signal providers to update via the same mechanism; in other words, the django management
    command ``jellyroll_update`` still works as it has.
  * list ``jellyroll`` alone in ``settings.INSTALLED_APPS`` to gain access to basic core 
    functionality like ``jellyoll.templatetags``, basic ``Feed`` classes in ``jellyroll.feeds``
    and the core ``Item`` model. This is the minimum requirement and only allows the user
    access to the ``Provider`` bits and tracking of externally-defined models.
  * You may specify "contrib" modules separately or you may install them all by using ``jellyroll.contrib``.

2. What you can't do:
  * access any previous models (other than ``Item``) via ``jellyroll.models``. Models that
    are defined externally as using ``Item`` tracking, thusly, shouldn't be affected. The
    remaining models previously in ``jellyroll.models`` now exist in ``jellyroll.contrib.somecategory``.

Removals
--------

* I've removed video results from jellyroll.providers.gsearch due to on-going/potential/etc.
  EOS issues with Google Video.
* I've removed the pownce provider because, sadly, due to on-going EOL issues.
* I've left the ma.gnolia provider in the RCS, but have yet to refactor it to support the
  new internal system for Provider objects. If it resumes service, I might end up fixing
  this issue.

Additions
---------

* Backend support for GData

Future Work
-----------

* Backend support for YQL (partially-complete)



Notes
-----

I'll be removing this section as it is displaced by an app-level policy(ies) governing
the treatment of objects destined for ``Item.timestamp``.

1. pytz is included in order to support date translation of providers whose sources
   do not syndicate item dates in your local timezone (typically these services have
   settings for which you can specify your timezone). These services currently include:

  * gitscm (stores all dates UTC as time_struct)
  * lastfm (publishes all dates in RSS as UTC timestamp)
  * twitter (publishes all dates in RSS as UTC string)
