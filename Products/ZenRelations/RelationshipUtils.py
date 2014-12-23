# 
# Copyright (C) Zenoss, Inc. 2014-2015, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
from Products.ZenRelations.utils import memoize


@memoize
def _storeFunction(self):
    """
    Wrapper function to import DB at run-time
    """
    from Globals import DB

    return DB.storage._with_store


@memoize
def _loadFunction(self):
    """
    Wrapper function to import DB at run-time
    """
    from Globals import DB

    return DB.storage._with_store


def doUpdate(f):
    return _storeFunction()(f)
doInsert = doDelete = doUpdate


def doSelect(f):
    return _loadFunction()(f)
