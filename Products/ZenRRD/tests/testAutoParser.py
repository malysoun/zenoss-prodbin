###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from Products.ZenRRD.tests.testCacti import TestCacti
from Products.ZenRRD.tests.testNagiosParser import TestNagiosParser

from Products.ZenRRD.tests.BaseParsersTestCase import Object
from Products.ZenRRD.CommandParser import ParsedResults
from Products.ZenRRD.parsers.Auto import Auto


class TestAutoParser(TestNagiosParser, TestCacti):
    def setUp(self):
        self.cmd = Object()
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        self.cmd.deviceConfig = deviceConfig

        self.cmd.parser = "Auto"
        self.cmd.result = Object()
        self.cmd.result.exitCode = 2
        self.cmd.severity = 2
        self.cmd.command = "testAutoPlugin"
        self.cmd.eventKey = "AutoKey"
        self.cmd.eventClass = "/Cmd"
        self.cmd.component = "zencommand"
        self.parser = Auto()
        self.results = ParsedResults()
        self.dpdata = dict(processName='someJob a b c',
                       ignoreParams=False,
                       alertOnRestart=True,
                       failSeverity=3)


    def testNagiosAutoCaseApache(self):
        self.cmd.points = []

        slotDNSLookup = Object()
        slotDNSLookup.id = 'slotDNSLookup'
        slotDNSLookup.data = self.dpdata
        self.cmd.points.append(slotDNSLookup)

        totalAccesses = Object()
        totalAccesses.id = 'totalAccesses'
        totalAccesses.data = self.dpdata
        self.cmd.points.append(totalAccesses)


        slotReadingRequest = Object()
        slotReadingRequest.id = 'slotReadingRequest'
        slotReadingRequest.data = self.dpdata
        self.cmd.points.append(slotReadingRequest)

        busyServers = Object()
        busyServers.id = 'busyServers'
        busyServers.data = self.dpdata
        self.cmd.points.append(busyServers)


        self.cmd.result.output = 'STATUS OK|slotDNSLookup=0 totalAccesses=38 slotReadingRequest=0 totalKBytes=15 busyServers=1 slotKeepAlive=0 slotGracefullyFinishing=0 bytesPerReq=404.211 cpuLoad=.000142755 bytesPerSec=2.19272 slotLogging=0 slotSendingReply=1 slotStartingUp=0 reqPerSec=.0054247 slotWaiting=7 slotOpen=248 idleServers=7'
        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(4, len(self.results.values))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestAutoParser))
    return suite