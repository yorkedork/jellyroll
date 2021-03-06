import logging
import optparse
import jellyroll

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        optparse.make_option(
            "-p", "--providers", 
            dest="providers", 
            action="append", 
            help="Only use certain provider(s)."
        ),
        optparse.make_option(
            "-l", "--list-providers", 
            dest="list_providers",
            action="store_true", 
            help="Display a list of active data providers."
        ),
    )
    
    def handle(self, *args, **options):
        level = {
            '0': logging.WARN, 
            '1': logging.INFO, 
            '2': logging.DEBUG
            }[options.get('verbosity', '0')]
        logging.basicConfig(level=level, format="%(name)s: %(levelname)s: %(message)s")

        if 'list_providers' not in options:
            options['list_providers'] = False
        if 'providers' not in options:
            options['providers'] = self.available_providers()

        if options['list_providers']:
            self.print_providers()
            return 0
        if options['providers']:
            for provider in options['providers']:
                if provider not in self.available_providers():
                    print "Invalid provider: %r" % provider
                    self.print_providers()
                    return 0

        jellyroll.update(options['providers'])

    def available_providers(self):
        return jellyroll.active_providers()

    def print_providers(self):
        available = sorted(self.available_providers().keys())
        print "Available data providers:"
        for provider in available:
            print "   ", provider
        
