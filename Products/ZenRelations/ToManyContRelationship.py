##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2014-2015 all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
from Products.ZenRelations import ToManyRelationship

__doc__ = """ToManyContRelationship
A to-many container relationship
"""

import logging
log = logging.getLogger("zen.Relations")

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from OFS.ObjectManager import checkValidId

from OFS.event import ObjectWillBeAddedEvent
from OFS.event import ObjectWillBeRemovedEvent
from zope.event import notify
from zope.container.contained import ObjectAddedEvent
from zope.container.contained import ObjectRemovedEvent

from BTrees.OOBTree import OOBTree

from Exceptions import zenmarker

from Products.ZenUtils.Utils import unused

def manage_addToManyContRelationship(context, id, REQUEST=None):
    """factory for ToManyRelationship"""
    rel = ToManyContRelationship(id)
    context._setObject(rel.id, rel)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
    return rel.id


addToManyContRelationship = DTMLFile('dtml/addToManyContRelationship', globals())


class ToManyContRelationship(ToManyRelationship):
    """
    ToManyContRelationship is the ToMany side of a realtionship that
    contains its related objects (like the normal Zope ObjectManager)
    """

    meta_type = "ToManyContRelationship"

    security = ClassSecurityInfo()


    def __init__(self, id):
        """set our instance values"""
        super(ToManyContRelationship, self).__init__(id)
        self._objects = OOBTree()

    def setCount(self):
        super(ToManyRelationship, self).setCount()
        if self._count != len(self._objects):
            #Something has gone wrong. Sync with the database now!
            self.checkRelation(repair=True)

    def _safeOfObjects(self):
        """
        Try to safely return ZenPack objects rather than
        causing imports to fail.
        """
        objs = []
        for ob in self.objectValues():
            try:
                objs.append(ob.__of__(self))
            except AttributeError:
                log.info("Ignoring unresolvable object '%s'", str(ob))
        return objs

    def __call__(self):
        """when we are called return our related object in our aq context"""
        return self._safeOfObjects()

    def __getattr__(self, name):
        """look in the two object stores for related objects"""
        if '_objects' in self.__dict__:
            objects = self._objects
            if name in objects:
                return objects[name]
        raise AttributeError("Unable to find the attribute '%s'" % name)

    def __hasattr__(self, name):
        """check to see if we have an object by an id
        this will fail if passed a short id and object is stored
        with fullid (ie: it is related not contained)
        use hasobject to get around this issue"""
        parentId = self.parentId()
        uids = self.getRemoteUids()
        return '/'.join((parentId, self.id, name)) in uids

    def addRelation(self, obj):
        """Override base to run manage_afterAdd like ObjectManager"""
        if self.hasobject(obj):
            log.debug("obj %s already exists on %s", obj.getPrimaryId(),
                      self.getPrimaryId())

        notify(ObjectWillBeAddedEvent(obj, self, obj.getId()))
        super(ToManyContRelationship, self).addRelation(self, obj)
        obj = obj.__of__(self)
        o = self._getOb(obj.id)
        notify(ObjectAddedEvent(o, self, o.getId()))

    def _setObject(self,id,object,roles=None,user=None,set_owner=1):
        """ObjectManager interface to add contained object."""
        unused(user, roles, set_owner)
        object.__primary_parent__ = aq_base(self)
        self.addRelation(object)
        return object.getId()

    def manage_afterAdd(self, item, container):
        # Don't do recursion anymore, a subscriber does that.
        pass
    manage_afterAdd.__five_method__ = True

    def manage_afterClone(self, item):
        # Don't do recursion anymore, a subscriber does that.
        pass
    manage_afterClone.__five_method__ = True

    def manage_beforeDelete(self, item, container):
        # Don't do recursion anymore, a subscriber does that.
        pass
    manage_beforeDelete.__five_method__ = True

    def _add(self, obj):
        """add an object to a relationship.
        if a relationship already exists, error"""
        id = obj.id
        checkValidId(self, id)

        super(ToManyContRelationship, self)._add(obj)

        self._objects[id] = aq_base(obj)

    def _remove(self, obj=None, suppress_events=False):
        """remove object from our side of a relationship"""
        objs = [obj] if obj else self.objectValuesAll()
        if not suppress_events:
            for robj in objs:
                notify(ObjectWillBeRemovedEvent(robj, self, robj.getId()))

        super(ToManyContRelationship, self)._remove(obj, suppress_events)

        if obj:
            del self._objects[id]
        else:
            self._objects = OOBTree()
            self.__primary_parent__._p_changed = True

        if not suppress_events:
            for robj in objs:
                notify(ObjectRemovedEvent(robj, self, robj.getId()))

    def _getOb(self, id, default=zenmarker):
        """look up in our local store and wrap in our aq_chain"""
        if self.__hasattr__(id):
            return self._objects[id].__of__(self)
        elif default == zenmarker:
            raise AttributeError("Unable to find %s" % id)
        return default

    security.declareProtected('View', 'objectIds')
    def objectIds(self, spec=None):
        """only return contained objects"""
        if not spec:
            return self.objectIdsAll()
        return [obj.id for obj in self.objectValues(spec)]

    security.declareProtected('View', 'objectIdsAll')
    def objectIdsAll(self):
        """only return contained objects"""
        return [uid.rsplit('/', 1)[1] for uid in self.getRemoteUids()]

    security.declareProtected('View', 'objectValues')
    def objectValues(self, spec=None):
        """override to only return owned objects for many to many rel"""
        specFilter = None
        if spec:
            if isinstance(spec, basestring):
                spec = [spec]
            specFilter = lambda x: x.meta_type in spec
        return filter(specFilter, self.objectValuesGen())

    security.declareProtected('View', 'objectValuesAll')
    objectValuesAll = objectValues

    def objectValuesGen(self):
        """Generator that returns all related objects."""
        return (self._objects[id].__of__(self) for id in self.objectIdsAll())

    def objectItems(self, spec=None):
        return [(obj.getPrimaryId(), obj) for obj in self.objectValues()]
    objectItemsAll = objectItems

    def _getCopy(self, container):
        """
        make new relation add copies of contained objs
        and refs if the relation is a many to many
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        rel = rel.__of__(container)
        norelcopy = getattr(self, 'zNoRelationshipCopy', [])
        if self.id in norelcopy: return rel
        for oobj in self.objectValuesAll():
            cobj = oobj._getCopy(rel)
            rel._setObject(cobj.id, cobj)
        return rel

    def checkValidId(self, id):
        """
        Is this a valid id for this container?
        """
        checkValidId(self, id)
        return True

    def exportXml(self, ofile, ignorerels=[]):
        """Return an xml representation of a ToManyContRelationship
        <tomanycont id='interfaces'>
            <object id='hme0'
                module='Products.Confmon.IpInterface' class='IpInterface'>
                <property></property> etc....
            </object>
        </tomanycont>
        """
        if self.countObjects() == 0: return
        ofile.write("<tomanycont id='%s'>\n" % self.id)
        for obj in self.objectValues():
            obj.exportXml(ofile, ignorerels)
        ofile.write("</tomanycont>\n")


    def checkRelation(self, repair=False):
        """Check to make sure that relationship bidirectionality is ok.
        """
        if len(self._objects):
            log.debug("checking relation: %s", self.id)
        else:
            return

        # look for objects that don't point back to us
        # or who should no longer exist in the database
        remoteName = self.remoteName()
        parentObject = self.getPrimaryParent()
        for obj in self._objects.values():
            if not hasattr(obj, remoteName):
                path = parentObject.getPrimaryUrlPath()
                if repair:
                    log.warn("Deleting %s object '%s' relation '%s' (missing remote relation '%s')",
                             path, obj, self.id, remoteName)
                    self._remove(obj, True)
                    continue
                else:
                    msg = "%s object '%s' relation '%s' missing remote relation '%s'" % (
                        path, obj, self.id, remoteName)
                    raise AttributeError(msg)

            rrel = getattr(obj, remoteName)
            if not rrel.hasobject(parentObject):
                log.error("remote relation %s doesn't point back to %s",
                          rrel.getPrimaryId(), self.getPrimaryId())
                if repair:
                    log.warn("reconnecting relation %s to relation %s",
                             rrel.getPrimaryId(),self.getPrimaryId())
                    rrel._add(parentObject)


InitializeClass(ToManyContRelationship)


class ToManyContSublocations(object):
    """
    Adapter so the event dispatching can propagate to children.
    """
    def __init__(self, container):
        self.container = container
    def sublocations(self):
        return (ob for ob in self.container.objectValuesAll())
