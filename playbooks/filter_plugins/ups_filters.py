#!/usr/bin/env python3
"""
Ansible Filter Plugin for UPS Power Quality Analysis
Analyzes SNMP data and detects power quality issues
"""

import re
import json
from datetime import datetime

class FilterModule(object):
    """Custom filters for UPS monitoring and power quality analysis"""
    
    def filters(self):
        return {
            'power_quality_filter': self.analyze_power_quality,
            'parse_snmp_value': self.parse_snmp_value,
            'ups_state_decode': self.decode_ups_state,
            'voltage_analysis': self.analyze_voltage,
            'load_analysis': self.analyze_load,
            'format_ups_data': self.format_monitoring_data
        }
    
    def analyze_power_quality(self, monitoring_data):
        """Analyze UPS data for power quality issues"""
        issues = []
        alerts = []
        analysis = {}
        
        try:
            snmp_data = monitoring_data.get('snmp_data', {})
            
            # Parse SNMP values
            parsed_data = {}
            for key, raw_value in snmp_data.items():
                parsed_data[key] = self.parse_snmp_value(raw_value)
            
            # Analyze input voltage
            input_voltage = self.get_numeric_value(parsed_data.get('input_voltage'))
            if input_voltage:
                if input_voltage < 200:
                    issues.append(f"UNDERVOLTAGE: {input_voltage}V")
                    alerts.append("LOW_VOLTAGE")
                elif input_voltage > 250:
                    issues.append(f"OVERVOLTAGE: {input_voltage}V")
                    alerts.append("HIGH_VOLTAGE")
            
            # Analyze UPS state for compensation
            ups_state = self.get_numeric_value(parsed_data.get('ups_basic_state'))
            state_info = self.decode_ups_state(ups_state)
            
            if ups_state == 4:  # Smart Boost
                issues.append("VOLTAGE_COMPENSATION: Smart Boost (Low Voltage Compensation)")
                alerts.append("COMPENSATION_ACTIVE")
            elif ups_state == 12:  # Smart Trim
                issues.append("VOLTAGE_COMPENSATION: Smart Trim (High Voltage Compensation)")
                alerts.append("COMPENSATION_ACTIVE")
            elif ups_state == 3:  # On Battery
                issues.append("POWER_FAILURE: Running on Battery")
                alerts.append("ON_BATTERY")
            
            # Analyze load
            output_load = self.get_numeric_value(parsed_data.get('output_load'))
            capacity_watts = monitoring_data.get('capacity_watts', 1000)
            
            if output_load:
                if output_load > 80:
                    issues.append(f"HIGH_LOAD: {output_load}% ({capacity_watts}W capacity)")
                    alerts.append("HIGH_LOAD")
                elif output_load > 60:
                    issues.append(f"MODERATE_LOAD: {output_load}%")
                    alerts.append("MODERATE_LOAD")
            
            # Analyze temperature
            battery_temp = self.get_numeric_value(parsed_data.get('battery_temperature'))
            if battery_temp and battery_temp > 35:
                issues.append(f"HIGH_TEMPERATURE: {battery_temp}°C")
                alerts.append("HIGH_TEMP")
            
            # Analyze frequency
            input_freq = self.get_numeric_value(parsed_data.get('input_frequency'))
            if input_freq:
                if input_freq < 49 or input_freq > 51:
                    issues.append(f"FREQUENCY_DEVIATION: {input_freq}Hz")
                    alerts.append("FREQUENCY_ISSUE")
            
            # Create analysis summary
            analysis = {
                'power_quality_issues': issues,
                'alerts': alerts,
                'parsed_snmp_data': parsed_data,
                'ups_state_description': state_info,
                'analysis_timestamp': datetime.now().isoformat(),
                'quality_score': self.calculate_quality_score(issues),
                'recommendations': self.generate_recommendations(issues, monitoring_data)
            }
            
        except Exception as e:
            analysis = {
                'power_quality_issues': [f"ANALYSIS_ERROR: {str(e)}"],
                'alerts': ['ANALYSIS_FAILED'],
                'error': str(e)
            }
        
        return analysis
    
    def parse_snmp_value(self, raw_value):
        """Parse SNMP command output to extract value"""
        if not raw_value or isinstance(raw_value, (int, float)):
            return raw_value
        
        # Parse snmpget output format: OID = TYPE: VALUE
        if '=' in str(raw_value):
            try:
                parts = str(raw_value).split('=', 1)
                if len(parts) > 1:
                    value_part = parts[1].strip()
                    
                    # Remove type indicators like "INTEGER:", "STRING:", etc.
                    type_patterns = [
                        r'^INTEGER:\s*',
                        r'^STRING:\s*',
                        r'^Gauge32:\s*',
                        r'^Counter32:\s*',
                        r'^Opaque:\s*',
                        r'^OID:\s*'
                    ]
                    
                    for pattern in type_patterns:
                        value_part = re.sub(pattern, '', value_part)
                    
                    # Remove quotes
                    value_part = value_part.strip('"\'')
                    
                    # Try to convert to number
                    try:
                        if '.' in value_part:
                            return float(value_part)
                        return int(value_part)
                    except ValueError:
                        return value_part
            except:
                pass
        
        return str(raw_value).strip()
    
    def get_numeric_value(self, value):
        """Extract numeric value from parsed SNMP data"""
        if value is None:
            return None
        
        try:
            if isinstance(value, (int, float)):
                return float(value)
            
            # Extract numbers from string
            numeric_match = re.search(r'[-+]?\d*\.?\d+', str(value))
            if numeric_match:
                return float(numeric_match.group())
        except:
            pass
        
        return None
    
    def decode_ups_state(self, state_code):
        """Decode UPS basic state code"""
        state_map = {
            1: 'Unknown',
            2: 'Normal Operation',
            3: 'On Battery',
            4: 'Smart Boost (Low Voltage Compensation)',
            5: 'Timed Sleeping',
            6: 'Software Bypass',
            7: 'Off',
            8: 'Rebooting',
            9: 'Switched Bypass',
            10: 'Hardware Failure Bypass',
            11: 'Sleeping Until Power Restored',
            12: 'Smart Trim (High Voltage Compensation)'
        }
        
        state_num = self.get_numeric_value(state_code)
        if state_num is not None:
            return state_map.get(int(state_num), f'Unknown State ({state_num})')
        
        return 'State Unknown'
    
    def analyze_voltage(self, voltage_data):
        """Analyze voltage stability and quality"""
        analysis = {
            'status': 'normal',
            'issues': [],
            'recommendations': []
        }
        
        input_voltage = self.get_numeric_value(voltage_data.get('input_voltage'))
        output_voltage = self.get_numeric_value(voltage_data.get('output_voltage'))
        
        if input_voltage:
            if input_voltage < 200:
                analysis['status'] = 'critical'
                analysis['issues'].append('Input voltage critically low')
                analysis['recommendations'].append('Check utility power quality')
            elif input_voltage > 250:
                analysis['status'] = 'critical'
                analysis['issues'].append('Input voltage critically high')
                analysis['recommendations'].append('Check for overvoltage conditions')
        
        if input_voltage and output_voltage:
            voltage_diff = abs(input_voltage - output_voltage)
            if voltage_diff > 10:
                analysis['issues'].append(f'Large voltage difference: {voltage_diff}V')
        
        return analysis
    
    def analyze_load(self, load_data, capacity_info):
        """Analyze load patterns and capacity utilization"""
        analysis = {
            'status': 'normal',
            'utilization': 'low',
            'recommendations': []
        }
        
        load_percent = self.get_numeric_value(load_data.get('output_load'))
        capacity_watts = capacity_info.get('capacity_watts', 1000)
        
        if load_percent:
            if load_percent > 80:
                analysis['status'] = 'critical'
                analysis['utilization'] = 'critical'
                analysis['recommendations'].append('Consider load balancing or additional UPS capacity')
            elif load_percent > 60:
                analysis['status'] = 'warning'
                analysis['utilization'] = 'high'
                analysis['recommendations'].append('Monitor load trends for capacity planning')
            elif load_percent < 20:
                analysis['utilization'] = 'low'
                analysis['recommendations'].append('UPS may be oversized for current load')
        
        return analysis
    
    def calculate_quality_score(self, issues):
        """Calculate power quality score based on issues"""
        if not issues:
            return 100.0
        
        score = 100.0
        for issue in issues:
            if 'CRITICAL' in issue or 'POWER_FAILURE' in issue:
                score -= 30
            elif 'HIGH' in issue or 'COMPENSATION' in issue:
                score -= 15
            elif 'MODERATE' in issue or 'WARNING' in issue:
                score -= 10
            else:
                score -= 5
        
        return max(0.0, score)
    
    def generate_recommendations(self, issues, monitoring_data):
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        if any('VOLTAGE_COMPENSATION' in issue for issue in issues):
            recommendations.append('Investigate utility power quality - frequent compensation may indicate upstream issues')
            recommendations.append('Consider installing power conditioning equipment')
        
        if any('HIGH_LOAD' in issue for issue in issues):
            recommendations.append('Plan for load redistribution or additional UPS capacity')
            recommendations.append('Review critical vs non-critical load classification')
        
        if any('HIGH_TEMPERATURE' in issue for issue in issues):
            recommendations.append('Check UPS ventilation and ambient temperature')
            recommendations.append('Verify UPS internal fans are operational')
        
        if any('FREQUENCY' in issue for issue in issues):
            recommendations.append('Contact utility company regarding power quality issues')
            recommendations.append('Consider generator or frequency regulation equipment')
        
        if not issues:
            recommendations.append('UPS operating normally - continue regular monitoring')
        
        return recommendations
    
    def format_monitoring_data(self, raw_data):
        """Format monitoring data for reports and CSV export"""
        formatted = {
            'timestamp': raw_data.get('timestamp', ''),
            'ups_host': raw_data.get('ups_host', ''),
            'ip_address': raw_data.get('ip_address', ''),
            'status': raw_data.get('status', 'unknown'),
            'model': raw_data.get('model', 'Unknown'),
            'location': raw_data.get('location', 'Unknown'),
        }
        
        # Add parsed SNMP data
        parsed_data = raw_data.get('parsed_snmp_data', {})
        formatted.update({
            'input_voltage': self.get_numeric_value(parsed_data.get('input_voltage')),
            'output_voltage': self.get_numeric_value(parsed_data.get('output_voltage')),
            'input_frequency': self.get_numeric_value(parsed_data.get('input_frequency')),
            'output_load': self.get_numeric_value(parsed_data.get('output_load')),
            'battery_capacity': self.get_numeric_value(parsed_data.get('battery_capacity')),
            'battery_temperature': self.get_numeric_value(parsed_data.get('battery_temperature')),
            'ups_state': self.get_numeric_value(parsed_data.get('ups_basic_state')),
        })
        
        # Add analysis results
        formatted.update({
            'power_quality_issues': '; '.join(raw_data.get('power_quality_issues', [])),
            'alerts': '; '.join(raw_data.get('alerts', [])),
            'quality_score': raw_data.get('quality_score', 0),
            'ups_state_description': raw_data.get('ups_state_description', 'Unknown')
        })
        
        return formatted
