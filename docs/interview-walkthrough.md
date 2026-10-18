# Explaining the project

Use this as a demonstration outline, not a script to memorize.

1. Start with the release failure problem. Show the test where a healthy old revision must still fail the new release.
2. Trace client → ALB → private Fargate task. Explain why only the ALB security group can reach port 8080.
3. Separate the deployment role, execution role and application task role. Explain why the application does not need AWS permissions.
4. Explain why environment-bound OIDC needs GitHub branch restrictions as well as an exact subject in AWS.
5. Show a real failure drill when available. Separate expected behavior from observed results.
6. Explain the single-NAT compromise, cost risks and cleanup. Name what would change for a production service.
7. Explain the Terraform task-definition ownership boundary and how a task configuration change is promoted.

Possible portfolio bullet, once you have reviewed and can explain the code:

“Developed an AWS/Terraform portfolio lab with private ECS Fargate tasks, HTTPS load balancing, GitHub OIDC delivery and automated detection of failed releases that roll back to a healthy previous revision.”

Do not add availability percentages, cost savings or recovery-time improvements without measurements. Do not present the lab as employment experience. Add a measured recovery result only after the AWS drill.
