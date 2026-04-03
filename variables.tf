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
# Compute (Oracle Linux on Always Free A1 Flex by default)
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
  description = "Compute shape for the OpenClaw instance. Default is Always Free Ampere."
  default     = "VM.Standard.A1.Flex"
}

variable "compute_ocpus" {
  type        = number
  description = "Number of OCPUs for the Flex shape. Default targets Always Free."
  default     = 1
}

variable "compute_memory_gbs" {
  type        = number
  description = "Memory (GB) for the Flex shape. Default targets Always Free."
  default     = 6
}
