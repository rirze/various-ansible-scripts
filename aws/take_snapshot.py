#!/usr/bin/python3
from datetime import datetime
import boto3
import boto3.session
from time import time

from multiprocessing import Barrier, Lock, Process

ec2 = boto3.client('ec2')

filters = [
    {
        'Name': 'tag:DRSnapshot',
        'Values': ['Y']
    },
    {
        'Name': 'tag:Name',
        'Values': ['MO-PRD sapqe4db']
    }
]


def create_snapshot(volumeinfo, synchronizer, serializer):
    synchronizer.wait()
    start = time()
    session = boto3.session.Session()
    thread_ec2 = session.resource('ec2')
    thread_ec2.create_snapshot(Description=script_datetime,
                               VolumeId=volumeinfo['VolumeId'],
                               TagSpecifications=[
                                   {
                                       'ResourceType': 'snapshot',
                                       'Tags': [
                                           {
                                               'Key': 'InstanceType',
                                               'Value': volumeinfo['InstanceType'],
                                           },
                                           {
                                               'Key': 'DeviceName',
                                               'Value': volumeinfo['DeviceName']
                                           },
                                           {
                                               'Key': 'InstanceName',
                                               'Value': volumeinfo['Name']

                                           }
                                       ]
                                   }
                               ])

    end = time()
    with serializer:
        print(f"{start} \t {end}")


def aws_tags_to_dict(tags_list):
    tags_dict = {}
    for tag in tags_list:
        if 'key' in tag and not tag['key'].startswith('aws:'):
            tags_dict[tag['key']] = tag['value']
        elif 'Key' in tag and not tag['Key'].startswith('aws:'):
            tags_dict[tag['Key']] = tag['Value']

    return tags_dict


def dict_to_aws_tags(tags_dict):
    tags_list = []
    for k, v in tags_dict.items():
        tags_list.append({'Key': k, 'Value': v})

    return tags_list


if __name__ == '__main__':
    instances = ec2.describe_instances(Filters=filters)

    instance_list = []
    volumes = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:

            tags = aws_tags_to_dict(instance['Tags'])
            # instance_list.append({'InstanceId': instance['InstanceId'],
            #                       'Tags': instance['Tags'],
            #                       'InstanceType': instance['InstanceType'],
            #                       'Devices': [{'DeviceName': d['DeviceName'],
            #                                    'VolumeId': d['Ebs']['VolumeId']} for d in instance['BlockDeviceMappings']]})
            tags_to_add = {k: tags[k] for k in ('Name',)}
            volumes.extend([{'DeviceName': d['DeviceName'],
                             'VolumeId': d['Ebs']['VolumeId'],
                             'InstanceType': instance['InstanceType'],
                             **tags_to_add
                             } for d in instance['BlockDeviceMappings']])


    script_datetime = datetime.utcnow().ctime()  # 'Tue Dec 17 21:55:11 2019'


    # with cf.ProcessPoolExecutor() as executor:
    #     [print(t) for t in executor.map(create_snapshot, volumes)]

    synchronizer = Barrier(len(volumes))
    serializer = Lock()

    [Process(target=create_snapshot, args=(v, synchronizer, serializer)).start() for v in volumes]
    # print(p)
    # print('Process list created')

    # map(lambda x: x.start(), p)
    # print('All Processes started')

    # map(lambda x: x.join(), p)
    # print('All Processes joined')

    # [print(x) for x in map(lambda x: x.join(), p)]
