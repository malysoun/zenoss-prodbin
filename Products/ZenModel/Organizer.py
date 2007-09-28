###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


__doc__="""Organizer

$Id: DeviceOrganizer.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

from Globals import InitializeClass
from Acquisition import aq_parent
from AccessControl import ClassSecurityInfo, getSecurityManager

import simplejson

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import travAndColl
from Products.ZenUtils.Exceptions import ZenPathError, ZentinelException

from EventView import EventView
from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable
from ZenossSecurity import ZEN_COMMON
        
class Organizer(ZenModelRM, EventView):
    """
    @summary: OrganizerBase class is base for all hierarchical organization classes.
    It allows Organizers to be addressed and created with file system like
    paths like /Devices/Servers.  Organizers have a containment relation
    called children.  Subclasses must define the attribute:

    dmdRootName - root in the dmd database for this organizer
    """

    _properties = (
                    {'id':'description', 'type':'string', 'mode':'w'},
                   )

    _relations = ZenModelRM._relations
 
    security = ClassSecurityInfo()
    security.declareObjectProtected("View")

    def __init__(self, id, description = ''):
        """
        @param id: Name of this organizer
        @type id: string
        @param description: A decription of this organizer
        @type description: string
        @return: N/A
        @rtype: Organizer
        @raise:
        @summary: Creates a new organizer
        """
        ZenModelRM.__init__(self, id)
        self.description = description

    def childMoveTargets(self):
        """ 
        Returns a list of all organizer names 
        under the same root excluding ourselves
        
        @return: A list of organizers excluding our self.
        @rtype: list
        @raise:
        @summary:
        @todo: We should be using either deviceMoveTargets or childMoveTargets
            
        >>> dmd.Events.getOrganizerName() in dmd.Events.childMoveTargets()
        False
        """ 
        myname = self.getOrganizerName()
        return filter(lambda x: x != myname, 
                    self.getDmdRoot(self.dmdRootName).getOrganizerNames())

    def childMoveTargetsJSON(self):
        """
        Returns a list of all organizer names  
        under the same root excluding ourselves (as a json dump)
        
        @return: Organizer names under a the same organizer root as a json dump
        @rtype: list
        @raise:
        @summary:
        """
        return simplejson.dumps(self.childMoveTargets());

    def getChildMoveTarget(self, moveTargetName):
        """
        Returns an organizer under the same root
        
        @param moveTargetName: Name of the organizer
        @type moveTargetName: string
        @rtype: Organizer
        @summary:
        
        >>> dmd.Devices.getChildMoveTarget('Server')
        <DeviceClass at /zport/dmd/Devices/Server>
        """
        return self.getDmdRoot(self.dmdRootName).getOrganizer(moveTargetName)
        
           
    security.declareProtected(ZEN_COMMON, "children")
    def children(self, sort=False, checkPerm=True, spec=None):
        """
        Returns the immediate children of an organizer
        
        @param sort: If True, sorts the returned children. 
            Defaults to False.
        @type sort: boolean
        @param checkPerm: If True, checks if the user has the permission 
            to view each child. Defaults to True.
        @type checkPerm: boolean
        @param spec: If set, returns children of the specified meta_type.
            Defaults to None.
        @type spec: string
        @return: A list of children of the organizer
        @rtype: list
        @raise:
        @summary: Return children of our organizer who have same type as parent.
        @permission: ZEN_COMMON
        
        >>> dmd.Devices.Printer.children()
        [<DeviceClass at /zport/dmd/Devices/Printer/Laser>,
        <DeviceClass at /zport/dmd/Devices/Printer/InkJet>]
        """
        if spec is None:
            spec = self.meta_type
        kids = self.objectValues(spec=spec)
        if checkPerm:
            kids = [ kid for kid in kids if self.checkRemotePerm("View", kid)]
        if sort: kids.sort(lambda x,y: cmp(x.primarySortKey(), 
                                           y.primarySortKey()))
        return kids


    def childIds(self, spec=None):
        """
        Returns the ids of the immediate children of an organizer
        
        @param spec: If set, returns children of the specified meta_type.
            Defaults to None.
        @type spec: string
        @return: Ids of children within our organizer 
        @rtype: list
        @summary:
        
        >>> dmd.Devices.childIds()
        ['Discovered', 'Network', 'Server', 'Printer', 'Power', 'KVM', 'Ping']
        """
        if spec is None:
            spec = self.meta_type
            #spec = self.getDefaultSpecForChildren()
        return self.objectIds(spec=spec)


    security.declareProtected(ZEN_COMMON, "countChildren")
    def countChildren(self, spec=None):
        """
        Returns the number of all the children underneath an organizer
        
        @param spec: If set, returns children of the specified meta_type.
            Defaults to None.
        @type spec: string 
        @return: A count of all our contained children.
        @rtype: integer
        @summary:
        @permission: ZEN_COMMON
        
        >>> dmd.Devices.countChildren()
        24
        """
        if spec is None:
            spec = self.meta_type
            #spec = self.getDefaultSpecForChildren()
        count = len(self.objectIds(spec=spec))
        for child in self.children(spec=spec):
            count += child.countChildren(spec=spec)
        return count
        

    security.declareProtected('Add DMD Objects', 'manage_addOrganizer')
    def manage_addOrganizer(self, newPath, REQUEST=None):
        """
        Adds a new organizer under this organizer, 
        if given a fully qualified path it will create an organizer at that path
        
        @param newPath: Path of the organizer to be created
        @type newPath:  string
        @param REQUEST: Request object
        @type REQUEST: dict
        @return: called object
        @rtype: 
        @raise: ZentinelException
        @summary: Add an organizer to the database
        @permission: 'Add DMD Objects'
        
        >>> dmd.Devices.manage_addOrganizer('/Devices/DocTest')
        """ 
        if not newPath: return self.callZenScreen(REQUEST)
        try:
            if newPath.startswith("/"):
                self.createOrganizer(newPath)
            else:
                org = self.__class__(newPath)
                self._setObject(org.id, org)
        except ZentinelException, e:
            if REQUEST: 
                REQUEST['message'] = 'Error: %s' % e
                return self.callZenScreen(REQUEST)
        if REQUEST:
            REQUEST['message'] = "%s %s added" % (self.__class__.__name__, newPath)
            return self.callZenScreen(REQUEST)
            

    security.declareProtected('Delete objects', 'manage_deleteOrganizer')
    def manage_deleteOrganizer(self, orgname, REQUEST=None):
        """
        Deletes an organizer underneath this organizer
        
        @param orgname: Name of the organizer to delete
        @type orgname: string
        @param REQUEST: Request object
        @type REQUEST: dict
        @return: called object
        @rtype:
        @raise: KeyError
        @summary: Delete an Organizer from its parent name is relative to parent
        @permission: 'Delete objects'
        
        >>> dmd.Devices.manage_deleteOrganizer('/Devices/Server/Linux')
        """
        if orgname.startswith("/"):
            try:
                orgroot = self.getDmdRoot(self.dmdRootName)
                organizer = orgroot.getOrganizer(orgname)
                parent = aq_parent(organizer)
                parent._delObject(organizer.getId())
            except KeyError:
                pass  # we may have already deleted a sub object
        else:
            self._delObject(orgname)
        if REQUEST: 
            REQUEST['message'] = "%s %s deleted" % (self.__class__.__name__, orgname)
            return self.callZenScreen(REQUEST)


    security.declareProtected('Delete objects', 'manage_deleteOrganizers')
    def manage_deleteOrganizers(self, organizerPaths=None, REQUEST=None):
        """
        Deletes organizers underneath this organizer
        
        @param organizerPaths: Names of organizer to be deleted
        @type organizerPaths: list
        @param REQUEST: Request object
        @type REQUEST: dict
        @return: called object
        @rtype: 
        @raise:
        @summary: Delete a list of Organizers from the database using their ids.
        @permission: 'Delete objects'
        
        >>> dmd.Devices.manage_deleteOrganizers(['/Devices/Server/Linux',
        ... '/Devices/Server/Windows'])   
        """
        if not organizerPaths: 
            REQUEST['message'] = "Organizer not specified, not deleted"
            return self.callZenScreen(REQUEST)
        for organizerName in organizerPaths:
            self.manage_deleteOrganizer(organizerName)
        if REQUEST:
            plural = ''
            if len(organizerPaths) > 1: plural = 's'
            REQUEST['message'] = "%s%s %s deleted" % (self.__class__.__name__, 
                                        plural, ', '.join(organizerPaths))
            return self.callZenScreen(REQUEST)
            
    
    def deviceMoveTargets(self):
        """
        DEPRECATED - see childMoveTargets
        Return list of all organizers excluding our self.
        
        @return: A sorted list of organizers excluding our self.
        @rtype: list
        @raise:
        @summary: Return list of all organizers excluding our self.
        @todo: We should be using either deviceMoveTargets or childMoveTargets
        """
        targets = filter(lambda x: x != self.getOrganizerName(),
            self.getDmdRoot(self.dmdRootName).getOrganizerNames())
        targets.sort(lambda x,y: cmp(x.lower(), y.lower()))
        return targets

   
    def moveOrganizer(self, moveTarget, organizerPaths=None, REQUEST=None):
        """
        Move organizers under this organizer to another organizer
        
        @param moveTarget: Name of the destination organizer
        @type moveTarget: string
        @param organizerPaths: Paths of organizers to be moved
        @type organizerPaths: list
        @param REQUEST: Request object
        @type REQUEST: dict
        @return: called object
        @rtype: 
        @raise:
        @summary: Move organizer to moveTarget.
                      
        >>> dmd.Events.Status.moveOrganizer('/Events/Ignore',
        ... ['Ping', 'Snmp'])        
        """
        if not moveTarget or not organizerPaths: return self()
        target = self.getDmdRoot(self.dmdRootName).getOrganizer(moveTarget)
        movedStuff = False
        for organizerName in organizerPaths:
            if moveTarget.find(organizerName) > -1: continue
            obj = self._getOb(organizerName)
            obj._operation = 1 #move object
            self._delObject(organizerName)
            target._setObject(organizerName, obj)
            movedStuff = True
        if REQUEST:
            if movedStuff: 
                plural = ''
                if len(organizerPaths) > 1: plural = 's'
                REQUEST['message'] = "%s%s %s moved to %s" % (self.__class__.__name__,
                    plural, ', '.join(organizerPaths), moveTarget)
            else: REQUEST['message'] = "No %s were moved" % self.__class__.__name__
            return target.callZenScreen(REQUEST)
            
            
    def createOrganizer(self, path):
        """
        Creates an organizer with a specified path. 
        Use manage_addOrganizer instead
        
        @param path: Path of the organizer to create
        @type path: string
        @return: Organizer created with the specified path
        @rtype: Organizer
        @summary: Create and return and an Organizer from its path.
        """
        return self.createHierarchyObj(self.getDmdRoot(self.dmdRootName), 
                                           path,self.__class__)


    def getOrganizer(self, path):
        """
        Get an organizer by path under the same root
        
        @param path: Path of the organizer to retrieve
        @type path: string
        @return: Organizer with the specified path
        @rtype: Organizer
        @raise:
        @summary: Return and an Organizer from its path.
                                             
        >>> dmd.Events.Status.getOrganizer('/Status/Snmp')
        <EventClass at /zport/dmd/Events/Status/Snmp>
        >>> dmd.Events.Status.getOrganizer('Status/Snmp')
        <EventClass at /zport/dmd/Events/Status/Snmp>
        >>> dmd.Events.Status.getOrganizer('/Events/Status/Snmp')
        <EventClass at /zport/dmd/Events/Status/Snmp>
        """
        if path.startswith("/"): path = path[1:]
        return self.getDmdRoot(self.dmdRootName).getObjByPath(path) 


    security.declareProtected(ZEN_COMMON, "getOrganizerName")
    def getOrganizerName(self):
        """
        @return: Name of this organizer
        @rtype: string 
        @summary: Return the DMD path of an Organizer without its 
            dmdSubRel names.
        @permission: ZEN_COMMON
               
        >>> dmd.Events.Status.Snmp.getOrganizerName()
        '/Status/Snmp'
        """
        return self.getPrimaryDmdId(self.dmdRootName)
    getDmdKey = getOrganizerName


    security.declareProtected(ZEN_COMMON, "getOrganizerNames")
    def getOrganizerNames(self, addblank=False):
        """
        Returns a list of all organizer names under this organizer
        
        @param addblank: If True, add a blank item in the list.
            Defaults to False.
        @type addblank: boolean
        @return: The DMD paths of all Organizers below this instance.
        @rtype: list
        @raise:
        @summary:
        @permission: ZEN_COMMON
        
        >>> dmd.Events.Security.getOrganizerNames()
        ['/Security', '/Security/Auth', '/Security/Conn', 
        '/Security/Conn/Close', '/Security/Conn/Open', '/Security/Login', 
        '/Security/Login/BadPass', '/Security/Login/Fail', '/Security/Sudo', 
        '/Security/Virus']
        """
        groupNames = []
        user = getSecurityManager().getUser()
        if user.has_permission("View", self):
            groupNames.append(self.getOrganizerName())
        for subgroup in self.children(checkPerm=False):
            groupNames.extend(subgroup.getOrganizerNames())
        if self.id == self.dmdRootName: 
            if addblank: groupNames.append("")
        groupNames.sort(lambda x,y: cmp(x.lower(), y.lower()))
        return groupNames


    def _getCatalog(self):
        """
        Returns a catalog instance for this organizer.
        
        @return: The catalog instance for this Organizer.
        @rtype: ZCatalog
        @raise:
        @note: Catalog is found using the attribute default_catalog.
        """
        catalog = None
        if hasattr(self, self.default_catalog):
            catalog = getattr(self, self.default_catalog)
        return catalog


    security.declareProtected(ZEN_COMMON, "getSubOrganizers")
    def getSubOrganizers(self):
        """
        Returns all the organizers under this organizer
        
        @return: Organizers below this instance
        @rtype: list
        @raise:
        @summary:
        @permission: ZEN_COMMON
        
        >>> dmd.Events.Security.getSubOrganizers()
        [<EventClass at /zport/dmd/Events/Security/Login>, 
        <EventClass at /zport/dmd/Events/Security/Sudo>, 
        <EventClass at /zport/dmd/Events/Security/Conn>, 
        <EventClass at /zport/dmd/Events/Security/Virus>, 
        <EventClass at /zport/dmd/Events/Security/Auth>, 
        <EventClass at /zport/dmd/Events/Security/Login/BadPass>, 
        <EventClass at /zport/dmd/Events/Security/Login/Fail>, 
        <EventClass at /zport/dmd/Events/Security/Conn/Open>, 
        <EventClass at /zport/dmd/Events/Security/Conn/Close>]
        """
        orgs = self.children()
        for child in self.children():
            orgs.extend(child.getSubOrganizers())
        return orgs
                       
    security.declareProtected(ZEN_COMMON, "getSubInstances")
    def getSubInstanceIds(self, rel):
        """
        Returns the object ids of all the instances of a specific relation
        under this organizer
        
        @param rel: The name of the relation to traverse
        @type rel: string
        @return: The object ids of instances under an relation of this org
        @rtype: list
        @raise: AttributeError
        @summary:
        @permission: ZEN_COMMON
        
        >>> dmd.Events.Security.Login.getSubInstanceIds('instances')
        ['MSExchangeIS Mailbox Store_1009', 'MSExchangeIS Mailbox Store_1011', 
        'defaultmapping', 'dropbear', 'sshd', 'MSFTPSVC_100', 'W3SVC_100', 
        'dropbear', 'remote(pam_unix)']
        """
        relobj = getattr(self, rel, None)
        if not relobj:
            raise AttributeError, "%s not found on %s" % (rel, self.id)
        objs = relobj.objectIds()
        for suborg in self.children():
            objs.extend(suborg.getSubInstanceIds(rel))
        return objs
        
    security.declareProtected(ZEN_COMMON, "getSubInstances")
    def getSubInstances(self, rel):
        """
        Returns the object isntances of a specific relation under this organizer
        
        @param rel: The name of the relation to traverse
        @type rel: string
        @return: The object instances under an relation of this org
        @rtype: list
        @raise: AttributeError
        @summary: 
        @permission: ZEN_COMMON
        
        >>> dmd.Events.Security.Login.getSubInstances('instances')
        [<EventClassInst at /zport/dmd/Events/Security/Login/instances/MSExchangeIS Mailbox Store_1009>, 
        <EventClassInst at /zport/dmd/Events/Security/Login/instances/MSExchangeIS Mailbox Store_1011>, 
        <EventClassInst at /zport/dmd/Events/Security/Login/instances/defaultmapping>, 
        <EventClassInst at /zport/dmd/Events/Security/Login/BadPass/instances/dropbear>, 
        <EventClassInst at /zport/dmd/Events/Security/Login/BadPass/instances/sshd>, 
        <EventClassInst at /zport/dmd/Events/Security/Login/Fail/instances/MSFTPSVC_100>, 
        <EventClassInst at /zport/dmd/Events/Security/Login/Fail/instances/W3SVC_100>, 
        <EventClassInst at /zport/dmd/Events/Security/Login/Fail/instances/dropbear>, 
        <EventClassInst at /zport/dmd/Events/Security/Login/Fail/instances/remote(pam_unix)>]
        """
        relobj = getattr(self, rel, None)
        if not relobj:
            raise AttributeError, "%s not found on %s" % (rel, self.id)
        objs = relobj()
        if not objs: objs = []
        for suborg in self.children():
            objs.extend(suborg.getSubInstances(rel))
        return objs
        
    security.declareProtected(ZEN_COMMON, "getSubInstancesGen")
    def getSubInstancesGen(self, rel):
        """
        Returns the object isntances of a specific relation under this organizer 
        
        @param rel: The name of the relation to traverse
        @type rel: string
        @return: The object ids of instances under an relation of this org
        @rtype: generator
        @raise: AttributeError
        @summary: 
        @permission: ZEN_COMMON
        """
        relobj = getattr(self, rel, None)
        if not relobj: 
            raise AttributeError, "%s not found on %s" % (rel, self.id)
        for obj in relobj.objectValuesGen():
            yield obj
        for suborg in self.children():
            for obj in suborg.getSubInstancesGen(rel):
                yield obj
                    
    def exportXmlHook(self, ofile, ignorerels):
        """
        Calls exportXml on the children of this organizer
        
        @param ofile: The file to output
        @type ofile: File
        @param ignorerels: Relations to ignore
        @type ignorerels: list
        @return: None
        @rtype: None
        @raise:
        @summary: Export of our child objects.
        """
        map(lambda o: o.exportXml(ofile, ignorerels), self.children())


InitializeClass(Organizer)

