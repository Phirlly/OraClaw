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

output "lb_id" {
  description = "Load balancer OCID"
  value       = oci_load_balancer_load_balancer.openclaw.id
}

output "lb_public_ip" {
  description = "Load balancer public IP"
  value       = oci_load_balancer_load_balancer.openclaw.ip_address_details[0].ip_address
}

output "lb_https_url" {
  description = "Public HTTPS URL"
  value       = "https://${oci_load_balancer_load_balancer.openclaw.ip_address_details[0].ip_address}/"
}

output "backend_health_check" {
  description = "Backend health check path"
  value       = "http://${oci_core_instance.openclaw.private_ip}:8080/healthz"
}
