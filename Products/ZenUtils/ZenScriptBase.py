##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""ZenScriptBase

Scripts with classes who extend ZenScriptBase have a zope instance with a
dmd root and loaded ZenPacks, like zendmd.
"""

from zope.component import getUtility

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from transaction import commit
from Products.ZenUtils.Utils import getObjByPath, zenPath
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenUtils.ZeoConn import ZeoConn
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup

from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Products.ZenUtils.Exceptions import ZentinelException

defaultCacheDir = zenPath('var')


class DataRootError(Exception):
    pass


class ZenScriptBase(CmdBase, ZeoConn):

    def __init__(self, noopts=0, app=None, connect=False):
        CmdBase.__init__(self, noopts)
        ZeoConn.__init__(self)
        self.dataroot = self.dmd = None
        self.app = app
        if connect:
            self.connect(self.options)

    def connect(self, **kwargs):
        ZeoConn.connect(self, **kwargs)
        self.opendb()
        self.getDataRoot()
        self.login()
        if getattr(self.dmd, 'propertyTransformers', None) is None:
            self.dmd.propertyTransformers = {}
            commit()
        setDescriptors(self.dmd)

    def login(self, name='admin', userfolder=None):
        """Logs in."""
        if userfolder is None:
            userfolder = self.app.acl_users
        user = userfolder.getUserById(name)
        if user is None: return
        if not hasattr(user, 'aq_base'):
            user = user.__of__(userfolder)
        newSecurityManager(None, user)

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

    def getDataRoot(self):
        if not self.app:
            self.opendb()
        if not self.dataroot or not self.dmd:
            self.dataroot = getObjByPath(self.app, self.options.dataroot)
            self.dmd = self.dataroot
        return self.dmd

    def getDmdObj(self, path):
        """return an object based on a path starting from the dmd"""
        return getObjByPath(self.app, self.options.dataroot+path)

    def findDevice(self, name):
        """return a device based on its FQDN"""
        devices = self.dataroot.getDmdRoot("Devices")
        return devices.findDevice(name)

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        CmdBase.buildOptions(self)

        connectionFactory = getUtility(IZodbFactoryLookup).get()
        connectionFactory.buildOptions(self.parser)
