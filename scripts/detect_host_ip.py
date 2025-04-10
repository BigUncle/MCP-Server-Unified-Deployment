#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Host IP Detection Script
------------------------
This script provides reliable methods to detect the real host IP address
that is accessible from external clients in containerized environments.
"""

import os
import socket
import subprocess
import logging
import json
import time
from pathlib import Path
import ipaddress

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('host_ip_detection')

def is_valid_ip(ip):
    """
    Validate if a string is a valid IP address
    
    Args:
        ip (str): IP address to validate
        
    Returns:
        bool: True if valid IP address
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def get_docker_gateway_ip():
    """
    Get the Docker gateway IP address (usually host IP from container's perspective)
    
    Returns:
        str: IP address or None if not found
    """
    try:
        # Try to get the default gateway using route command
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            # Parse the output to find the gateway IP
            for line in result.stdout.splitlines():
                if "default via" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "via" and i < len(parts) - 1:
                            gateway = parts[i+1]
                            if is_valid_ip(gateway):
                                return gateway
        
        # Alternative method using netstat
        result = subprocess.run(
            ["netstat", "-rn"],
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "0.0.0.0" in line or "default" in line:
                    parts = line.split()
                    for part in parts:
                        if is_valid_ip(part) and not part.startswith("0.0.0.0"):
                            return part
                            
        return None
    except Exception as e:
        logger.error(f"Error getting Docker gateway IP: {e}")
        return None

def get_local_ips():
    """
    Get all non-loopback local network interface IPs
    
    Returns:
        list: List of IP addresses
    """
    local_ips = []
    
    try:
        # Method 1: Using hostname lookup
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if is_valid_ip(ip) and not ip.startswith("127."):
                local_ips.append(ip)
                
        # Method 2: Using socket connection method
        if not local_ips:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('10.255.255.255', 1))
                ip = s.getsockname()[0]
                if is_valid_ip(ip) and not ip.startswith("127."):
                    local_ips.append(ip)
            except:
                pass
            finally:
                s.close()
                
        # Method 3: Using hostname -I command
        try:
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if result.returncode == 0:
                for ip in result.stdout.split():
                    if is_valid_ip(ip) and not ip.startswith("127."):
                        local_ips.append(ip)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Error getting local IPs: {e}")
    
    # Filter duplicate IPs
    return list(set(local_ips))

def check_environment_variables():
    """
    Check environment variables for explicitly configured host IP
    
    Returns:
        str: IP address from environment or None
    """
    # Check for explicit REAL_HOST_IP setting
    real_host_ip = os.environ.get('REAL_HOST_IP')
    if real_host_ip and is_valid_ip(real_host_ip):
        logger.info(f"Using explicitly configured REAL_HOST_IP: {real_host_ip}")
        return real_host_ip
    
    # Check for EXTERNAL_HOST setting
    external_host = os.environ.get('EXTERNAL_HOST')
    if external_host:
        # If it's an IP address, use it directly
        if is_valid_ip(external_host):
            logger.info(f"Using EXTERNAL_HOST IP: {external_host}")
            return external_host
        
        # If it's a hostname, try to resolve it
        try:
            ip = socket.gethostbyname(external_host)
            logger.info(f"Resolved EXTERNAL_HOST {external_host} to {ip}")
            return ip
        except socket.gaierror:
            logger.warning(f"Could not resolve EXTERNAL_HOST: {external_host}")
    
    return None

def is_docker_internal_ip(ip):
    """
    Check if an IP is likely a Docker internal network IP
    
    Args:
        ip (str): IP address to check
        
    Returns:
        bool: True if likely Docker internal IP
    """
    if not ip:
        return False
        
    try:
        # Docker commonly uses these network ranges for internal addressing
        ip_obj = ipaddress.ip_address(ip)
        
        # Docker default bridge network
        if ip_obj in ipaddress.ip_network('172.17.0.0/16'):
            return True
        
        # User-defined networks often use these ranges
        if ip_obj in ipaddress.ip_network('172.18.0.0/16'):
            return True
        if ip_obj in ipaddress.ip_network('172.19.0.0/16'):
            return True
        if ip_obj in ipaddress.ip_network('172.20.0.0/16'):
            return True
            
        # Docker Desktop specific ranges
        if ip_obj in ipaddress.ip_network('198.18.0.0/16'):
            return True
            
        return False
    except:
        return False

def find_best_host_ip():
    """
    Find the best IP address for external clients to connect to the host
    
    This function tries multiple strategies to determine the most appropriate
    IP address for external clients to connect to services running in the container.
    
    Returns:
        str: Best IP address to use
    """
    # Strategy 1: Check environment variables for explicit configuration
    env_ip = check_environment_variables()
    if env_ip and not is_docker_internal_ip(env_ip):
        return env_ip
    
    # Strategy 2: Get the Docker gateway IP (often the host's IP)
    gateway_ip = get_docker_gateway_ip()
    if gateway_ip and not is_docker_internal_ip(gateway_ip):
        logger.info(f"Using Docker gateway IP: {gateway_ip}")
        return gateway_ip
    
    # Strategy 3: Try to find a suitable local IP
    local_ips = get_local_ips()
    
    # Filter out Docker internal IPs
    external_ips = [ip for ip in local_ips if not is_docker_internal_ip(ip)]
    
    if external_ips:
        # Prefer IPs in common LAN subnets
        for ip in external_ips:
            ip_obj = ipaddress.ip_address(ip)
            
            # 192.168.x.x range (common home/office networks)
            if ip_obj in ipaddress.ip_network('192.168.0.0/16'):
                logger.info(f"Using LAN IP from 192.168.x.x range: {ip}")
                return ip
                
            # 10.x.x.x range (common for larger networks)
            if ip_obj in ipaddress.ip_network('10.0.0.0/8'):
                logger.info(f"Using LAN IP from 10.x.x.x range: {ip}")
                return ip
                
            # 172.16.x.x range (excluding Docker ranges we already checked)
            if ip_obj in ipaddress.ip_network('172.16.0.0/16'):
                logger.info(f"Using LAN IP from 172.16.x.x range: {ip}")
                return ip
        
        # If no preferred subnet, use the first external IP
        logger.info(f"Using first available external IP: {external_ips[0]}")
        return external_ips[0]
    
    # Strategy 4: Fall back to environment IP even if it's a Docker internal IP
    if env_ip:
        logger.warning(f"No suitable external IP found, using configured IP: {env_ip}")
        return env_ip
    
    # Last resort: use localhost, which isn't externally accessible
    logger.error("Could not determine a suitable host IP, falling back to localhost")
    return "localhost"

def write_host_info(ip):
    """
    Write the detected host IP to a file for other processes to use
    
    Args:
        ip (str): The detected host IP
    """
    try:
        # Create host info record with metadata
        host_info = {
            "host_ip": ip,
            "timestamp": time.time(),
            "detected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_docker_internal": is_docker_internal_ip(ip),
            "detection_method": "detect_host_ip.py script"
        }
        
        config_dir = Path("/app/config")
        if not config_dir.exists():
            config_dir = Path.home()
        
        # Write to JSON file
        info_file = config_dir / "host_info.json"
        with open(info_file, "w") as f:
            json.dump(host_info, f, indent=2)
        
        logger.info(f"Host IP information written to {info_file}")
        
        # Also set environment variable for current process
        os.environ["DETECTED_HOST_IP"] = ip
        
    except Exception as e:
        logger.error(f"Error writing host info: {e}")

if __name__ == "__main__":
    # When run directly, find and print the best host IP
    detected_ip = find_best_host_ip()
    print(f"Detected host IP: {detected_ip}")
    write_host_info(detected_ip)