# Design decisions

## ECS Fargate for this workload

This service needs a container scheduler and a load balancer. It has no Kubernetes API dependency, custom controller or multi-cluster requirement. Fargate keeps the exercise focused on AWS networking, IAM, Terraform and release operations. EKS would add a control plane and cluster operations without solving a current requirement.

## One NAT gateway is a deliberate lab compromise

Tasks are placed in two private subnets. A single NAT gateway reduces fixed costs, but its availability zone is an outbound dependency for both subnets. This is not a claim of full zone-failure resilience. Existing tasks may continue serving while replacements cannot pull images or publish logs. For a production design, compare per-zone NAT against VPC endpoints and validate failure behavior.

## Infrastructure and application releases have different owners

Terraform owns the service configuration and the initial task definition. GitHub Actions owns subsequent task-definition revisions. The service ignores only `task_definition`; it still tracks network settings, capacity and health checks. This avoids Terraform silently restoring the bootstrap image after a release.

Changing task resources, environment variables, roles or logging in Terraform does not automatically roll the live service because of that ignore rule. Review the newly registered Terraform task revision, then explicitly update the ECS service to it in a maintenance release before using the image-only workflow again. Do not edit an ignored task definition and assume production changed.

## Baseline and eventual consistency

A release first requires a completed, stable deployment with at least one running task. If an operator is already changing the service, the script stops before registering or updating a task. This is a preflight check, not an atomic distributed lock: GitHub concurrency covers workflow runs, while operators must still coordinate external changes.

After UpdateService, the script allows up to 60 seconds for the candidate to appear in DescribeServices. Once observed, disappearance is treated as failure. AWS CLI calls have a 60-second process timeout; workflow execution is also bounded.

## Rollback is not deployment success

The circuit breaker can restore the last completed deployment. A simple services-stable waiter can therefore succeed even when the proposed release failed. The deployment script also checks the expected task ARN, rollout state, desired/running counts and remaining deployments. Its tests include a healthy service running the old revision.

Rollback requires a previous completed deployment. The first-ever deployment has no recovery target. Investigate bootstrap failures directly.

## Trust and access

The GitHub role trusts exactly `repo:dhanraj002/aws-terraform-cloud-platform:environment:lab` with the STS audience. The `lab` environment must restrict deployment branches to `main`; the workflow also checks the branch. AWS cannot infer that branch restriction from this environment-based subject alone.

ECR access is scoped to one repository; ECS service updates are scoped to one service. `iam:PassRole` is restricted to the execution/task roles and the ECS tasks service. ECR authentication and ECS task-definition registration/description use wildcard resources because of their API authorization model. This role does not run Terraform or change IAM policies. Task registration is still a sensitive permission: protect the workflow and the `lab` environment.

The application role has no permissions. The execution role pulls from one ECR repository and writes to one log group. No static AWS credentials are stored in GitHub.

## Tagging and governance

Required tags are applied through the AWS provider. The plan checker validates an explicit set of customer-managed taggable resources, including resources in child modules. It intentionally does not create an organization-wide SCP requiring tags on every service operation. Managed services can create resources through service-linked roles or APIs with different tagging behavior. Test governance in a sandbox and document narrow service exceptions rather than relaxing the whole account.

Activate the Project cost-allocation tag in Billing before relying on the tag-filtered budget. The budget is an alert, not a spending cap.

## Scope limits

The Python HTTP server is a release probe, not a production application server. There is no database, authentication, user data, cross-region recovery or tested availability SLO. HTTPS terminates at the ALB; the ALB-to-task hop uses HTTP inside the VPC. Request logs omit client IPs, query strings and headers. EU region selection alone does not establish GDPR compliance.

Base-image tags can change at rebuild time. Deployed images are pinned by digest; the base image is maintained through Dependabot. A stricter supply-chain setup would pin the base digest and gate updates on a vulnerability policy. ECR scan-on-push is configured but is not presently a blocking release gate.

## References

- [AWS: GitHub OIDC trust](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html)
- [AWS: ECS deployment circuit breaker](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html)
- [Terraform: S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3)
