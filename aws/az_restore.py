#!/usr/bin/python3
from collections import defaultdict
from aws_cdk import core
from aws_cdk.aws_ec2 import CfnLaunchTemplate as LT, CfnInstance as Instance
import boto3

boto_ec2 = boto3.client('ec2')

filters = [
    {
        'Name': 'tag-key',
        'Values': [tag]
    }
    for tag in ['System', 'Type', 'DeviceName']
]


def organize_snapshots(snapshots):
    mapping = defaultdict(list)

    for s in snapshots:
        tags = dict(map(lambda x: (x['Key'], x['Value']), s['Tags']))
        mapping[(tags['System'], tags['Type'])].append({'SnapshotId': s['SnapshotId'],
                                                        'DeviceName': tags['DeviceName']})

    return mapping


class LaunchTemplateStack(core.Stack):
    def __init__(self, app: core.App, id: str, mapping) -> None:
        super().__init__(app, id)

        for (System, Type), volumes in mapping.items():
            launch_template_data = LT.LaunchTemplateDataProperty(
                block_device_mappings=[
                    LT.BlockDeviceMappingProperty(device_name=tags['DeviceName'],
                                                  ebs=LT.EbsProperty(snapshot_id=tags['SnapshotId']))
                    for tags in volumes
                ],
                instance_type='dummy_instance_type',
                tag_specifications=[
                    LT.TagSpecificationProperty(resource_type='instance',
                                                tags=[
                                                    core.CfnTag(key="System", value=System),
                                                    core.CfnTag(key="Type", value=Type)
                                                ])
                ])

            lt = LT(self, System + Type + 'LaunchTemplate',
                    launch_template_data=launch_template_data,
                    launch_template_name=System + Type + 'LaunchTemplate')

            Instance(self, System + Type + 'Instance', launch_template=Instance.LaunchTemplateSpecificationProperty(version=lt.attr_latest_version_number, launch_template_id=lt.ref))


if __name__ == '__main__':
    # raw_snapshots = boto_ec2.describe_snapshots(Filters=filters, OwnerIds=['self'])

    # mapping = organize_snapshots(raw_snapshots['Snapshots'])
    mapping = {('System', 'Type'): [{'SnapshotId': '1',
                                     'DeviceName': '\\'},
                                    {'SnapshotId': '1',
                                     'DeviceName': '\\sda\\xvd'}]}

    app = core.App(outdir='/home/chronos/ship')
    LaunchTemplateStack(app, "RestoredTheseLaunchTemplates", mapping)
    print(app.synth().directory)
