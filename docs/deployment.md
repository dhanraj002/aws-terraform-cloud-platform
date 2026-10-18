# Bootstrap and deployment

Use a sandbox account. This guide creates billable AWS resources; first review cost-and-cleanup.md. Commands assume the repository root and the default `release-platform` name in `eu-central-1`. If you change either, change the deploy workflow environment values too.

Prerequisites: AWS CLI v2 authenticated through your normal SSO/profile, Terraform 1.10+, Docker, an owned DNS name, and an issued ACM certificate for that name in eu-central-1. Do not paste credentials into files or GitHub variables.

## 1. Bootstrap

```bash
aws sts get-caller-identity
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=infra/bootstrap apply bootstrap.tfplan
terraform -chdir=infra/bootstrap output
```

If the account already has a GitHub OIDC provider, pass its ARN using `existing_oidc_provider_arn` in a local ignored `terraform.tfvars`. AWS allows only one provider for the issuer URL per account. Do not replace an existing shared provider.

Bootstrap initially uses local state. Keep this state secure and backed up; losing it loses management of the shared prerequisites. The state bucket has prevent_destroy and versioning. A team deployment should migrate bootstrap state to a separately managed administrative backend. The application stack below uses S3 locking.

## 2. Publish the initial image

```bash
export AWS_REGION=eu-central-1
ECR_URL=$(terraform -chdir=infra/bootstrap output -raw repository_url)
REGISTRY=${ECR_URL%%/*}
TAG="bootstrap-$(date -u +%Y%m%d%H%M%S)"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker build --platform linux/amd64 -t "$ECR_URL:$TAG" .
docker push "$ECR_URL:$TAG"
DIGEST=$(aws ecr describe-images --region "$AWS_REGION" --repository-name release-platform --image-ids imageTag="$TAG" --query 'imageDetails[0].imageDigest' --output text)
printf '%s@%s\n' "$ECR_URL" "$DIGEST"
```

Use the resulting digest URI for `image_uri`. Immutable ECR tags mean reusing a tag is expected to fail.

## 3. Plan and create the application stack

Copy `infra/backend.hcl.example` to `infra/backend.hcl` and set the bootstrap bucket name. This backend file contains no credentials; do not put any there. Copy `infra/terraform.tfvars.example` to `infra/terraform.tfvars`, replacing the image digest, certificate ARN and alert email.

```bash
terraform -chdir=infra init -backend-config=backend.hcl
terraform -chdir=infra plan -out=lab.tfplan
terraform -chdir=infra show -json lab.tfplan > /tmp/release-platform-plan.json
python3 scripts/check_plan.py /tmp/release-platform-plan.json
terraform -chdir=infra apply lab.tfplan
terraform -chdir=infra output
```

Plan JSON may contain sensitive values; keep it local, delete it after review, and never upload it as a public artifact. The plan tag checker is a manual pre-apply gate; pull-request CI uses mocked plans and does not access an AWS account.

Create a DNS CNAME (or Route 53 alias) from the certificate's hostname to `alb_dns_name`. Verify with `curl --fail https://YOUR_HOSTNAME/readyz`; do not bypass TLS verification or use the ALB DNS name as the certificate hostname. Confirm the SNS email subscription. Activate `Project` as a cost-allocation tag in Billing, allowing AWS processing time before expecting budget attribution.

## 4. Configure GitHub

Create an environment named `lab`. Restrict deployment branches to `main`. Where available, add required reviewers. Set the environment variable `AWS_DEPLOY_ROLE_ARN` to the bootstrap output. This is a role identifier, not a secret key. Protect main against unreviewed workflow changes for collaborative use.

Open Actions → Deploy lab → Run workflow from main. Leave `fail_readiness` false for a normal release. The job runs tests, checks the built container, pushes an immutable image and verifies the exact task revision. Concurrency prevents overlapping runs of this workflow; avoid simultaneous out-of-band deployments.

Before a failure drill, verify one healthy completed deployment exists. Follow runbook.md. GitHub CI passing proves repository checks, not an AWS deployment.
