##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ZenDaemon

$Id: ZC.py,v 1.9 2004/02/16 17:19:31 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import time

from threading import Lock
from zope.component import getUtility

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager

from Products.ZenUtils.Utils import getObjByPath, zenPath
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup

from Exceptions import ZentinelException
from ZenDaemon import ZenDaemon

from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Products.ZenUtils.mysql import MySQLdb

defaultCacheDir = zenPath('var')

class DataRootError(Exception):pass

def login(context, name='admin', userfolder=None):
    """Logs in."""
    if userfolder is None:
        userfolder = context.getPhysicalRoot().acl_users
    user = userfolder.getUserById(name)
    if user is None: return
    if not hasattr(user, 'aq_base'):
        user = user.__of__(userfolder)
    newSecurityManager(None, user)
    return user

class ZCmdBase(ZenDaemon):

    def __init__(self, noopts=0, app=None, keeproot=False):
        ZenDaemon.__init__(self, noopts, keeproot)
        self.dataroot = None
        self.app = app
        self.db = None
        if not app:
            self.zodbConnect()
        self.poollock = Lock()
        self.getDataRoot()
        self.login()
        setDescriptors(self.dmd)

    def zodbConnect(self):
        connectionFactory = getUtility(IZodbFactoryLookup).get()
        self.db, self.storage = connectionFactory.getConnection(**self.options.__dict__)

    def login(self, name='admin', userfolder=None):
        """Logs in."""
        login(self.dmd, name, userfolder)


    def logout(self):
        """Logs out."""
        noSecurityManager()


    def getConnection(self):
        """Return a wrapped app connection from the connection pool.
        """
        if not self.db:
            raise ZentinelException(
                "running inside zope can't open connections.")
        with self.poollock:
            connection=self.db.open()
            root=connection.root()
            app=root['Application']
            app = self.getContext(app)
            app._p_jar.sync()
            return app


    def closeAll(self):
        """Close all connections in both free an inuse pools.
        """
        self.db.close()


    def opendb(self):
        if self.app: return 
        self.connection=self.db.open()
        root=self.connection.root()
        app=root['Application']
        self.app = self.getContext(app)


    def syncdb(self):
        MAX_RETRY_TIME_MINUTES = 10
        MAX_RETRY_DELAY_SECONDS = 30

        retryStartedAt = None
        def timedOut():
            if retryStartedAt is None:
                return False
            else:
                return retryStartedAt + MAX_RETRY_TIME_MINUTES * 60 < time.time()
        
        retryMultiplier = 1.618
        retryDelay = 1

        keepTrying = True
        while keepTrying:
            try:
                self.connection.sync()

            except MySQLdb.OperationalError, e:
                if timedOut():
                    self.log.info("Timed out trying to reconnect to ZODB.")
                    self.log.exception(e)
                    keepTrying = False
                    break
    
                if retryDelay * retryMultiplier >= MAX_RETRY_DELAY_SECONDS:
                    retryDelay = MAX_RETRY_DELAY_SECONDS
                else:
                    retryDelay *= retryMultiplier

                self.log.warn("Connection to ZODB interrupted, will try to reconnect again in %d seconds.", retryDelay)
                
                if retryStartedAt is None:
                    retryStartedAt = time.time()
                
                try:
                    time.sleep(retryDelay)
                except Exception, e:
                    break

            else:
                keepTrying = False
	

    def closedb(self):
        self.connection.close()
        #self.db.close()
        self.app = None
        self.dataroot = None
        self.dmd = None


    def getDataRoot(self):
        if not self.app: self.opendb()
        if not self.dataroot:
            self.dataroot = getObjByPath(self.app, self.options.dataroot)
            self.dmd = self.dataroot


    def getContext(self, app):
        from ZPublisher.HTTPRequest import HTTPRequest
        from ZPublisher.HTTPResponse import HTTPResponse
        from ZPublisher.BaseRequest import RequestContainer
        resp = HTTPResponse(stdout=None)
        env = {
            'SERVER_NAME':'localhost',
            'SERVER_PORT':'8080',
            'REQUEST_METHOD':'GET'
            }
        req = HTTPRequest(None, env, resp)
        return app.__of__(RequestContainer(REQUEST = req))


    def getDmdObj(self, path):
        """return an object based on a path starting from the dmd"""
        return getObjByPath(self.app, self.options.dataroot+path)


    def findDevice(self, name):
        """return a device based on its FQDN"""
        devices = self.dataroot.getDmdRoot("Devices")
        return devices.findDevice(name)

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenDaemon.buildOptions(self)

        connectionFactory = getUtility(IZodbFactoryLookup).get()
        connectionFactory.buildOptions(self.parser)
