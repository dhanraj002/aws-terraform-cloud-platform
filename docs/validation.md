# Validation record

Initial local validation: 18 October 2026.

| Check | Result |
|---|---|
| Python application, release checks and tag-policy tests | 14 passed |
| Terraform format | Passed |
| Application Terraform validation | Passed |
| Bootstrap Terraform validation | Passed |
| Mocked AWS Terraform plans | 2 passed, including rejection of mutable image tags |
| AWS provider lockfiles | Version 6.69.1; committed for both roots |
| GitHub Actions references | Pinned to resolved official action commit SHAs |
| Local Docker execution | Not run: Docker daemon unavailable |
| GitHub CI container build and smoke test | See live CI run linked from README |
| Live AWS deployment / rollback drill | Not run |

Local Python version was 3.14.7 and Terraform was 1.16.1. CI uses Python 3.13 and Terraform 1.16.1. Terraform tests use a mocked AWS provider; they do not establish real IAM authorization or network connectivity.

No AWS resources were provisioned during this build. Certificate setup, live IAM authorization, networking, SNS delivery, budget attribution and recovery timings require a sandbox deployment. The runbook contains an unfilled evidence table for that first drill.
