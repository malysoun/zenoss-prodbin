##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
from Products.ZenRelations.RelationshipUtils import doSelect


__doc__ = """RelationshipBase

RelationshipBase is the base class for RelationshipManager
and ToManyRelationship."""

import logging
log = logging.getLogger("zen.Relations")

from Globals import InitializeClass
from Acquisition import aq_base
from zope import interface

from Products.Zuul.decorators import memoize
from Products.Zuul.utils import safe_hasattr
from Products.ZenRelations.Exceptions import *
from Products.ZenRelations.utils import importClass

from PrimaryPathObjectManager import PrimaryPathManager

class IRelationship(interface.Interface):
    """
    Marker interface.
    """
    def __call__():
        """Return the contents of this relation."""

    def getId():
        pass

    def hasobject(obj):
        """Does this relationship relate to obj."""

    def addRelation(obj):
        """Form a bi-directional relation between self and obj."""

    def removeRelation(obj=None, suppress_events=False):
        """remove an object from a relationship"""

    def remoteType():
        """Return the type of the remote end of our relationship."""

    def remoteTypeName():
        """Return the type of the remote end of our relationship."""

    def remoteClass():
        """Return the class at the remote end of our relationship."""

    def remoteName():
        """Return the name at the remote end of our relationship."""

    def cb_isCopyable():
        """Don't let relationships move off their managers"""

    def cb_isMoveable():
        """Don't let relationships move off their managers"""

    def checkRelation(repair=False):
        """Check to make sure that relationship bidirectionality is ok."""


class RelationshipBase(PrimaryPathManager):
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

    def parentId(self):
        id = self.__primary_parent__.getPrimaryId()
        return id if id.startswith('/zport/') else '/zport/' + id

    def _remoteRemove(self, obj=None):
        raise NotImplementedError

    def hasobject(self, obj):
        """does this relation point to the object passed"""
        myId = self.__primary_parent__.getPrimaryId()
        uid = obj.getPrimaryId()

        def get(connection, cursor):
            sql = "SELECT COUNT(*) FROM relations WHERE uid=%s AND name=%s AND remote_uid=%s"
            cursor.execute(sql, (myId, self.id, uid))
            return bool(cursor.fetchone()[0])
        return doSelect(get)



InitializeClass(RelationshipBase)
