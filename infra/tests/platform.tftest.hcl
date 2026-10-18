mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = { names = ["eu-central-1a", "eu-central-1b"] }
  }
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
}
variables {
  certificate_arn = "arn:aws:acm:eu-central-1:123456789012:certificate/00000000-0000-0000-0000-000000000000"
  image_uri       = "123456789012.dkr.ecr.eu-central-1.amazonaws.com/release-platform@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  alert_email     = "test@example.com"
}
run "plan_platform" {
  command = plan
  assert {
    condition     = output.cluster_name == "release-platform"
    error_message = "Cluster name must remain stable for the deployment workflow."
  }
}
run "reject_mutable_images" {
  command = plan
  variables { image_uri = "example:latest" }
  expect_failures = [var.image_uri]
}
