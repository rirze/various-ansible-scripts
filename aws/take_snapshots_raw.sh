#!/bin/bash
instances=$(aws ec2 describe-instances --filters Name=tag:System,Values=SystemName Name=tag:Type,Values=app --query 'Reservations[].Instances[].[InstanceId,InstanceType]' | jq -c '.[]')
date_now=$(date -R -u)

for i in ${instances//[\]\[\"]}
do
    instance_id=${i%,*}
    instance_type=${i#*,}
    read -rd '' json <<-EOF
{
    "Description": "$date_now",
    "InstanceSpecification": {
        "InstanceId": "$instance_id"
    },
    "TagSpecifications": [
        {
            "ResourceType": "snapshot",
            "Tags": [
                {
                    "Key": "InstanceType",
                    "Value": "$instance_type"
                }
            ]
        }
    ],
    "DryRun": true,
    "CopyTagsFromSource": "volume"
}
EOF
    aws ec2 create-snapshots --cli-input-json "$json"
done
