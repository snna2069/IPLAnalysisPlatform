locals {
  bucket_name = trimspace(var.s3_bucket_name)
}

resource "aws_s3_bucket" "data_lake" {
  count  = var.enable_s3_data_lake ? 1 : 0
  bucket = local.bucket_name

  force_destroy = var.s3_force_destroy
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  count  = var.enable_s3_data_lake ? 1 : 0
  bucket = aws_s3_bucket.data_lake[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data_lake" {
  count  = var.enable_s3_data_lake ? 1 : 0
  bucket = aws_s3_bucket.data_lake[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  count  = var.enable_s3_data_lake ? 1 : 0
  bucket = aws_s3_bucket.data_lake[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  count  = var.enable_s3_data_lake ? 1 : 0
  bucket = aws_s3_bucket.data_lake[0].id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
