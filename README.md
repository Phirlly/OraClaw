# OraClaw — OpenClaw on OCI (Always Free Compute) + OCI Generative AI (OpenAI-compatible)

This folder (`stack/`) contains an **OCI Resource Manager compatible Terraform stack** that deploys **OpenClaw Gateway** on an **OCI Always Free** compute instance.

It also deploys a local **OCI → OpenAI-compatible proxy** so OpenClaw can use **OCI Generative AI Inference** models through an OpenAI-style API (`/v1/chat/completions`, `/v1/embeddings`).

## What’s free (and what isn’t)

- **Compute:** This stack is designed to run on OCI **Always Free** ARM compute (Ampere A1 Flex). If you stay within OCI Always Free limits, the VM cost is **$0**.
- **OCI Generative AI:** **Not free.** OCI Generative AI usage is billed according to your OCI pricing for the models you use.

## Quick deploy (OCI Resource Manager)

Automated deployment:
1) Click the **Deploy to Oracle Cloud** button below.
2) In OCI Console, fill in the required values.
3) Click **Apply**.

Deploy button (main branch ZIP):

[![Deploy to Oracle Cloud](https://docs.oracle.com/en-us/iaas/Content/ResourceManager/Images/deploy-to-oracle-cloud.svg)](https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https://github.com/Phirlly/OraClaw/archive/refs/heads/main.zip)

If the button doesn’t work in your environment, use this URL directly:

- https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https://github.com/Phirlly/OraClaw/archive/refs/heads/main.zip

## What gets deployed

Terraform in this stack creates:

- Networking
  - VCN
  - Public subnet
  - Internet Gateway
  - Route tables
  - Network Security Group with inbound **22 (SSH)** and **443 (HTTPS)**
- Compute
  - 1 Oracle Linux instance (default shape: `VM.Standard.A1.Flex`)
  - cloud-init provisioning that installs and configures:
    - **nginx** (terminates HTTPS on-instance with an auto-generated self-signed cert)
    - **OpenClaw Gateway** (local mode, loopback bind)
    - **OCI OpenAI-compatible proxy** (FastAPI + Uvicorn, Instance Principals)

## Entry points (after Apply)

From `stack/outputs.tf` + `stack/schema.yaml`, the primary URLs are:

- Health check:
  - `https://<INSTANCE_PUBLIC_IP>/healthz`
- OpenClaw “login” page:
  - `https://<INSTANCE_PUBLIC_IP>/login`

Note: The TLS certificate is **self-signed** (generated automatically). Your browser will warn; you must proceed/accept.

## Required inputs in Resource Manager

When creating the stack in OCI Resource Manager, you must provide:

- **Tenancy OCID** (`tenancy_ocid`)
- **Region** (`region`)
- **Compartment OCID** (`compartment_ocid`)
- **SSH public key** (`ssh_public_key`)

Compute defaults are set for Always Free, but can be adjusted.

Optional:
- **Override models.json** (`oci_openai_proxy_models_json_override`)
  - This overrides the proxy’s model catalog at `/etc/oci-openai-proxy/models.json`.

## How OCI Generative AI access works (important)

The proxy authenticates to OCI using **Instance Principals**.

That means the instance must be allowed (via dynamic group + policy) to call the Generative AI services in your tenancy/compartment.

If you don’t already have this configured, you will need an IAM policy similar to:

- Allow the instance (dynamic group) to use Generative AI in the target compartment.

(Exact dynamic group + policy setup varies by tenancy standards. If you want, I can add a concrete IAM section once you confirm your preferred policy wording.)

## Verify after deployment

1) In the OCI Console, open the instance details and copy its **Public IP**.

2) Verify nginx health:

```bash
curl -kfsS https://<INSTANCE_PUBLIC_IP>/healthz
```

Expected: HTTP 200 and a small response body.

3) Open the UI:

- `https://<INSTANCE_PUBLIC_IP>/login`

## Troubleshooting

### Deploy button opens but stack fails to Apply

Check the Resource Manager Apply Job logs:
- missing required variables (compartment/tenancy/ssh key)
- Always Free capacity issues for A1 Flex in your AD

### Instance comes up but UI doesn’t load

- Ensure NSG ingress includes **TCP 443** from `0.0.0.0/0`.
- Verify the instance is running and has a public IP.

### Proxy / GenAI issues

If OpenClaw can’t reach models or chat calls fail, likely causes are:
- IAM dynamic group / policy not allowing the instance to call GenAI
- Region endpoint mismatch in models.json (if overridden)

## Destroy / cleanup

From OCI Resource Manager:
- Run a **Destroy** job for the stack to remove resources.

## Repo

- Source: https://github.com/Phirlly/OraClaw

## License / cost disclaimer

This repository provides infrastructure templates and configuration.
You are responsible for:
- any OCI costs incurred (especially **Generative AI usage** and any resources outside Always Free limits)
- securing access to the deployed endpoints

---

### Notes for contributors

This stack uses a cloud-init workflow that downloads runtime assets from this repository.
Key files:
- `stack/cloud-init/nginx-healthz.yaml`
- `stack/cloud-init/assets/oci_openai_proxy_server.py`
- `stack/cloud-init/assets/oci_openai_proxy/`
```