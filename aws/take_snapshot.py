#!/usr/bin/python3
from datetime import datetime
import boto3
import boto3.session
from time import time

from multiprocessing import Barrier, Lock, Process

from aws_helpers import aws_tags_to_dict, dict_to_aws_tags

ec2 = boto3.client('ec2')

filters = [
    {
        'Name': 'tag:DRSnapshot',
        'Values': ['Y']
    },
    {
        'Name': 'tag:Name',
        'Values': ['MO-PRD sapqe4db', 'MO-PRD sapqe4ci']
    }
]


def create_snapshot(volumeinfo, instance_info, synchronizer, serializer, script_datetime=datetime.utcnow().ctime()):
    instance_id = volumeinfo['InstanceId']

    tags = [
        {
            'Key': 'DeviceName',
            'Value': volumeinfo['DeviceName']
        },
        {
            'Key': 'InstanceId',
            'Value': instance_id
        },
    ]

    if volumeinfo['DeviceName'] == instance_info[instance_id]['RootDeviceName']:
        tags.extend(dict_to_aws_tags(instance_info[instance_id]))

    session = boto3.session.Session()
    thread_ec2 = session.resource('ec2')

    synchronizer.wait()
    start = time()
    thread_ec2.create_snapshot(Description=script_datetime,
                               VolumeId=volumeinfo['VolumeId'],
                               TagSpecifications=[
                                   {
                                       'ResourceType': 'snapshot',
                                       'Tags': tags
                                   }
                               ])

    end = time()
    with serializer:
        print(f"{start} \t {end}")




def take_snapshots():
    instances = ec2.describe_instances(Filters=filters)

    instance_info = {}
    subnet_info = {}
    volumes = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:

            tags = aws_tags_to_dict(instance['Tags'])
            tags_to_add = {k: tags[k] for k in ('Name', 'Project') if k in tags}

            volumes.extend([{'DeviceName': d['DeviceName'],
                             'VolumeId': d['Ebs']['VolumeId'],
                             'InstanceId': instance['InstanceId']}
                            for d in instance['BlockDeviceMappings']])

            subnet_id = instance['SubnetId']
            if subnet_id not in subnet_info:
                subnet_query = ec2.describe_subnets(SubnetIds=[subnet_id])['Subnets'][0]
                subnet_tags = aws_tags_to_dict(subnet_query['Tags'])

                subnet_info[subnet_id] = subnet_tags['SubnetGroup']

            instance_info[instance['InstanceId']] = {'InstanceType': instance['InstanceType'],
                                                     'VpcId': instance['VpcId'],
                                                     'SecurityGroupIds': ','.join(sg['GroupId'] for sg in instance['SecurityGroups']),
                                                     'SubnetGroup': subnet_info[subnet_id],
                                                     'IamInstanceProfileName': instance['IamInstanceProfile']['Arn'].split('/')[1],
                                                     'RootDeviceName': instance['RootDeviceName'],
                                                     'Architecture': instance['Architecture'],
                                                     'VirtualizationType': instance['VirtualizationType'],
                                                     **tags_to_add}


    script_datetime = datetime.utcnow().ctime()  # 'Tue Dec 17 21:55:11 2019'

    synchronizer = Barrier(len(volumes))
    serializer = Lock()

    [Process(target=create_snapshot, args=(v, instance_info, synchronizer, serializer, script_datetime)).start()
     for v in volumes]


if __name__ == '__main__':
    take_snapshots()
