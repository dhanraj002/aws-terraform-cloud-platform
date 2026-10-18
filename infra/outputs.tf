output "alb_dns_name" { value = module.service.alb_dns_name }
output "cluster_name" { value = module.service.cluster_name }
output "service_name" { value = module.service.service_name }
output "task_execution_role_arn" { value = module.service.execution_role_arn }
output "task_role_arn" { value = module.service.task_role_arn }
