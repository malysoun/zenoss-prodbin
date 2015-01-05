##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
from Products.ZenUtils.ZeoConn import ZeoConn


__doc__="""ZenDaemon

$Id: ZC.py,v 1.9 2004/02/16 17:19:31 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import time
from collections import Iterator

from threading import Lock
from twisted.internet import defer
from zope.component import getUtility

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager

from Products.ZenUtils.Utils import getObjByPath, zenPath
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup

from Exceptions import ZentinelException
from ZenDaemon import ZenDaemon

from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Products.ZenUtils.mysql import MySQLdb
from Products.ZenUtils.Utils import wait

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


class _RetryIterator(Iterator):
    """
    Provides an interator that returns a delay interval (seconds) in
    sucession until a predetermined amount of time has passed.  Each
    returned delay value is larger than the prior value but will not
    exceed the MAX_DELAY_SECONDS value.
    """

    TIMEOUT_SECONDS = 10 * 60
    MAX_DELAY_SECONDS = 30
    DELAY_MULTIPLIER = 1.618

    def __init__(self, maxdelay=MAX_DELAY_SECONDS, timeout=TIMEOUT_SECONDS):
        """
        Initialize an instance of _RetryIterator.

        @param maxdelay {float} Maximum delay interval (seconds).
        @param timeout {float} Timeout duration (seconds).
        """
        self.started = time.time()
        self.maxdelay = maxdelay
        self.until = self.started + timeout
        self.delay = 1.0 / self.DELAY_MULTIPLIER

    def next(self):
        """
        Returns the next delay iterval or raises StopIteration when
        the timeout duration has been exceeded,
        """
        if self.until < time.time():
            raise StopIteration()
        self.delay = min(self.delay * self.DELAY_MULTIPLIER, self.maxdelay)
        return self.delay


class ZCmdBase(ZenDaemon, ZeoConn):

    def __init__(self, noopts=0, app=None, keeproot=False):
        ZenDaemon.__init__(self, noopts, keeproot)
        ZeoConn.__init__(self)
        self.dataroot = self.dmd = None
        self.app = app
        if not app:
            self.connect(**self.options.__dict__)
            self.opendb()
        self.poollock = Lock()
        self.getDataRoot()
        self.login()
        setDescriptors(self.dmd)

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
            return self.getApp()

    @defer.inlineCallbacks
    def async_syncdb(self):
        """
        Asynchronous version of the syncdb method.
        """
        last_exc = None
        for delay in _RetryIterator():
            try:
                self.connection.sync()
            except MySQLdb.OperationalError as exc:
                last_exc = str(exc)
                self.log.warn(
                    "Connection to ZODB interrupted, will try "
                    "to reconnect again in %.3f seconds.", delay
                )
                # yield back to reactor for 'delay' seconds
                yield wait(delay)
            else:
                self.log.debug("Synchronized with database")
                break
        else:
            # This code only executed if the RetryIterator 'runs out'
            # of retry attempts.
            self.log.warn(
                "Timed out trying to reconnect to ZODB: %s", last_exc
            )

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
                super(ZCmdBase, self).syncdb()

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

    def getDataRoot(self):
        if not self.app:
            self.opendb()
        if not self.dataroot:
            self.dataroot = getObjByPath(self.app, self.options.dataroot)
            self.dmd = self.dataroot

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
