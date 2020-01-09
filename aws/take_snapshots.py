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
        'Values': ['test']
    }
]


def create_snapshots(instanceinfo):
    ec2.create_snapshots(Description=script_datetime,
                         InstanceSpecification={
                             'InstanceId': instanceinfo['InstanceId'],
                         },
                         CopyTagsFromSource='volume',
                         TagSpecifications=[
                             {
                                 'ResourceType': 'snapshot',
                                 'Tags': [
                                     {
                                         'Key': 'InstanceType',
                                         'Value': instanceinfo['InstanceType']
                                     }
                                 ]
                             }
                         ])


if __name__ == '__main__':
    instances = ec2.describe_instances(Filters=filters)

    instance_list = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_list.append({'InstanceId': instance['InstanceId'],
                                  'InstanceType': instance['InstanceType']})

    script_datetime = datetime.utcnow().ctime()  # 'Tue Dec 17 21:55:11 2019'

    with cf.ProcessPoolExecutor() as executor:
        executor.map(create_snapshots, instance_list)
