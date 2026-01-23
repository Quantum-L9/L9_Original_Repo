# =============================================================================
# L9 Infrastructure - Terraform
# 
# Provisions a VPS with all necessary resources.
# Supports: DigitalOcean, Hetzner, AWS EC2
#
# Usage:
#   cd scripts/infra/terraform
#   terraform init
#   terraform plan
#   terraform apply
#
# GOVERNANCE: IGOR_ONLY
# =============================================================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    # Uncomment the provider you're using
    
    # digitalocean = {
    #   source  = "digitalocean/digitalocean"
    #   version = "~> 2.0"
    # }
    
    hetzner = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
    
    # aws = {
    #   source  = "hashicorp/aws"
    #   version = "~> 5.0"
    # }
  }
}

# =============================================================================
# VARIABLES
# =============================================================================

variable "server_name" {
  description = "Name of the server"
  type        = string
  default     = "l9-vps"
}

variable "server_type" {
  description = "Server size/type"
  type        = string
  default     = "cx21"  # Hetzner: 2 vCPU, 4GB RAM, 40GB SSD (~€5/mo)
  # default   = "s-2vcpu-4gb"  # DigitalOcean: ~$24/mo
  # default   = "t3.medium"    # AWS: ~$30/mo
}

variable "region" {
  description = "Datacenter region"
  type        = string
  default     = "nbg1"  # Hetzner Nuremberg
  # default   = "nyc1"  # DigitalOcean NYC
  # default   = "us-east-1"  # AWS
}

variable "ssh_key_name" {
  description = "Name of SSH key in cloud provider"
  type        = string
  default     = "Hetzner-L9"
}

variable "domain" {
  description = "Domain name for the server"
  type        = string
  default     = ""
}

# =============================================================================
# HETZNER CLOUD (Recommended - Best price/performance)
# =============================================================================

provider "hcloud" {
  # Set HCLOUD_TOKEN environment variable
  # export HCLOUD_TOKEN="your-api-token"
}

# Get SSH key
data "hcloud_ssh_key" "default" {
  name = var.ssh_key_name
}

# Create server
resource "hcloud_server" "l9" {
  name        = var.server_name
  server_type = var.server_type
  location    = var.region
  image       = "ubuntu-22.04"
  ssh_keys    = [data.hcloud_ssh_key.default.id]
  
  labels = {
    project = "l9"
    env     = "production"
  }
  
  # Bootstrap script - runs on first boot
  user_data = <<-EOF
    #!/bin/bash
    
    # Update system
    apt-get update && apt-get upgrade -y
    
    # Install essentials
    apt-get install -y curl git unzip
    
    # Create admin user
    useradd -m -s /bin/bash admin
    usermod -aG sudo admin
    echo "admin ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/admin
    
    # Copy SSH keys to admin
    mkdir -p /home/admin/.ssh
    cp /root/.ssh/authorized_keys /home/admin/.ssh/
    chown -R admin:admin /home/admin/.ssh
    chmod 700 /home/admin/.ssh
    chmod 600 /home/admin/.ssh/authorized_keys
    
    # Install Docker
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker admin
    
    # Signal completion
    touch /tmp/bootstrap-complete
  EOF
}

# Firewall
resource "hcloud_firewall" "l9" {
  name = "${var.server_name}-fw"
  
  # SSH
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  
  # HTTP
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  
  # HTTPS
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  
  # Allow all outbound
  rule {
    direction = "out"
    protocol  = "tcp"
    port      = "any"
    destination_ips = ["0.0.0.0/0", "::/0"]
  }
  
  rule {
    direction = "out"
    protocol  = "udp"
    port      = "any"
    destination_ips = ["0.0.0.0/0", "::/0"]
  }
}

# Attach firewall to server
resource "hcloud_firewall_attachment" "l9" {
  firewall_id = hcloud_firewall.l9.id
  server_ids  = [hcloud_server.l9.id]
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "server_ip" {
  description = "Public IP of the L9 server"
  value       = hcloud_server.l9.ipv4_address
}

output "server_status" {
  description = "Server status"
  value       = hcloud_server.l9.status
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh admin@${hcloud_server.l9.ipv4_address}"
}

output "next_steps" {
  description = "What to do next"
  value       = <<-EOF
    
    Server provisioned! Next steps:
    
    1. Wait for cloud-init to complete (~2 min):
       ssh admin@${hcloud_server.l9.ipv4_address} "ls /tmp/bootstrap-complete"
    
    2. Run the full bootstrap script:
       ssh admin@${hcloud_server.l9.ipv4_address}
       curl -sL https://raw.githubusercontent.com/YOUR_REPO/l9/main/scripts/infra/bootstrap_vps.sh | sudo bash
    
    3. Or manually:
       git clone YOUR_REPO /opt/l9
       cd /opt/l9
       ./scripts/infra/bootstrap_vps.sh
    
  EOF
}

# =============================================================================
# DIGITALOCEAN (Alternative)
# =============================================================================
# Uncomment this block if using DigitalOcean instead of Hetzner

# provider "digitalocean" {
#   # Set DIGITALOCEAN_TOKEN environment variable
# }
# 
# data "digitalocean_ssh_key" "default" {
#   name = var.ssh_key_name
# }
# 
# resource "digitalocean_droplet" "l9" {
#   name     = var.server_name
#   size     = var.server_type
#   region   = var.region
#   image    = "ubuntu-22-04-x64"
#   ssh_keys = [data.digitalocean_ssh_key.default.id]
#   
#   user_data = <<-EOF
#     #!/bin/bash
#     # Same bootstrap as above
#   EOF
# }
# 
# resource "digitalocean_firewall" "l9" {
#   name        = "${var.server_name}-fw"
#   droplet_ids = [digitalocean_droplet.l9.id]
#   
#   inbound_rule {
#     protocol         = "tcp"
#     port_range       = "22"
#     source_addresses = ["0.0.0.0/0", "::/0"]
#   }
#   
#   inbound_rule {
#     protocol         = "tcp"
#     port_range       = "80"
#     source_addresses = ["0.0.0.0/0", "::/0"]
#   }
#   
#   inbound_rule {
#     protocol         = "tcp"
#     port_range       = "443"
#     source_addresses = ["0.0.0.0/0", "::/0"]
#   }
#   
#   outbound_rule {
#     protocol              = "tcp"
#     port_range            = "all"
#     destination_addresses = ["0.0.0.0/0", "::/0"]
#   }
# }
