Prerequisites
-------------

* Django 1.0
* PIL
* dateutil
* django-tagging, SVN r149+

Optional
--------

* pytz (1)

Notes
-----

1. pytz is included in order to support date translation of providers whose sources
   do not syndicate item dates in your local timezone (typically these services have
   settings for which you can specify your timezone). These services currently include:

  * gitscm (stores all dates UTC as time_struct)
  * lastfm (publishes all dates in RSS as UTC timestamp)
  * twitter (publishes all dates in RSS as UTC string)

Disclaimer
----------

Recently, the provider subsystem of this fork of jellyroll has been more or less refactored. 

In addition, a few things have been removed. Although mostly everything that didn't rely on all 
models being defined in jellyroll.models should continue to work without problem, and the 
interface (for the user) has stayed the same, developers should note that there is a much 
different (and hopefully you would agree, here), cleaner and simpler way to implement 
service providers.

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
