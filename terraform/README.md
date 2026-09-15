# Phase 8 Terraform Infrastructure

This directory demonstrates Infrastructure as Code for the IPL platform without requiring cloud resources for local development.

## Default behavior

The default configuration sets `enable_s3_data_lake = false`, so `terraform plan` proposes no resources. The application continues to use the local filesystem data lake under `data/`. No AWS credentials are required when the optional resource is disabled because the provider is not used to create infrastructure.

## Optional S3 data lake

The only managed resource in this phase is an optional private S3 bucket and its safety configuration:

- S3 bucket with a caller-provided globally unique name
- Public access blocked
- Versioning enabled for raw-file recovery
- AES256 server-side encryption
- Incomplete multipart uploads expired after seven days

S3 is disabled by default and should remain disabled for free-tier/local development. Enabling it can incur storage, request, and data-transfer charges. Use a disposable development bucket, keep `s3_force_destroy = false`, and destroy the bucket only after its contents are handled. Do not enable this module in automated CI unless AWS cost controls and credentials are configured.

## Credentials and state

Terraform does not contain credentials. Configure AWS authentication using the standard AWS credential chain, AWS CLI profiles, environment variables, or an approved CI identity. Never put access keys in `terraform.tfvars` or source files.

For a team deployment, configure a remote encrypted Terraform backend with locking as a future infrastructure improvement. Local state is ignored by Git in the meantime.

## Usage

From the repository root:

```powershell
Copy-Item terraform/terraform.tfvars.example terraform/terraform.tfvars
Set-Location terraform
terraform init
terraform fmt -check
terraform validate
terraform plan -var-file=terraform.tfvars
```

To opt into S3, set `enable_s3_data_lake = true` and provide a globally unique `s3_bucket_name` in the untracked `terraform.tfvars`, then run `terraform plan` again. Review the plan before any apply. Applying or destroying infrastructure is intentionally not part of the default workflow.

Useful checks:

```powershell
terraform fmt
terraform validate
terraform plan -var-file=terraform.tfvars
terraform output
```

## Future extension points

Additional modules can later add an IAM reporting role, remote state, networking, or cloud orchestration. Keep those concerns in separate modules and preserve the current `enable_*` pattern so local development never requires cloud provisioning.
