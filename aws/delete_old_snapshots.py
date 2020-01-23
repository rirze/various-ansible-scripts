#!/usr/bin/python3
from datetime import timedelta
import boto3
from collections import defaultdict

ec2 = boto3.client('ec2')

oldest_diff = timedelta(hours=4, minutes=0)  # all snapshots within this time period from the lastest snapshot will be kept
minimum_number = 4  # the latest n number of snapshots will be kept

filters = [
    {
        'Name': 'tag-key',
        'Values': [tag]
    }
    for tag in ('DeviceName',)  # 'InstanceId')
]


def get_snapshots_to_delete():
    snapshots = ec2.describe_snapshots(Filters=filters, OwnerIds=['self'])['Snapshots']

    ordering = defaultdict(list)

    for snap in snapshots:
        vol_id = snap['VolumeId']

        ordering[vol_id].append((snap['StartTime'], snap['SnapshotId']))

    to_delete = []
    for vol_id, snaps in ordering.items():
        snaps.sort(key=lambda x: x[0], reverse=True)  # so latest is index=0, oldest is last index

        if len(snaps) <= minimum_number:
            continue

        latest_ts = snaps[0][0]
        found_break = False

        for ts, s in snaps[minimum_number:]:
            if found_break:
                to_delete.append(s)

            elif ts + oldest_diff < latest_ts:
                found_break = True
                to_delete.append(s)

    return to_delete


def delete_snapshots(snapshotIds):
    print(f'About to delete {len(snapshotIds)} snapshots!')

    for s in snapshotIds:
        ec2.delete_snapshot(SnapshotId=s)

    print(f'{len(snapshotIds)} snapshots deleted!')


def delete_old_snapshots():
    to_delete = get_snapshots_to_delete()
    delete_snapshots(to_delete)


if __name__ == '__main__':
    delete_old_snapshots()
