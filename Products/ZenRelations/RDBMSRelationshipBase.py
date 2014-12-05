##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
from Products.ZenUtils.ZenDB import ZenDB

__doc__ = """RDBMSRelationshipBase

RDBMSRelationshipBase is the base class for RDBMS Relationship types
and RDBMS ToManyRelationshipBase."""

import logging

log = logging.getLogger("zen.Relations")

import Globals
from Globals import InitializeClass
from Acquisition import aq_base
from zope import interface
from decorator import decorator

from Products.Zuul.decorators import memoize
from Products.Zuul.utils import safe_hasattr
from Products.ZenRelations.Exceptions import *
from Products.ZenRelations.utils import importClass

from PrimaryPathObjectManager import PrimaryPathManager

from zope.event import notify
from OFS.event import ObjectWillBeAddedEvent
from OFS.event import ObjectWillBeRemovedEvent
from zope.container.contained import dispatchToSublocations
from zope.container.contained import ObjectAddedEvent
from zope.container.contained import ObjectRemovedEvent
from zope.container.contained import ContainerModifiedEvent


def getSqlConnection():
    dbconn = getattr(Globals, 'RelDB', None)
    if dbconn and dbconn.open():
        return dbconn

    dbconn = ZenDB('zodb').getConnection()
    Globals.RelDb = dbconn
    return dbconn


@decorator
def relDbTransactional(func, *args, **kwargs):
    dbconn = getSqlConnection()
    dbconn.begin()
    try:
        func(*args, **kwargs)
    except Exception as ex:
        dbconn.rollback()
        raise ex
    else:
        dbconn.commit()


def getSqlCursor():
    dbconn = getSqlConnection()
    return dbconn.cursor()


class RDBMSRelationshipBase(PrimaryPathManager):
    """
    Abstract base class for all relationship classes.
    """

    _operation = -1 # if a Relationship's are only deleted

    def getId(self):
        return self.id

    @property
    def _schema(self):
        return self.__primary_parent__.lookupSchema(self.id)

    def addRelation(self, obj):
        """Form a bi-directional relation between self and obj."""
        if obj is None:
            raise ZenRelationsError("Can not add None to relation")
        if not isinstance(obj, self.remoteClass()):
            raise ZenSchemaError("%s restricted to class %s. %s is class %s" %
                                 (self.id, self.remoteClass().__name__,
                                  obj.id, obj.__class__.__name__))

        # make sure remote rel is on this obj
        if not safe_hasattr(aq_base(obj), self.remoteName()):
            raise ZenRelationsError("Remote object %s does not have reciprocal relationship %s" %
                                    (obj.getPrimaryId(), self.remoteName()))

        try:
            self._add(obj.getPrimaryId())
        except RelationshipExistsError:
            log.debug("obj %s already exists on %s", obj.getPrimaryId(),
                      self.getPrimaryId())


    def removeRelation(self, obj=None, suppress_events=False):
        """remove an object from a relationship"""
        self._remove(obj, suppress_events=suppress_events)

    @memoize
    def remoteType(self):
        """Return the type of the remote end of our relationship."""
        return self._schema.remoteType

    @memoize
    def remoteTypeName(self):
        """Return the type of the remote end of our relationship."""
        return self._schema.remoteType.__name__

    @memoize
    def remoteClass(self):
        """Return the class at the remote end of our relationship."""
        return importClass(self._schema.remoteClass)

    def remoteName(self):
        """Return the name at the remote end of our relationship."""
        return self._schema.remoteName


    def cb_isCopyable(self):
        """Don't let relationships move off their managers"""
        return 0


    def cb_isMoveable(self):
        """Don't let relationships move off their managers"""
        return 0


InitializeClass(RDBMSRelationshipBase)
