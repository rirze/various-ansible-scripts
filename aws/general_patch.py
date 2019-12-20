#!/usr/bin/python3
from pssh.clients.native import ParallelSSHClient
from pssh.utils import load_private_key

import boto3

ec2 = boto3.client('ec2')

filters = [
    {
        'Name': 'tag:patch',
        'Values': ['y']
    }
]

def patch(instances):
    client = ParallelSSHClient(instances, user='ec2-user', pkey='/home/chronos/second2.pem')

    output = client.run_command('sudo yum check-update')
    output2 = client.run_command('sudo yum update -y')

    for host, host_output in output2.items():
        for line in host_output.stdout:
            print(line)

    return output


if __name__ == '__main__':
    to_patch_instances = ec2.describe_instances(Filters=filters)

    ips = []
    for instance_list in to_patch_instances['Reservations']:
        for i in instance_list['Instances']:
            # pprint(i)
            ips.append(i['PublicIpAddress'])

    print(patch(ips))
