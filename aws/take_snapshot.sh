#!/bin/bash
volumes="$@"
date_now=$(date -R -u)

for volume_id in $volumes
do
    aws ec2 create-snapshot --description "$date_now" \
        --volume-id $volume_id --copy-tags-from-source volume \
        > /dev/null 2>&1 &
done
