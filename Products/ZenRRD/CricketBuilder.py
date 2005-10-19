#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""CricketBuilder

Gets cricket config from dmd and writes it out on the cricket server

$Id: CricketBuilder.py,v 1.6 2004/04/07 00:02:44 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import time
import os.path
import xmlrpclib
import pprint

import Globals

from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenUtils.Utils import basicAuthUrl

from utils import RRDException

class TargetDataError(RRDException):pass

class CricketBuilder(CmdBase):

    def __init__(self):
        CmdBase.__init__(self)
        self.curtargetpath = ''
        self.curtarget = ''



    def buildOptions(self):

        CmdBase.buildOptions(self)

        self.parser.add_option("-z", "--zopeurl",
                    dest="zopeurl",
                    help="XMLRPC url path for cricket configuration server ")

        self.parser.add_option("-u", "--zopeusername",
                    dest="zopeusername",
                    help="username for zope server")

        self.parser.add_option("-p", "--zopepassword",
                    dest="zopepassword")
   
        self.parser.add_option("-d", "--devicename",
                    dest="devicename")

        self.parser.add_option("-F", "--force",
                    dest="force", action='store_true',
                    help="force generation of cricket data " 
                         "(even without change to the device)")
    
        self.parser.add_option("-D", "--debug",
                    dest="debug", action='store_true')
    
    def build(self):
        url = basicAuthUrl(self.options.zopeusername, 
                            self.options.zopepassword,
                            self.options.zopeurl)
        server = xmlrpclib.Server(url)
        cricketDevices = server.cricketDeviceList()
        if self.options.devicename:
            cricketDevices = filter(
                lambda x: x.endswith(self.options.devicename), cricketDevices)
        if self.options.debug:
            pprint.pprint(cricketDevices)
        for devurl in cricketDevices:
            self.buildDevice(devurl)


    def buildDevice(self, devurl):        
        try:
            self.log.info("building device %s", devurl.split("/")[-1])
            devurl = basicAuthUrl(self.options.zopeusername, 
                                  self.options.zopepassword, devurl)
            device = xmlrpclib.Server(devurl, allow_none=True)
            cricketData = device.cricketGenerate(self.options.force)
            if self.options.debug:
                pprint.pprint(cricketData)
            for targetpath, targetdatas in cricketData:
                if targetpath[0] == '/': targetpath = targetpath[1:]
                tfile = self.opentargets(targetpath)
                tfile.write("# Generated by CricketBuilder.py on %s\n" 
                                % time.strftime('%Y/%m/%d %H:%M:%S %Z'))
                tfile.write("# From DMD %s\n" % self.options.zopeurl)
                tfile.write("# !!! Do not edit manually !!!\n\n")
                for targetdata in targetdatas:
                    self.printTargets(tfile, targetdata)
                tfile.close()
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("Exception processing device %s", devurl)


    def opentargets(self, targetpath):
        """open targets file based on targetpath"""
        self.curtargetpath = targetpath
        self.log.debug("building target file %s" % targetpath)
        if not os.path.exists(targetpath):
            os.makedirs(targetpath, 0755)
        targetfile = targetpath + '/targets'
        return open(targetfile, 'w')
       

    def printTargets(self, tfile, targetdata):
        """print out target file using target data"""
        if not targetdata.has_key('target'):
            raise TargetDataError, "Malformed targetdata no target found"
        self.curtarget = targetdata['target']
        self.log.debug("building target %s" % self.curtarget)
        tfile.write("target %s\n" % self.curtarget)
        for attrib, value in targetdata.items():
            if attrib == 'target' or value == '' or value == None: continue
            value = str(value)
            self.log.debug("attrib=%s value=%s" % (attrib, value))
            if value.find(' ') > -1: value = '"%s"' % value
            tfile.write("\t%s = %s\n" % (attrib, value))
        tfile.write('\n')
   

if __name__ == '__main__':
    cb = CricketBuilder()
    cb.build()
