terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
variable "region" { default = "eu-central-1" }
variable "name" { default = "release-platform" }
variable "repository" { default = "dhanraj002/aws-terraform-cloud-platform" }
variable "existing_oidc_provider_arn" {
  type        = string
  default     = null
  description = "Reuse the account's GitHub provider if it already exists."
}
provider "aws" {
  region = var.region
  default_tags { tags = { Project = var.name, Owner = "dhanraj002", Environment = "lab", CostCentre = "portfolio", ManagedBy = "terraform" } }
}
data "aws_caller_identity" "current" {}
resource "aws_s3_bucket" "state" {
  bucket = "${var.name}-state-${data.aws_caller_identity.current.account_id}-${var.region}"
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Sid = "DenyInsecureTransport", Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } }] })
}
resource "aws_ecr_repository" "app" {
  name                 = var.name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
  force_delete = false
}
resource "aws_iam_openid_connect_provider" "github" {
  count          = var.existing_oidc_provider_arn == null ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}
resource "aws_iam_role" "deploy" {
  name = "${var.name}-github-deploy"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "sts:AssumeRoleWithWebIdentity", Principal = { Federated = var.existing_oidc_provider_arn != null ? var.existing_oidc_provider_arn : aws_iam_openid_connect_provider.github[0].arn }, Condition = { StringEquals = {
    "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub" = "repo:${var.repository}:environment:lab"
  } } }] })
}
resource "aws_iam_role_policy" "deploy" {
  role = aws_iam_role.deploy.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:DescribeImages"], Resource = aws_ecr_repository.app.arn },
    { Effect = "Allow", Action = ["ecs:DescribeServices", "ecs:UpdateService"], Resource = "arn:aws:ecs:${var.region}:${data.aws_caller_identity.current.account_id}:service/${var.name}/${var.name}" },
    { Effect = "Allow", Action = ["ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition"], Resource = "*" },
    { Effect = "Allow", Action = ["iam:PassRole"], Resource = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.name}-execution", "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.name}-task"], Condition = { StringEquals = { "iam:PassedToService" = "ecs-tasks.amazonaws.com" } } }
  ] })
}
output "state_bucket" { value = aws_s3_bucket.state.id }
output "repository_url" { value = aws_ecr_repository.app.repository_url }
output "deploy_role_arn" { value = aws_iam_role.deploy.arn }
