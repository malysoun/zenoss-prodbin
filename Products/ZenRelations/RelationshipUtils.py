# 
# Copyright (C) Zenoss, Inc. 2014-2015, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 

from Globals import DB


def doUpdate(f):
    return DB.storage._with_store(f)
doInsert = doDelete = doUpdate


def doSelect(f):
    return DB.storage._with_load(f)
