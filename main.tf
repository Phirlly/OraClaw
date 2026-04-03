resource "random_password" "openclaw_gateway_token" {
  length           = 64
  special          = true
  override_special = "-_.~" # URL-safe-ish, avoids quotes/slashes/spaces
}

locals {
  openclaw_gateway_token_effective = coalesce(
    trimspace(var.openclaw_gateway_token),
    random_password.openclaw_gateway_token.result
  )

  # Render cloud-init template and base64-encode for OCI metadata.user_data
  cloud_init_rendered = templatefile("${path.module}/cloud-init/nginx-healthz.yaml", {
    openclaw_gateway_token                = local.openclaw_gateway_token_effective
    vcn_cidr                              = var.vcn_cidr
    compartment_ocid                      = var.compartment_ocid
    oci_openai_proxy_models_json_override = var.oci_openai_proxy_models_json_override

    # NEW: allow browser WS Origin via LB public URL
    gateway_allowed_origin = "https://${oci_load_balancer_load_balancer.openclaw.ip_address_details[0].ip_address}"
  })

  user_data_b64 = base64encode(local.cloud_init_rendered)

  # RM file upload variables arrive as base64 strings
  lb_tls_public_cert_pem = trimspace(base64decode(var.lb_tls_public_cert_pem_file))
  lb_tls_private_key_pem = trimspace(base64decode(var.lb_tls_private_key_pem_file))
  lb_tls_ca_chain_pem    = trimspace(base64decode(var.lb_tls_ca_chain_pem_file))
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

data "oci_core_images" "oracle_linux" {
  compartment_id           = var.tenancy_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = var.oracle_linux_version
  shape                    = var.compute_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

locals {
  oracle_linux_image_id = data.oci_core_images.oracle_linux.images[0].id
}

resource "oci_core_vcn" "openclaw" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = [var.vcn_cidr]
  display_name   = "openclaw-vcn"
  dns_label      = "openclawvcn"
}

resource "oci_core_internet_gateway" "openclaw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.openclaw.id
  display_name   = "openclaw-igw"
  enabled        = true
}

resource "oci_core_nat_gateway" "openclaw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.openclaw.id
  display_name   = "openclaw-nat"
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.openclaw.id
  display_name   = "openclaw-public-rt"

  route_rules {
    network_entity_id = oci_core_internet_gateway.openclaw.id
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
  }
}

resource "oci_core_route_table" "private" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.openclaw.id
  display_name   = "openclaw-private-rt"

  route_rules {
    network_entity_id = oci_core_nat_gateway.openclaw.id
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
  }
}

resource "oci_core_subnet" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.openclaw.id

  cidr_block = var.public_subnet_cidr

  display_name               = "openclaw-public-subnet"
  dns_label                  = "pub"
  prohibit_public_ip_on_vnic = false

  route_table_id    = oci_core_route_table.public.id
  security_list_ids = [oci_core_vcn.openclaw.default_security_list_id]
}

resource "oci_core_subnet" "private" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.openclaw.id

  cidr_block = var.private_subnet_cidr

  display_name               = "openclaw-private-subnet"
  dns_label                  = "priv"
  prohibit_public_ip_on_vnic = true

  route_table_id    = oci_core_route_table.private.id
  security_list_ids = [oci_core_vcn.openclaw.default_security_list_id]
}

resource "oci_core_network_security_group" "lb" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.openclaw.id
  display_name   = "openclaw-lb-nsg"
}

resource "oci_core_network_security_group_security_rule" "lb_ingress_443" {
  network_security_group_id = oci_core_network_security_group.lb.id

  direction   = "INGRESS"
  protocol    = "6"
  source      = "0.0.0.0/0"
  source_type = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}

resource "oci_core_network_security_group" "instance" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.openclaw.id
  display_name   = "openclaw-instance-nsg"
}

resource "oci_core_network_security_group_security_rule" "lb_egress_8080_to_instance" {
  network_security_group_id = oci_core_network_security_group.lb.id

  direction        = "EGRESS"
  protocol         = "6"
  destination      = oci_core_network_security_group.instance.id
  destination_type = "NETWORK_SECURITY_GROUP"

  tcp_options {
    destination_port_range {
      min = 8080
      max = 8080
    }
  }
}

resource "oci_core_network_security_group_security_rule" "instance_ingress_ssh" {
  network_security_group_id = oci_core_network_security_group.instance.id

  direction   = "INGRESS"
  protocol    = "6"
  source      = "0.0.0.0/0"
  source_type = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_network_security_group_security_rule" "instance_ingress_8080_from_lb" {
  network_security_group_id = oci_core_network_security_group.instance.id

  direction   = "INGRESS"
  protocol    = "6"
  source      = oci_core_network_security_group.lb.id
  source_type = "NETWORK_SECURITY_GROUP"

  tcp_options {
    destination_port_range {
      min = 8080
      max = 8080
    }
  }
}

resource "oci_core_network_security_group_security_rule" "instance_egress_all" {
  network_security_group_id = oci_core_network_security_group.instance.id

  direction        = "EGRESS"
  protocol         = "all"
  destination      = "0.0.0.0/0"
  destination_type = "CIDR_BLOCK"
}

resource "oci_core_instance" "openclaw" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name

  display_name = var.instance_display_name
  shape        = var.compute_shape

  shape_config {
    ocpus         = var.compute_ocpus
    memory_in_gbs = var.compute_memory_gbs
  }

  source_details {
    source_type = "image"
    source_id   = local.oracle_linux_image_id
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    nsg_ids          = [oci_core_network_security_group.instance.id]
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = local.user_data_b64
  }
}

resource "oci_load_balancer_load_balancer" "openclaw" {
  compartment_id = var.compartment_ocid
  display_name   = "openclaw-lb"

  subnet_ids = [oci_core_subnet.public.id]

  shape = "flexible"

  shape_details {
    minimum_bandwidth_in_mbps = 10
    maximum_bandwidth_in_mbps = 10
  }

  network_security_group_ids = [oci_core_network_security_group.lb.id]
  is_private                 = false
}

resource "oci_load_balancer_certificate" "openclaw" {
  load_balancer_id = oci_load_balancer_load_balancer.openclaw.id
  certificate_name = "openclaw-cert"

  public_certificate = local.lb_tls_public_cert_pem
  private_key        = local.lb_tls_private_key_pem

  ca_certificate = local.lb_tls_ca_chain_pem
  passphrase     = var.lb_tls_private_key_passphrase

  lifecycle {
    create_before_destroy = true
  }
}

resource "oci_load_balancer_backend_set" "openclaw" {
  load_balancer_id = oci_load_balancer_load_balancer.openclaw.id
  name             = "openclaw-backendset"
  policy           = "ROUND_ROBIN"

  health_checker {
    protocol    = "HTTP"
    port        = 8080
    url_path    = "/healthz"
    return_code = 200
  }
}

resource "oci_load_balancer_backend" "openclaw" {
  load_balancer_id = oci_load_balancer_load_balancer.openclaw.id
  backendset_name  = oci_load_balancer_backend_set.openclaw.name

  ip_address = oci_core_instance.openclaw.private_ip
  port       = 8080
}

resource "oci_load_balancer_listener" "https" {
  load_balancer_id         = oci_load_balancer_load_balancer.openclaw.id
  name                     = "https-443"
  port                     = 443
  protocol                 = "HTTP"
  default_backend_set_name = oci_load_balancer_backend_set.openclaw.name

  ssl_configuration {
    certificate_name        = oci_load_balancer_certificate.openclaw.certificate_name
    protocols               = ["TLSv1.2"]
    verify_peer_certificate = false
  }
}
