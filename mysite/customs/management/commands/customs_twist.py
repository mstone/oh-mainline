from django.core.management.base import BaseCommand
import twisted.web.client
from twisted.internet import reactor, defer
import mysite.customs.profile_importers

import mysite.profile.models

class Command(BaseCommand):
    help = "Call this when you want to run a Twisted reactor."

    def create_tasks_from_dias(self):
        print 'For all DIAs we know how to process with Twisted: enqueue them.'
        deferreds_we_created = []
        for dia in mysite.profile.models.DataImportAttempt.objects.filter(completed=False):
            if dia.source in mysite.customs.profile_importers.SOURCE_TO_CLASS:
                cls = mysite.customs.profile_importers.SOURCE_TO_CLASS[dia.source]
                d = self.add_dia_to_reactor(cls, dia.query, dia.id)
                deferreds_we_created.append(d)
        return deferreds_we_created

    def add_dia_to_reactor(self, cls, query, dia_id):
        ### For now, only the 'db' == Debian == qa.debian.org DIAs are in a format where
        ### they can handle asynchronous operation.
        state_manager = cls(query, dia_id)

        ### d is the "deferred" object. We create it using getPage(), and then
        ### we configure its next actions.
        url = state_manager.getUrl()
        d = twisted.web.client.getPage(url)
        d.addCallback(state_manager.handlePageContents)
        d.addErrback(state_manager.handleError)
        return d

    def enqueue_reactor_death(self, deferreds):
        dl = defer.DeferredList(deferreds)
        dl.addCallback(lambda x: reactor.stop())

    def handle(self, *args, **options):
        print "Creating getPage()-based deferreds..."
        created_deferreds = self.create_tasks_from_dias()
        if created_deferreds:
            print "Creating a DeferredList that, when all those are done, will quit the reactor..."
            self.enqueue_reactor_death(created_deferreds)
            print 'Starting Reactor...'
            reactor.run()
            print '...reactor finished!'
        else:
            print "We have no work to do. Exiting."