locals {
  tags = {
    Project     = var.name
    Owner       = var.owner
    Environment = "lab"
    CostCentre  = var.cost_centre
    ManagedBy   = "terraform"
  }
}
module "network" {
  source = "./modules/network"
  name   = var.name
}
module "service" {
  source          = "./modules/service"
  name            = var.name
  region          = var.region
  vpc_id          = module.network.vpc_id
  public_subnets  = module.network.public_subnets
  private_subnets = module.network.private_subnets
  certificate_arn = var.certificate_arn
  image_uri       = var.image_uri
  alert_email     = var.alert_email
  depends_on      = [module.network]
}
resource "aws_budgets_budget" "lab" {
  name         = "${var.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  cost_filter {
    name   = "TagKeyValue"
    values = [format("user:Project$%s", var.name)]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}
