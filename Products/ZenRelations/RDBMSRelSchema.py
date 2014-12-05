##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
from Products.ZenRelations.RelSchema import RelSchema
from RDBMSToOneRelationship import RDBMSToOneRelationship
from ToManyRelationship import ToManyRelationship
from ToManyContRelationship import ToManyContRelationship


RELMETATYPES = (
    'ToOneRelationship', 'ToManyContRelationship', 'ToManyRelationship')


class RDBMSRelSchema(RelSchema):
    pass


class ToOne(RDBMSRelSchema):
    _relationClass = RDBMSToOneRelationship


class ToMany(RDBMSRelSchema):
    _relationClass = ToManyRelationship


class ToManyCont(RDBMSRelSchema):
    _relationClass = ToManyContRelationship
