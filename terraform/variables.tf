variable "aws_region" {
  description = "AWS region used only when optional S3 infrastructure is enabled."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name applied to provisioned resources."
  type        = string
  default     = "ipl-analytics"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "dev"
}

variable "enable_s3_data_lake" {
  description = "Whether to provision the optional S3 data-lake bucket. Keep false for local development."
  type        = bool
  default     = false
}

variable "s3_bucket_name" {
  description = "Globally unique S3 bucket name. Required only when enable_s3_data_lake is true."
  type        = string
  default     = ""

  validation {
    condition     = !var.enable_s3_data_lake || length(trimspace(var.s3_bucket_name)) > 0
    error_message = "s3_bucket_name must be set when enable_s3_data_lake is true."
  }
}

variable "s3_force_destroy" {
  description = "Allow Terraform to delete objects when destroying the optional bucket. Keep false outside disposable experiments."
  type        = bool
  default     = false
}
