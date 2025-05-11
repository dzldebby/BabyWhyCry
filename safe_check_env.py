#!/usr/bin/env python3
import os
import re

# Read the .env file directly without loading it
try:
    with open("config/.env", "r") as f:
        env_content = f.read()
    
    # Check if DATABASE_URL is defined properly
    database_url_line = None
    for line in env_content.split('\n'):
        if line.startswith('DATABASE_URL='):
            # Mask any passwords in the output
            masked_line = re.sub(r':(.*?)@', ':****@', line)
            database_url_line = masked_line
            break
    
    if database_url_line:
        print(f"DATABASE_URL found in config/.env: {database_url_line}")
        
        # Check if it's properly formatted
        if database_url_line.count('=') != 1:
            print("WARNING: DATABASE_URL format may be incorrect - multiple '=' characters")
        
        # Check if it contains the pooler URL
        if "pooler.supabase.com" in database_url_line:
            print("✓ Session pooler URL detected")
        else:
            print("⚠ Session pooler URL not detected")
        
        # Check for common formatting issues
        if database_url_line.endswith('"') or database_url_line.endswith("'"):
            print("⚠ DATABASE_URL has trailing quotes which may cause issues")
        
        if "DATABASE_URL=" in database_url_line and not database_url_line.startswith("DATABASE_URL="):
            print("⚠ DATABASE_URL may have unexpected characters before variable name")
            
    else:
        print("DATABASE_URL not found in config/.env file")
        
except FileNotFoundError:
    print("config/.env file not found")
except Exception as e:
    print(f"Error reading config/.env: {e}") 