##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2014-2015 all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

__doc__ = """ToOneRelationship

ToOneRelationship is a class used on a RelationshipManager
to give it toOne management Functions.
"""

import sys
import logging

log = logging.getLogger("zen.Relations")


# Base classes for ToOneRelationship
from RelationshipBase import IRelationship, RelationshipBase

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from App.Dialogs import MessageDialog
from zope import interface

from zExceptions import NotFound
from Products.ZenRelations.Exceptions import *
from Products.ZenUtils.Utils import unused, getObjByPath
from RelationshipUtils import doSelect, doDelete, doInsert

def manage_addToOneRelationship(context, id, REQUEST=None):
    """ToOneRelationship Factory"""
    r = ToOneRelationship(id)
    context._setObject(id, r)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')


addToOneRelationship = DTMLFile('dtml/addToOneRelationship', globals())


class ToOneRelationship(RelationshipBase):
    """ToOneRelationship represents a to one Relationship
    on a RelationshipManager"""

    interface.implements(IRelationship)

    meta_type = 'ToOneRelationship'

    security = ClassSecurityInfo()

    def __init__(self, id):
        self.id = id

    def __call__(self):
        """return the related object when a ToOne relation is called"""
        uid = self.getRemoteUid()
        if uid:
            return self.dmd.unrestrictedTraverse(uid)

    def getRemoteUid(self):
        def get(connection, cursor):
            sql = "SELECT remote_uid from relations where uid=%s and name=%s"
            cursor.execute(sql, (self.__primary_parent__.getPrimaryId(), self.id))
            return cursor.fetchone()
        return doSelect(get)

    def hasobject(self, obj):
        """does this relation point to the object passed"""
        myId = self.__primary_parent__.getPrimaryId()
        uid = obj.getPrimaryId()

        def get(connection, cursor):
            #return self.obj == obj
            sql = "SELECT COUNT(*) FROM relations WHERE uid=%s AND name=%s AND remote_uid=%s"
            return cursor.execute(sql, (myId, self.id, uid)).result
        return doSelect(get)

    def _add(self, obj):
        """add a to one side of a relationship
        if a relationship already exists clear it"""
        myId = self.__primary_parent__.getPrimaryId()
        uid = obj.getPrimaryId()

        #if obj == self.obj: raise RelationshipExistsError
        if self.hasobject(obj):
            raise RelationshipExistsError

        #self.obj = aq_base(obj)
        #self._remoteRemove()
        self._remove()
        #self.__primary_parent__._p_changed = True

        def put(connection, cursor):
            sql = "INSERT INTO relations (uid, name, remote_uid) values (%s, %s, %s)"
            cursor.executemany(sql, ((myId, self.id, uid),
                                     (uid, self.remoteName(), myId)))
        doInsert(put)

    def _remove(self, obj=None, suppress_events=False):
        #find our current object
        myId = self.__primary_parent__.getPrimaryId()
        uid = self.getRemoteUid()
        if uid:
            if obj.getPrimaryId() != uid:
                raise ObjectNotFound("object %s was not found on %s" % (obj, self))

            # if obj == None or obj == self.obj:
            #     self.obj = None
            #     self.__primary_parent__._p_changed = True
            def delete(connection, cursor):
                sql = "DELETE FROM relations WHERE uid=%s AND name=%s AND remote_uid=%s"
                cursor.executemany(sql, ((myId, self.id, uid),
                                         (uid, self.remoteName(), myId)))
            doDelete(delete)

    def _remoteRemove(self, obj=None):
        raise NotImplementedError

    security.declareProtected('View', 'getRelatedId')

    def getRelatedId(self):
        """return the id of the our related object"""
        uid = self.getRemoteUid()
        if uid:
            return uid.rsplit('/', 1)[-1]
        else:
            return None

    def _getCopy(self, container):
        """
        Create ToOne copy. If this is the one side of one to many
        we set our side of the relation to point towards the related
        object (maintain the relationship across the copy).
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        rel = rel.__of__(container)

        if self.remoteTypeName() == "ToMany":
            obj = self()
            if obj:
                rel.addRelation(obj)
        return rel

    def manage_workspace(self, REQUEST):
        """ZMI function to return the workspace of the related object"""
        obj = self()
        if obj:
            objurl = obj.getPrimaryUrlPath()
            REQUEST['RESPONSE'].redirect(objurl + '/manage_workspace')
        else:
            return MessageDialog(
                title="No Relationship Error",
                message="This relationship does not currently point to an object",
                action="manage_main")

    def manage_main(self, REQUEST=None):
        """ZMI function to redirect to parent relationship manager"""
        REQUEST['RESPONSE'].redirect(
            self.getPrimaryParent().getPrimaryUrlPath() + '/manage_workspace')


    #FIXME - please make me go away, I'm so ugly!
    security.declareProtected('View', 'getPrimaryLink')

    def getPrimaryLink(self, target=None):
        """get the link tag of a related object"""
        link = ""
        obj = self()
        if obj:
            if not obj.checkRemotePerm("View", obj):
                link = obj.id
            else:
                attributes = ''
                if target is not None:
                    attributes = "target='%s' " % (target,)
                link = "<a %shref='%s'>%s</a>" % (
                    attributes,
                    obj.getPrimaryUrlPath(),
                    obj.id)
        return link

    def getPrimaryHref(self):
        """Return the primary URL for our related object.
        """
        obj = self()
        return obj.getPrimaryUrlPath()

    def exportXml(self, ofile, ignorerels=[]):
        """return an xml representation of a ToOneRelationship
        <toone id='cricket'>
            /Monitors/Cricket/crk0.srv.hcvlny.cv.net
        </toone>"""
        obj = self()
        if not obj or self.remoteTypeName() == "ToManyCont":
            return
        ofile.write("<toone id='%s' objid='%s'/>\n" % (
            self.id, obj.getPrimaryId()))

    def checkRelation(self, repair=False):
        """Check to make sure that relationship bidirectionality is ok.
        """
        obj = self()
        if not obj:
            return
        log.debug("checking relation: %s", self.id)

        try:
            ppath = obj.getPrimaryPath()
            getObjByPath(self, ppath)
        except (KeyError, NotFound):
            log.error("object %s in relation %s has been deleted from its primary path",
                      obj.getPrimaryId(), self.getPrimaryId())
            if repair:
                log.warn("removing object %s from relation %s",
                         obj.getPrimaryId(), self.getPrimaryId())
                self._remove(obj=obj, suppress_events=True)
                return

        parobj = self.getPrimaryParent()
        try:
            rname = self.remoteName()
        except ZenSchemaError:
            path = parobj.getPrimaryUrlPath()
            log.exception("Object %s (parent %s) has a bad schema" % (obj, path))
            log.warn("Might be able to fix by re-installing ZenPack")
            return

        rrel = getattr(obj, rname)
        if not rrel.hasobject(parobj):
            log.error("remote relation %s doesn't point back to %s",
                      rrel.getPrimaryId(), self.getPrimaryId())
            if repair:
                log.warn("reconnecting relation %s to relation %s",
                         rrel.getPrimaryId(), self.getPrimaryId())
                rrel._add(parobj)


InitializeClass(ToOneRelationship)
