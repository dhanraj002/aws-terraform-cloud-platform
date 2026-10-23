"""Publish an immutable task revision and reject silent rollback as success."""
import argparse
import copy
import json
import re
import subprocess
import time

REGISTER_FIELDS = {
    "family", "taskRoleArn", "executionRoleArn", "networkMode", "containerDefinitions",
    "volumes", "placementConstraints", "requiresCompatibilities", "cpu", "memory",
    "pidMode", "ipcMode", "proxyConfiguration", "inferenceAccelerators",
    "ephemeralStorage", "runtimePlatform",
}

def aws(*args):
    result = subprocess.run(['aws', *args, '--output', 'json', '--no-cli-pager'],
                            check=True, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)

def task_revision(current, image, revision, fail_readiness=False):
    if not re.fullmatch(r"[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/[a-z0-9._/-]+@sha256:[a-f0-9]{64}", image):
        raise ValueError("Expected an ECR image pinned by sha256 digest")
    result = {k: copy.deepcopy(v) for k, v in current.items() if k in REGISTER_FIELDS}
    matches = [c for c in result['containerDefinitions'] if c['name'] == 'app']
    if len(matches) != 1:
        raise ValueError("Expected exactly one app container")
    app = matches[0]
    app['image'] = image
    env = {e['name']: e['value'] for e in app.get('environment', [])}
    env.update(APP_REVISION=revision, FAIL_READINESS=str(fail_readiness).lower())
    app['environment'] = [{'name': k, 'value': v} for k, v in sorted(env.items())]
    return result

def assert_release(service, expected):
    primary = [d for d in service.get('deployments', []) if d['status'] == 'PRIMARY']
    if len(primary) != 1 or primary[0]['taskDefinition'] != expected:
        raise RuntimeError("Expected task revision is not PRIMARY: rollback or concurrent release")
    if primary[0].get('rolloutState') != 'COMPLETED':
        raise RuntimeError("Expected deployment has not completed")
    if service.get('desiredCount', 0) < 1 or service['runningCount'] != service['desiredCount']:
        raise RuntimeError("Expected running tasks are missing")
    if len(service['deployments']) != 1 or service.get('pendingCount', 0):
        raise RuntimeError("Old or pending tasks remain")

def describe(cluster, service):
    response = aws('ecs', 'describe-services', '--cluster', cluster, '--services', service)
    if response.get('failures') or len(response.get('services', [])) != 1:
        raise RuntimeError('ECS service not found or inaccessible')
    return response['services'][0]

def release(cluster, service_name, image, revision, fail_readiness=False):
    current = describe(cluster, service_name)
    # Reject a second writer or a service without a completed rollback target.
    assert_release(current, current['taskDefinition'])
    definition = aws('ecs', 'describe-task-definition', '--task-definition', current['taskDefinition'])['taskDefinition']
    candidate = task_revision(definition, image, revision, fail_readiness)
    registered = aws('ecs', 'register-task-definition', '--cli-input-json', json.dumps(candidate))
    expected = registered['taskDefinition']['taskDefinitionArn']
    print(json.dumps({'previous': current['taskDefinition'], 'candidate': expected}), flush=True)
    aws('ecs', 'update-service', '--cluster', cluster, '--service', service_name, '--task-definition', expected)
    deadline = time.monotonic() + 900
    visibility_deadline = time.monotonic() + 60
    seen_candidate = False
    while time.monotonic() < deadline:
        service = describe(cluster, service_name)
        candidates = [d for d in service['deployments'] if d['taskDefinition'] == expected]
        if any(d.get('rolloutState') == 'FAILED' for d in candidates):
            raise RuntimeError('Candidate failed; check ECS events and automatic rollback')
        if not candidates:
            # DescribeServices may briefly return the old revision after UpdateService.
            # Once observed, a disappearing candidate is a rollback/concurrent update.
            if seen_candidate or time.monotonic() >= visibility_deadline:
                raise RuntimeError('Candidate disappeared or was never observed; inspect ECS events')
        else:
            seen_candidate = True
            if len(service['deployments']) == 1 and service.get('pendingCount', 0) == 0:
                if candidates[0].get('rolloutState') == 'COMPLETED':
                    assert_release(service, expected)
                    print(json.dumps({'released': expected}))
                    return
        time.sleep(15)
    raise TimeoutError('Release did not complete within 15 minutes; inspect ECS before retrying')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cluster', required=True)
    parser.add_argument('--service', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--fail-readiness', action='store_true')
    args = parser.parse_args()
    release(args.cluster, args.service, args.image, args.revision, args.fail_readiness)

if __name__ == '__main__':
    main()
