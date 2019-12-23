#!/usr/bin/python3
from datetime import datetime
import concurrent.futures as cf
import boto3

ec2 = boto3.client('ec2')

filters = [
    {
        'Name': 'tag:System',
        'Values': ['SystemName']
    },
    {
        'Name': 'tag:Type',
        'Values': ['db', 'app']

    }
]


def create_snapshots(instance):
    ec2.create_snapshots(Description=script_datetime,
                         InstanceSpecification={
                             'InstanceId': instance,
                             'ExcludeBootVolume': False
                         },
                         CopyTagsFromSource='volume')


if __name__ == '__main__':
    instances = ec2.describe_instances(Filters=filters)

    volumes = []
    instance_list = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_list.append(instance['InstanceId'])
            # tags = [d for d in instance['Tags'] if d['Key'] != 'Name']
            # for volume in instance['BlockDeviceMappings']:
            #     ebs = volume['Ebs']
            #     volumes.append({'VolumeId': ebs['VolumeId'], 'Tags': tags +
            #                     [{'Key': 'Mount Point', 'Value': volume['DeviceName']}]})

    script_datetime = datetime.utcnow().ctime()  # 'Tue Dec 17 21:55:11 2019'

    with cf.ProcessPoolExecutor() as executor:
        executor.map(create_snapshots, instance_list)
