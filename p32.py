import os
import configparser
import sys
import zipfile
import ctypes
import urllib.request
import subprocess

# Constants
USERDIR = os.getenv('USERPROFILE')
P32DIR = os.path.join(USERDIR, '.p32')
CONFIG = os.path.join(P32DIR, 'config.conf')
CACHE = os.path.join(P32DIR, 'temp')

# Essential Checking
if not os.path.isdir(P32DIR):
    print("Setting up P32 Paths")
    os.mkdir(P32DIR)
if not os.path.isdir(CACHE):
    print("Setting up Cache Paths")
    os.mkdir(CACHE)

if not os.path.isfile(CONFIG):
    DEFCFG = """
[main]
url = https://juanvel4000.serv00.net/p32/main
"""
    with open(CONFIG, 'w') as cfg:
        cfg.write(DEFCFG.strip())

# Admin Privileges Check
if not ctypes.windll.shell32.IsUserAnAdmin():
    print("=> Prompting for Administrator Privileges")
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

# Base Functions
def download(url):
    if not url:
        raise ValueError("URL cannot be empty")
    try:
        location = os.path.basename(url)
        output = os.path.join(CACHE, location)
        os.makedirs(CACHE, exist_ok=True)
        urllib.request.urlretrieve(url, output)
        return output
    except Exception as e:
        print(f"An error occurred during download: {e}")
        return None

def parse(file: str) -> dict:
    cfg = configparser.ConfigParser()
    cfg.read(file)
    try:
        dependencies = cfg['Package'].get('Dependencies', '').split()
        return {
            "Name": cfg['Package'].get('Name', 'Unknown'),
            "Maintainer": cfg['Package'].get('Maintainer', 'Unknown'),
            "Version": cfg['Package'].get('Version', '0.0.0'),
            "Dependencies": dependencies,
            "Installer": cfg['Package'].get('InstallerFile', ''),
            "Summary": cfg['Package'].get('ShortDescription', ''),
            "Description": cfg['Package'].get('Description', '')
        }
    except KeyError as e:
        raise ValueError(f"Missing key in configuration: {e}")

def extract(file):
    stripped = file.split('.')
    name = stripped[0]
    output = os.path.join(CACHE, name)
    os.makedirs(output, exist_ok=True)
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(output)

def install(folder):
    values = parse(os.path.join(folder, 'P32/Manifest.ini'))
    subprocess.run([values['Installer']], check=True)

def parsenet(file):
    cfg = configparser.ConfigParser()
    cfg.read(file)
    location = cfg['Pkgnet']['Location']
    return location

def checkpkg(url, package):
    try:
        request = urllib.request.Request(f"{url}/{package}.p3s", method='HEAD')
        response = urllib.request.urlopen(request)
        return response.getcode() == 200
    except urllib.error.HTTPError:
        print(f"Error: {package} Not found")
        sys.exit(1)

def main():
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG)
    server = cfg['main']['url']
    
    if len(sys.argv) != 3:
        print("Usage: p32 <install> <package_name>")
        sys.exit(1)

    action = sys.argv[1]
    package = sys.argv[2]
    
    if action == "install":
        checkpkg(server, package)
        pkgf = f"{server}/{package}.p3s"
        print("Downloading Package...")
        path = download(pkgf)
        pnf = parsenet(path)
        print("Downloading Package Net File...")
        out = download(pnf)
        print("Installing...")
        install(out)

if __name__ == "__main__":
    main()
