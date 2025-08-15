cat > start_monitoring.sh << 'EOF'
#!/bin/bash
# Quick Start Script for Ansible UPS Monitoring

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Ansible UPS Power Quality Monitoring System"
echo "=============================================="

# Check if Ansible is installed
if ! command -v ansible-playbook &> /dev/null; then
    echo "❌ Ansible not found. Please install Ansible first:"
    echo "   sudo apt update && sudo apt install ansible"
    exit 1
fi

# Check if inventory exists
if [ ! -f "inventory/ups_hosts.yml" ]; then
    echo "❌ Inventory file not found: inventory/ups_hosts.yml"
    echo "   Please configure your UPS devices in the inventory file"
    exit 1
fi

# Check if vault file exists
if [ ! -f "group_vars/all/vault.yml" ]; then
    echo "❌ Vault file not found. Creating template..."
    mkdir -p group_vars/all
    ansible-vault create group_vars/all/vault.yml
    echo "✅ Vault file created. Please edit and run again."
    exit 0
fi

echo "📋 Available monitoring options:"
echo "1. Single monitoring snapshot"
echo "2. Continuous monitoring (24 hours)"
echo "3. Continuous monitoring (custom duration)"
echo "4. Test connectivity to UPS devices"

read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo "🔍 Running single UPS monitoring snapshot..."
        ansible-playbook -i inventory/ups_hosts.yml playbooks/ups_monitoring.yml --ask-vault-pass
        ;;
    2)
        echo "🔄 Starting 24-hour continuous monitoring..."
        ansible-playbook -i inventory/ups_hosts.yml playbooks/continuous_monitoring.yml --ask-vault-pass
        ;;
    3)
        read -p "Enter monitoring duration in hours: " duration
        echo "🔄 Starting ${duration}-hour continuous monitoring..."
        ansible-playbook -i inventory/ups_hosts.yml playbooks/continuous_monitoring.yml \
            --ask-vault-pass \
            --extra-vars "monitoring_duration_hours=$duration"
        ;;
    4)
        echo "🔌 Testing UPS device connectivity..."
        ansible -i inventory/ups_hosts.yml ups_devices -m wait_for \
            -a "host={{ ansible_host }} port={{ snmp_port | default(161) }} timeout=5" \
            --ask-vault-pass
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac

echo "✅ Monitoring complete!"
echo "📁 Check the data/ and reports/ directories for results"
EOF

chmod +x start_monitoring.sh
