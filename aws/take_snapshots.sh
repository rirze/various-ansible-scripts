#!/bin/bash
instances=$(aws ec2 describe-instances --filters Name=tag:System,Values=SystemName Name=tag:Type,Values=app --query 'Reservations[].Instances[].[InstanceId,InstanceType]' | jq -c '.[]')
date_now=$(date -R -u)

for i in ${instances//[\]\[\"]}
do
    instance_id=${i%,*}
    instance_type=${i#*,}
    aws ec2 create-snapshots --description "$date_now" \
        --instance-specification InstanceId=$instance_id --copy-tags-from-source volume \
        --tag-specifications 'ResourceType=snapshot,Tags=[{Key=InstanceType,Value=$instance_type}]' \
        > /dev/null 2>&1 &
done
