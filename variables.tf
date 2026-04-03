variable "tenancy_ocid" {
  type        = string
  description = "OCI tenancy OCID (required for availability domain + platform image listing)."
}

variable "region" {
  type        = string
  description = "OCI region identifier, e.g. us-ashburn-1."
}

variable "compartment_ocid" {
  type        = string
  description = "Compartment OCID where resources will be created."
}

# =====================
# Network CIDRs
# =====================

variable "vcn_cidr" {
  type        = string
  description = "VCN CIDR block."
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  type        = string
  description = "Public subnet CIDR block."
  default     = "10.0.1.0/24"
}

variable "private_subnet_cidr" {
  type        = string
  description = "Private subnet CIDR block."
  default     = "10.0.2.0/24"
}

# =====================
# SSH key (Resource Manager SSH key control)
# =====================

variable "ssh_public_key" {
  type        = string
  description = "Public SSH key(s) for instance login. Resource Manager SSH key control can provide one or more keys; they will be passed as a newline-delimited string."
}

# =====================
# TLS inputs (Resource Manager file upload)
# =====================

variable "lb_tls_public_cert_pem_file" {
  type        = string
  description = "(RM file upload) PEM-encoded leaf/server certificate. RM stores this as base64; Terraform base64decode()."
  sensitive   = true
}

variable "lb_tls_private_key_pem_file" {
  type        = string
  description = "(RM file upload) PEM-encoded private key. RM stores this as base64; Terraform base64decode()."
  sensitive   = true
}

variable "lb_tls_ca_chain_pem_file" {
  type        = string
  description = "(Optional, RM file upload) PEM-encoded CA/intermediate chain. RM stores this as base64; Terraform base64decode()."
  sensitive   = true
  default     = ""
}

variable "lb_tls_private_key_passphrase" {
  type        = string
  description = "(Optional) Passphrase for encrypted private keys. Leave empty if key is unencrypted."
  sensitive   = true
  default     = ""
}

# =====================
# OpenClaw (token override or auto-generate)
# =====================

variable "openclaw_gateway_token" {
  type        = string
  description = "Optional override gateway token. If empty, Terraform will auto-generate a random token (stored in state)."
  sensitive   = true
  default     = ""
}

variable "oci_openai_proxy_models_json_override" {
  type        = string
  description = "Optional override for /etc/oci-openai-proxy/models.json."
  sensitive   = true
  default     = ""
}

# =====================
# Compute (Oracle Linux on E5 Flex)
# =====================

variable "instance_display_name" {
  type        = string
  description = "Compute instance display name."
  default     = "openclaw"
}

variable "oracle_linux_version" {
  type        = string
  description = "Oracle Linux major version to deploy (used for image lookup), e.g. '9'."
  default     = "9"
}

variable "compute_shape" {
  type        = string
  description = "Compute shape for the OpenClaw instance."
  default     = "VM.Standard.E5.Flex"
}

variable "compute_ocpus" {
  type        = number
  description = "Number of OCPUs for the Flex shape."
  default     = 2
}

variable "compute_memory_gbs" {
  type        = number
  description = "Memory (GB) for the Flex shape."
  default     = 16
}
