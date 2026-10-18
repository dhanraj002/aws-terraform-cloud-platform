# Release failure and recovery

## Objective

Prove that a failed candidate does not replace a healthy release, and that the pipeline reports the failure even after ECS recovers. Run only in the sandbox lab. No measured result is recorded until the exercise is executed.

## Establish a baseline

1. Complete a normal deployment and verify `/`, `/healthz`, and `/readyz` over HTTPS.
2. Record the commit SHA, image digest, task-definition ARN and UTC timestamp.
3. Confirm the service has two running tasks, zero pending tasks and one COMPLETED deployment. Confirm the alert subscription.

```bash
aws ecs describe-services --region eu-central-1 --cluster release-platform --services release-platform --query 'services[0].{task:taskDefinition,deployments:deployments,events:events[0:10]}'
```

## Trigger an unhealthy release

Run Deploy lab with `fail_readiness=true`. This changes an environment variable only on the new candidate. Its `/healthz` continues returning 200 but `/readyz` returns 503, so the ALB rejects it. The old healthy tasks remain during the rolling update.

Expected: failed target-health checks, circuit-breaker failure, automatic rollback to the prior completed task definition, and a red deployment job. The job may report failure before rollback finishes; verify recovery separately. It must never mark this drill green merely because the service is stable again.

## Diagnose

- Read ECS service events first: distinguish image-pull, IAM, network and target-health problems.
- Check `/ecs/release-platform` logs and target-group health reasons. The probe deliberately avoids logging request data.
- Verify execution-role ECR/log permissions, private-subnet routes, NAT availability, and ALB-to-task port 8080 access.
- If OIDC fails before deployment, check audience, repository/environment subject, GitHub environment branch rules and the role ARN. Do not log tokens.
- If a new release is healthy but Terraform later shows a task revision change, consult the task-definition ownership decision before applying anything.

## Recovery

Verify the primary task definition matches the recorded baseline and both targets are healthy. If automatic recovery cannot complete, inspect the failed deployment and explicitly select the last known-good task ARN:

```bash
aws ecs update-service --region eu-central-1 --cluster release-platform --service release-platform --task-definition YOUR_RECORDED_GOOD_TASK_ARN
aws ecs wait services-stable --region eu-central-1 --cluster release-platform --services release-platform
```

The waiter alone is insufficient evidence: describe the service again and compare the task ARN, running counts and rollout state. Then verify HTTPS endpoints. Stop and investigate if rollback has no completed baseline, image has been removed, or networking is broken. Do not repeatedly redeploy a known bad candidate.

## Evidence to record

| Field | Actual result |
|---|---|
| Date / region | Not run |
| Baseline commit / image digest / task ARN | Not run |
| Candidate task ARN | Not run |
| Failure detected at UTC | Not run |
| Baseline restored at UTC | Not run |
| Recovery duration | Not measured |
| Pipeline result | Not run |
| Alert received | Not run |
| Follow-up | Run first AWS drill |

Before sharing screenshots, remove account identifiers, email addresses and any unexpected customer data. Never fabricate an incident timeline or claim the drill happened at an employer.
