##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2015, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.component import getUtility
from Products.ZenUtils.Utils import set_context
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup


class ZeoConn(object):

    def __init__(self):
        self.app = None
        self.db = None
        self.connection = None

    def connect(self, **kwargs):
        connectionFactory = getUtility(IZodbFactoryLookup).get()
        self.db, self.storage = connectionFactory.getConnection(**kwargs)

    def opendb(self):
        if self.app:
            return
        self.connection = self._getConnection()
        self.app = self.getApp(self.connection)

    def syncdb(self):
        self.connection.sync()

    def closedb(self):
        self.connection.close()
        self.app = None

    def _getConnection(self):
        if not self.db:
            self.connect()

        return self.db.open()

    def getApp(self, connection=None):
        connection = connection or self._getConnection()
        root = connection.root()
        app = root['Application']
        app = set_context(app)
        app._p_jar.sync()
        return app

    def closeAll(self):
        """Close all connections in both free an inuse pools.
        """
        self.db.close()

    def syncdb(self):
        self.connection.sync()
