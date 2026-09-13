output "s3_data_lake_bucket_name" {
  description = "Optional S3 data-lake bucket name; null when disabled."
  value       = var.enable_s3_data_lake ? aws_s3_bucket.data_lake[0].bucket : null
}

output "s3_data_lake_bucket_arn" {
  description = "Optional S3 data-lake bucket ARN; null when disabled."
  value       = var.enable_s3_data_lake ? aws_s3_bucket.data_lake[0].arn : null
}

output "s3_data_lake_enabled" {
  description = "Whether optional S3 infrastructure is enabled."
  value       = var.enable_s3_data_lake
}
