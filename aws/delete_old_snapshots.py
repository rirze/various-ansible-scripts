#!/usr/bin/python3
from datetime import timedelta
import boto3

ec2 = boto3.client('ec2')

oldest_diff = timedelta(hours=0, minutes=10)

filters = [
    {

    }
]

if __name__ == '__main__':

    snapshots = ec2.describe_snapshots(Filters=filters, OwnerIds=['self'])

    times = [s['StartTime'] for s in snapshots['Snapshots']]

    latest_time = max(times)

    cutoff_time = latest_time - oldest_diff

    for snap in snapshots['Snapshots']:
        if snap['StartTime'] < cutoff_time:
            ec2.delete_snapshot(SnapshotId=snap['SnapshotId'])
