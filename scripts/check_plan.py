"""Check concrete planned tags only on customer-managed taggable resources.

This is deliberately not an account-wide SCP: AWS-managed resources may have
service-specific tagging behavior. Unknown planned tags fail closed.
"""
import json
import sys
REQUIRED = {'Project', 'Owner', 'Environment', 'CostCentre', 'ManagedBy'}
TAGGABLE = {'aws_vpc', 'aws_subnet', 'aws_internet_gateway', 'aws_nat_gateway',
            'aws_eip', 'aws_route_table', 'aws_security_group', 'aws_lb',
            'aws_lb_target_group', 'aws_lb_listener', 'aws_ecs_cluster',
            'aws_ecs_service', 'aws_ecs_task_definition', 'aws_cloudwatch_log_group',
            'aws_iam_role', 'aws_s3_bucket', 'aws_ecr_repository', 'aws_sns_topic'}

def violations(plan):
    errors = []
    for resource in plan.get('resource_changes', []):
        change = resource['change']
        if resource.get('mode') != 'managed' or resource['type'] not in TAGGABLE or change['actions'] == ['delete']:
            continue
        tags = (change.get('after') or {}).get('tags_all') or {}
        missing = sorted(k for k in REQUIRED if not isinstance(tags.get(k), str) or not tags[k].strip())
        if missing:
            errors.append(f"{resource['address']}: missing/unknown tags {', '.join(missing)}")
    return errors

if __name__ == '__main__':
    with open(sys.argv[1]) as source:
        errors = violations(json.load(source))
    print('\n'.join(errors) if errors else 'Tag checks passed')
    sys.exit(bool(errors))
