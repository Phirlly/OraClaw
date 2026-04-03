output "vcn_id" {
  description = "VCN OCID"
  value       = oci_core_vcn.openclaw.id
}

output "public_subnet_id" {
  description = "Public subnet OCID"
  value       = oci_core_subnet.public.id
}

output "instance_id" {
  description = "Compute instance OCID"
  value       = oci_core_instance.openclaw.id
}

output "instance_public_ip" {
  description = "Compute instance public IP"
  value       = oci_core_instance.openclaw.public_ip
}

output "instance_private_ip" {
  description = "Compute instance private IP"
  value       = oci_core_instance.openclaw.private_ip
}

output "instance_https_url" {
  description = "Public HTTPS URL (self-signed cert; use -k with curl)"
  value       = "https://${oci_core_instance.openclaw.public_ip}/"
}
