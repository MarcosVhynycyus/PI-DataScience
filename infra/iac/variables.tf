
variable "vm_macs" {
  description = "MACs das VMs devops-1 e devops-2"
  type        = list(string)
  default     = null

  validation {
    condition     = var.vm_macs == null ? true : length(var.vm_macs) == 2
    error_message = "Informe exatamente dois MACs."
  }
}

variable "ssh_key_path" {
  description = "Caminho da chave SSH privada, sem a extensão .pub"
  type        = string
  default     = "~/.ssh/devops_lab"
}
