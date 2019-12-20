#!/usr/bin/python3
from collections import defaultdict
from aws_cdk import aws_ec2 as cdk_ec2, core
import boto3

boto_ec2 = boto3.client('ec2')

filters = [
    {
        'Name': 'tag-key',
        'Values': ['System', 'Type', 'DeviceName']
    }
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
            lc_d = cdk_ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                block_device_mappings=[cdk_ec2.CfnLaunchTemplate.BlockDeviceMappingProperty(
                    device_name=tags['DeviceName'], ebs=cdk_ec2.CfnLaunchTemplate.EbsProperty(
                        snapshot_id=tags['SnapshotId'])) for tags in volumes],
                instance_type='dummy_instance_type',
                tag_specifications=[cdk_ec2.CfnLaunchTemplate.TagSpecificationProperty(
                    resource_type='instance',
                    tags=[core.CfnTag(key="System", value=System),
                          core.CfnTag(key="Type", value=Type)])])

            lc = cdk_ec2.CfnLaunchTemplate(self, System + Type, launch_template_data=lc_d)


if __name__ == '__main__':
    raw_snapshots = boto_ec2.describe_snapshots(Filters=filters, OwnerIds=['self'])

    mapping = organize_snapshots(raw_snapshots['Snapshots'])

    app = core.App(outdir='/home/chronos/ship')
    LaunchTemplateStack(app, "RestoredTheseLaunchTemplates", mapping)
    print(app.synth().directory)
