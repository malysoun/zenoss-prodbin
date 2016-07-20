##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class IncreaseMemcachedReqCount(Migrate.Step):
    "Change 'answering' healthcheck to retry a few times on failture"

    version = Migrate.Version(5, 2, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        memcached_services = filter(lambda s: s.name == 'memcached', ctx.services)

        for service in memcached_services:
            service.startup += ' -R 4096'

        ctx.commit()

IncreaseMemcachedReqCount()
