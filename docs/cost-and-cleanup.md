# Cost and cleanup

The local application, unit tests and mocked Terraform tests need no AWS resources. The AWS lab is not free-tier-only.

The main standing costs are NAT gateway hours, ALB hours, public IPv4 addresses and two Fargate tasks (each 0.25 vCPU / 0.5 GiB). Traffic adds NAT processing, load-balancer capacity and transfer charges. Container Insights, logs, alarms, ECR and S3 add charges too. A quiet application can still incur substantial fixed costs.

Estimate a short lab session and a full month separately with the [AWS Pricing Calculator](https://calculator.aws/). Include Frankfurt region, 2 tasks, 1 NAT gateway, 1 ALB, their public IPv4 addresses, and expected logs/traffic. No fixed monthly price is claimed here.

The default USD 50 budget is an alert threshold, not a forecast, spending limit, or automatic shutdown. Its tag filter requires the Project cost-allocation tag to be activated. A delayed budget notification does not stop charges.

## End a lab session

```bash
terraform -chdir=infra plan -destroy -out=destroy.tfplan
terraform -chdir=infra apply destroy.tfplan
```

Review the destroy plan first. This removes the application stack including its logs, dashboard and alerts; export needed evidence before teardown. Verify in the console that NAT gateway, EIP, ALB and ECS service are gone, and check billing later for residual charges.

The bootstrap stack remains: state bucket/version history, image repository and deployment role. Storage can still cost money. ECR has force_delete disabled; retained release images must be reviewed before deletion. Do not enable an aggressive lifecycle rule that deletes an image still needed by running tasks or rollback.

The state bucket has prevent_destroy. Do not remove that protection merely to make cleanup green. Archive state securely, verify no stack depends on it, then use a separately reviewed retirement procedure. Do not delete a shared GitHub OIDC provider used by other repositories.
