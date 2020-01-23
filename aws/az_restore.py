#!/usr/bin/python3
from collections import defaultdict
from aws_cdk import core
from aws_cdk.aws_ec2 import CfnInstance as Instance
import yaml
import json
import boto3
from time import time

from aws_helpers import aws_tags_to_dict


availability_zone = 'us-east-1b'

boto_ec2 = boto3.client('ec2')

filters = [
    {
        'Name': 'tag-key',
        'Values': [tag]
    }
    for tag in ['DeviceName', 'InstanceId']
]


def organize_snapshots(snapshots):
    if not snapshots:
        raise Exception("No Snapshots found! Check your tags/filters")

    mapping = defaultdict(dict)

    for s in snapshots:
        tags = aws_tags_to_dict(s['Tags'])

        item = mapping[tags['InstanceId']].get(tags['DeviceName'], None)

        if not item or item['StartTime'] < s['StartTime']:
            mapping[tags['InstanceId']].setdefault('BlockDeviceMappings', {})
            mapping[tags['InstanceId']]['BlockDeviceMappings'][tags['DeviceName']] = {
                'SnapshotId': s['SnapshotId'],
                'StartTime': s['StartTime']
            }

            if 'RootDeviceName' in tags:
                for t, tk in tags.items():
                    if t not in ('DeviceName', 'InstanceId'):
                        mapping[tags['InstanceId']][t] = tk

    return mapping


def get_mirror_subnet(subnet_group):

    mirror_subnet_info = boto_ec2.describe_subnets(Filters=[
        {
            'Name': 'tag:SubnetGroup',
            'Values': [subnet_group]
        },
        {
            'Name': 'availabilityZone',
            'Values': [availability_zone]

        }
    ])['Subnets'][0]

    return mirror_subnet_info['SubnetId']


class InstanceStack(core.Stack):
    def __init__(self, app: core.App, id: str, mapping) -> None:
        super().__init__(app, id)

        subnet_mirrors = {}
        ami_list = []
        for InstanceId, info in mapping.items():
            block_mappings = [{'DeviceName': d,
                               'Ebs': {'SnapshotId': s['SnapshotId']}}
                              for d, s in info['BlockDeviceMappings'].items()]

            name = info['Name']
            ami = boto_ec2.register_image(BlockDeviceMappings=block_mappings,
                                          Name=f'{name} AMI for AZ restore {time()}',
                                          RootDeviceName=info['RootDeviceName'],
                                          VirtualizationType=info['VirtualizationType'],
                                          Architecture=info['Architecture'])

            ami_list.append(ami['ImageId'])

            subnet_group = info['SubnetGroup']
            if subnet_group not in subnet_mirrors:
                subnet_mirrors[subnet_group] = get_mirror_subnet(subnet_group)

            Instance(self, name.replace(' ', '') + 'Instance',
                     instance_type=info['InstanceType'],
                     availability_zone=availability_zone,
                     iam_instance_profile=info['IamInstanceProfileName'],
                     image_id=ami['ImageId'],
                     security_group_ids=info['SecurityGroupIds'].split(','),
                     subnet_id=subnet_mirrors[subnet_group])

        boto_ec2.create_tags(Resources=ami_list, Tags=[
            {
                'Name': 'az_restore',
                'Value': 'Y'
            }
        ])


def get_mapping():
    raw_snapshots = boto_ec2.describe_snapshots(Filters=filters, OwnerIds=['self'])

    mapping = organize_snapshots(raw_snapshots['Snapshots'])

    return mapping


def create_cfn(mapping):
    app = core.App()
    _ = InstanceStack(app, 'RestoredInstances', mapping)
    directory = app.synth().directory

    output_yaml_filename = 'RestoredInstances.yml'
    with open(output_yaml_filename, 'w', encoding='utf-8') as yfile:
        yaml.dump(json.load(open(directory + '/RestoredInstances' + '.template.json')), yfile)

    print(f"See '{output_yaml_filename}' for the template")


def restore_to_az():
    mapping = get_mapping()
    create_cfn(mapping)


if __name__ == '__main__':
    restore_to_az()
