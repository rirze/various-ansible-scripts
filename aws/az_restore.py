#!/usr/bin/python3
from collections import defaultdict
from aws_cdk import core
from aws_cdk.aws_ec2 import CfnLaunchTemplate as LT, CfnInstance as Instance
import yaml
import json
import boto3


boto_ec2 = boto3.client('ec2')

filters = [
    {
        'Name': 'tag-key',
        'Values': [tag]
    }
    for tag in ['InstanceName', 'DeviceName', 'InstanceType']
]


def organize_snapshots(snapshots):
    if not snapshots:
        raise Exception("No Snapshots found! Check your tags/filters")

    mapping = defaultdict(list)

    for s in snapshots:
        tags = dict(map(lambda x: (x['Key'], x['Value']), s['Tags']))
        mapping[(tags['InstanceName'], tags['InstanceType'])].append({
            'SnapshotId': s['SnapshotId'],
            'DeviceName': tags['DeviceName']
        })

    return mapping


class LaunchTemplateStack(core.Stack):
    def __init__(self, app: core.App, id: str, mapping) -> None:
        super().__init__(app, id)

        for (InstanceName, InstanceType), volumes in mapping.items():
            launch_template_data = LT.LaunchTemplateDataProperty(
                block_device_mappings=[
                    LT.BlockDeviceMappingProperty(device_name=tags['DeviceName'],
                                                  ebs=LT.EbsProperty(snapshot_id=tags['SnapshotId']))
                    for tags in volumes
                ],
                instance_type=InstanceType,
                tag_specifications=[
                    LT.TagSpecificationProperty(resource_type='instance',
                                                tags=[
                                                    # core.CfnTag(key="System", value=System),
                                                    # core.CfnTag(key="Type", value=Type)
                                                    core.CfnTag(key="Name", value=InstanceName)
                                                ])
                ])

            lt = LT(self, InstanceName + 'LaunchTemplate',
                    launch_template_data=launch_template_data,
                    launch_template_name=InstanceName + 'LaunchTemplate')

            Instance(self, InstanceName + 'Instance',
                     launch_template=Instance.LaunchTemplateSpecificationProperty(
                         version=lt.attr_latest_version_number,
                         launch_template_id=lt.ref))


if __name__ == '__main__':
    raw_snapshots = boto_ec2.describe_snapshots(Filters=filters, OwnerIds=['self'])

    mapping = organize_snapshots(raw_snapshots['Snapshots'])
    # mapping = {('SystemName', 'SomeType', 'SomeInstanceType'): [{'SnapshotId': '1',
    #                                                              'DeviceName': '/'},
    #                                                             {'SnapshotId': '2',
    #                                                              'DeviceName': '/sda/xvd'}]}
    app = core.App()
    stack = LaunchTemplateStack(app, "RestoredLaunchTemplates", mapping)
    directory = app.synth().directory

    with open("RestoredLaunchTemplates.yml", 'w', encoding='utf-8') as yfile:
        yaml.dump(json.load(open(directory + "/RestoredLaunchTemplates" + '.template.json')), yfile)

    print("See 'RestoredLaunchTemplates.yml' for the template")
