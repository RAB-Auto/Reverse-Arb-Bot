import subprocess
import os
import json
from webull import webull

# Function to install webull package
def install_webull():
    subprocess.run(['pip', 'install', 'webull'], check=True)

# Function to prompt for and save configuration
def get_user_input(prompt):
    return input(prompt)

def save_config(config):
    config_file_path = 'webull_config.json'
    with open(config_file_path, 'w') as f:
        json.dump(config, f, indent=4)

def load_config():
    config_file_path = 'webull_config.json'
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as f:
            return json.load(f)
    return {}

def set_initial_config():
    config = load_config()

    if 'did' not in config:
        config['did'] = get_user_input("Enter your Webull DID: ")
        # Set the DID in Webull
        wb = webull()
        wb._set_did(config['did'])

    if 'user_agent' not in config:
        config['user_agent'] = get_user_input("Enter User-Agent: ")
    
    if 'osv' not in config:
        config['osv'] = get_user_input("Enter OSV: ")

    save_config(config)

    return config

# Function to modify the webull package with the user's settings
def modify_webull_package(config):
    result = subprocess.run(['pip', 'show', 'webull'], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith('Location:'):
            webull_path = line.split(': ')[1]
            break
    else:
        raise FileNotFoundError("Webull source code not found. Make sure the package is installed.")

    webull_file = os.path.join(webull_path, 'webull', 'webull.py')
    
    if not os.path.exists(webull_file):
        raise FileNotFoundError("Webull source code not found. Make sure the package is installed.")

    with open(webull_file, 'r') as file:
        lines = file.readlines()

    new_lines = []
    for line in lines:
        if "'User-Agent':" in line:
            line = f"            'User-Agent': '{config['user_agent']}',\n"
        if "'osv':" in line:
            line = f"            'osv': '{config['osv']}',\n"
        new_lines.append(line)

    with open(webull_file, 'w') as file:
        file.writelines(new_lines)

    print("Webull package modified successfully.")

# Main setup function
def main():
    install_webull()
    config = set_initial_config()
    modify_webull_package(config)

if __name__ == "__main__":
    main()
