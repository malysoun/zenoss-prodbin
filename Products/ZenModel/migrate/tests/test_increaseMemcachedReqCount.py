##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest


class test_increaseMemcachedReqCount(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that setting for memcached was changed
    """
    initial_servicedef = 'zenoss-resmgr-lite-5.1.0.json'
    expected_servicedef = 'zenoss-resmgr-lite-5.1.0-increaseMemcachedReqCount.json'
    migration_module_name = 'increaseMemcachedReqCount'
    migration_class_name = 'IncreaseMemcachedReqCount'
