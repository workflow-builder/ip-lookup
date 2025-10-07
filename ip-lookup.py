#!/usr/bin/env python3
"""
Simple IP/DNS Lookup Script with Multiple API Fallbacks
Reads a list of IPs or DNS names and outputs owner and region information
"""

import socket
import ipaddress
import urllib.request
import urllib.error
import json
import sys
import time

class APIProvider:
    """Base class for API providers"""
    def __init__(self, name, delay):
        self.name = name
        self.delay = delay
        self.failed = False
    
    def lookup(self, ip):
        raise NotImplementedError

def lookup_ipapi_com(ip):
    """Lookup using ip-api.com (45 requests/min)"""
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,org,query"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            if data.get('status') == 'success':
                owner = data.get('org', 'Unknown')
                region = f"{data.get('regionName', 'Unknown')}, {data.get('country', 'Unknown')}"
                return owner, region, True
            else:
                return "Unknown", "Unknown", True
    except urllib.error.HTTPError as e:
        if e.code == 429:  # Rate limit exceeded
            return None, None, False
        return f"HTTP Error: {e.code}", "N/A", True
    except Exception as e:
        return f"Error: {str(e)}", "N/A", True

def lookup_ipapi_co(ip):
    """Lookup using ipapi.co (1000 requests/day, 30/min)"""
    try:
        url = f"https://ipapi.co/{ip}/json/"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'ipapi.co/#ipapi-python/1.0.4')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            if 'error' in data:
                if data.get('reason') == 'RateLimited':
                    return None, None, False
                return "Unknown", "Unknown", True
            
            owner = data.get('org', 'Unknown')
            region = f"{data.get('region', 'Unknown')}, {data.get('country_name', 'Unknown')}"
            return owner, region, True
    except urllib.error.HTTPError as e:
        if e.code == 429:  # Rate limit exceeded
            return None, None, False
        return f"HTTP Error: {e.code}", "N/A", True
    except Exception as e:
        return f"Error: {str(e)}", "N/A", True

def lookup_ipwhois_io(ip):
    """Lookup using ipwhois.io (10000 requests/month, free tier)"""
    try:
        url = f"http://ipwho.is/{ip}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            if not data.get('success', False):
                return "Unknown", "Unknown", True
            
            connection = data.get('connection', {})
            owner = connection.get('org', 'Unknown')
            if owner == 'Unknown' or owner == '':
                owner = connection.get('isp', 'Unknown')
            
            region = f"{data.get('region', 'Unknown')}, {data.get('country', 'Unknown')}"
            return owner, region, True
    except urllib.error.HTTPError as e:
        if e.code == 429:  # Rate limit exceeded
            return None, None, False
        return f"HTTP Error: {e.code}", "N/A", True
    except Exception as e:
        return f"Error: {str(e)}", "N/A", True

def lookup_ipwhois_app(ip):
    """Lookup using ipwhois.app (10000 requests/month)"""
    try:
        url = f"http://ipwhois.app/json/{ip}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            if not data.get('success', False):
                return "Unknown", "Unknown", True
            
            owner = data.get('org', 'Unknown')
            if owner == 'Unknown' or owner == '':
                owner = data.get('isp', 'Unknown')
            
            region = f"{data.get('region', 'Unknown')}, {data.get('country', 'Unknown')}"
            return owner, region, True
    except urllib.error.HTTPError as e:
        if e.code == 429:  # Rate limit exceeded
            return None, None, False
        return f"HTTP Error: {e.code}", "N/A", True
    except Exception as e:
        return f"Error: {str(e)}", "N/A", True

# API providers in order of preference
API_PROVIDERS = [
    {'name': 'ip-api.com', 'func': lookup_ipapi_com, 'delay': 1.5, 'failed': False},
    {'name': 'ipapi.co', 'func': lookup_ipapi_co, 'delay': 2.0, 'failed': False},
    {'name': 'ipwho.is', 'func': lookup_ipwhois_io, 'delay': 1.0, 'failed': False},
    {'name': 'ipwhois.app', 'func': lookup_ipwhois_app, 'delay': 1.0, 'failed': False},
]

current_provider_index = 0

def lookup_ip_with_fallback(ip):
    """Lookup IP with automatic fallback to alternative APIs"""
    global current_provider_index
    
    attempts = 0
    while attempts < len(API_PROVIDERS):
        provider = API_PROVIDERS[current_provider_index]
        
        # Skip if provider has failed
        if provider['failed']:
            current_provider_index = (current_provider_index + 1) % len(API_PROVIDERS)
            attempts += 1
            continue
        
        # Try the current provider
        owner, region, success = provider['func'](ip)
        
        if success:
            # Successful lookup
            return owner, region, provider['name'], provider['delay']
        else:
            # Rate limit hit, switch to next provider
            print(f"  ⚠️  Rate limit hit on {provider['name']}, switching to next provider...")
            provider['failed'] = True
            current_provider_index = (current_provider_index + 1) % len(API_PROVIDERS)
            attempts += 1
    
    # All providers failed
    return "All APIs exhausted", "N/A", "None", 0

def resolve_dns(hostname):
    """Resolve DNS name to IP address"""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None

def is_valid_ip(ip):
    """Check if string is a valid IP address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def process_file(input_file, output_file):
    """Process input file and write results to output file"""
    try:
        with open(input_file, 'r') as f:
            entries = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    results = []
    print(f"Processing {len(entries)} entries...\n")
    
    for i, entry in enumerate(entries, 1):
        print(f"[{i}/{len(entries)}] Checking: {entry}")
        
        # Determine if it's an IP or DNS name
        if is_valid_ip(entry):
            ip = entry
        else:
            # Try to resolve as DNS name
            ip = resolve_dns(entry)
            if not ip:
                print(f"  ❌ Could not resolve DNS name\n")
                results.append({
                    'input': entry,
                    'ip': 'N/A',
                    'owner': 'DNS resolution failed',
                    'region': 'N/A',
                    'api_used': 'N/A'
                })
                continue
        
        # Lookup IP information with automatic fallback
        owner, region, api_used, delay = lookup_ip_with_fallback(ip)
        print(f"  IP: {ip}")
        print(f"  Owner: {owner}")
        print(f"  Region: {region}")
        print(f"  API Used: {api_used}\n")
        
        results.append({
            'input': entry,
            'ip': ip,
            'owner': owner,
            'region': region,
            'api_used': api_used
        })
        
        # Rate limiting delay
        if delay > 0 and i < len(entries):
            time.sleep(delay)
    
    # Write results to output file
    try:
        with open(output_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("IP/DNS LOOKUP RESULTS\n")
            f.write("=" * 80 + "\n\n")
            
            for result in results:
                f.write(f"Input: {result['input']}\n")
                f.write(f"IP Address: {result['ip']}\n")
                f.write(f"Owner: {result['owner']}\n")
                f.write(f"Region: {result['region']}\n")
                f.write(f"API Used: {result['api_used']}\n")
                f.write("-" * 80 + "\n\n")
        
        print(f"\n✅ Results saved to '{output_file}'")
    except Exception as e:
        print(f"Error writing output file: {e}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python ip_lookup.py <input_file> <output_file>")
        print("\nExample: python ip_lookup.py ips.txt results.txt")
        print("\nInput file format (one per line):")
        print("  8.8.8.8")
        print("  google.com")
        print("  1.1.1.1")
        print("\nSupported APIs (with automatic fallback):")
        print("  1. ip-api.com (45 req/min)")
        print("  2. ipapi.co (1000 req/day, 30 req/min)")
        print("  3. ipwho.is (10000 req/month)")
        print("  4. ipwhois.app (10000 req/month)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    process_file(input_file, output_file)

if __name__ == "__main__":
    main()
