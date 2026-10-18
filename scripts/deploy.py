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
                            check=True, capture_output=True, text=True)
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cluster', required=True)
    parser.add_argument('--service', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--fail-readiness', action='store_true')
    args = parser.parse_args()
    current = describe(args.cluster, args.service)
    definition = aws('ecs', 'describe-task-definition', '--task-definition', current['taskDefinition'])['taskDefinition']
    candidate = task_revision(definition, args.image, args.revision, args.fail_readiness)
    registered = aws('ecs', 'register-task-definition', '--cli-input-json', json.dumps(candidate))
    expected = registered['taskDefinition']['taskDefinitionArn']
    print(json.dumps({'previous': current['taskDefinition'], 'candidate': expected}), flush=True)
    aws('ecs', 'update-service', '--cluster', args.cluster, '--service', args.service, '--task-definition', expected)
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        service = describe(args.cluster, args.service)
        candidates = [d for d in service['deployments'] if d['taskDefinition'] == expected]
        if any(d.get('rolloutState') == 'FAILED' for d in candidates):
            raise RuntimeError('Candidate failed; check ECS events and automatic rollback')
        if not candidates:
            raise RuntimeError('Candidate disappeared; rollback or concurrent release')
        if len(service['deployments']) == 1 and service.get('pendingCount', 0) == 0:
            if candidates[0].get('rolloutState') == 'COMPLETED':
                assert_release(service, expected)
                print(json.dumps({'released': expected}))
                return
        time.sleep(15)
    raise TimeoutError('Release did not complete within 15 minutes; inspect ECS before retrying')

if __name__ == '__main__':
    main()
