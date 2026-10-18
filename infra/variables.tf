variable "region" { default = "eu-central-1" }
variable "name" { default = "release-platform" }
variable "owner" { default = "dhanraj002" }
variable "cost_centre" { default = "portfolio" }
variable "certificate_arn" {
  type        = string
  description = "Issued ACM certificate in the selected region; attach your own DNS name to the ALB."
}
variable "image_uri" {
  type        = string
  description = "Initial ECR image pinned by sha256 digest. Subsequent releases are owned by the deployment workflow."
  validation {
    condition     = can(regex("@sha256:[a-f0-9]{64}$", var.image_uri))
    error_message = "Supply an immutable image digest, not a tag."
  }
}
variable "alert_email" {
  type        = string
  description = "SNS subscription must be confirmed by its recipient."
}
variable "monthly_budget_usd" {
  type    = number
  default = 50
  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "Budget must be positive."
  }
}
