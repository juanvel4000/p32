import yaml
import urllib.request
import os
import subprocess
import zipfile
import shutil
import sys
import logging
from typing import Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

USER = os.getenv("USER")
CACHE = os.path.join(os.getenv('APPDATA'), 'P32-Cache')
HOME = os.getenv('USERPROFILE')
PKGLIST = os.path.join(HOME, '.p32/pkglist')

def create_conf() -> None:
    conf_path = os.path.join(HOME, '.p32/config.conf')
    logger.info("Creating configuration file at %s", conf_path)
    os.makedirs(os.path.dirname(conf_path), exist_ok=True)
    with open(conf_path, 'w') as f:
        f.write("[Server]\nurl = https://juanvel4000.serv00.net/p32/main/\n")

def load_yaml(file: str) -> Dict:
    """Load a YAML file and handle exceptions."""
    try:
        with open(file, 'r') as f:
            return yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        logger.error("Error loading YAML file '%s': %s", file, e)
        return {}

def parse_meta(file: str) -> Dict[str, str]:
    """Parse metadata from a manifest YAML file."""
    cfg = load_yaml(file)
    package = cfg.get('Package', {})
    return {
        'name': package.get('Name', 'Unknown'),
        'version': package.get('Version', 'Unknown'),
        'maintainer': package.get('Maintainer', 'Unknown'),
        'summary': package.get('Summary', ''),
        'largedesc': package.get('Description', ''),
        'sysdeps': [dep.strip() for dep in package.get('SysDeps', '').split(',') if dep.strip()],
        'deps': [dep.strip() for dep in package.get('Dependencies', '').split(',') if dep.strip()],
        'optdeps': package.get('Optdeps', []),
        'installer': package.get('Installer', '')
    }

def download(url: str, destpath: str, destname: str) -> None:
    """Download a file from a URL to a specified path."""
    output = os.path.join(destpath, destname)
    try:
        urllib.request.urlretrieve(url, output)
        logger.info("Downloaded: %s", output)
    except Exception as e:
        logger.error("Error downloading %s: %s", url, e)

def run_installer(path: str) -> None:
    """Run an installer from a specified path."""
    logger.info("Attempting to install from: %s", path)
    try:
        subprocess.run([path], check=True)
        logger.info("Installed: %s", path)
    except subprocess.CalledProcessError as e:
        logger.error("Error installing %s: %s", path, e)

def handle_sysdeps(sysdeps: List[str]) -> None:
    """Handle system dependencies."""
    if not sysdeps:
        logger.info("No valid system dependencies found.")
        return

    logger.info("Handling system dependencies: %s", sysdeps)
    sysdep_urls = {
        "redist.2019": "https://aka.ms/vs/17/release/vc_redist.x64.exe",
        "net4": 'https://download.microsoft.com/download/9/5/A/95A9616B-7A37-4AF6-BC36-D6EA96C8DAAE/dotNetFx40_Full_x86_x64.exe'
    }

    for sysdep in sysdeps:
        if sysdep in sysdep_urls:
            download(sysdep_urls[sysdep], CACHE, f'{sysdep}.exe')
            run_installer(os.path.join(CACHE, f'{sysdep}.exe'))
        else:
            logger.error("No working dependency found for %s", sysdep)

def install_folder(path: str) -> None:
    """Install a package from a specified folder."""
    metadata = parse_meta(os.path.join(path, 'manifest.yaml'))
    package_name = metadata['name']
    logger.info("Installing Dependencies for %s", package_name)

    handle_sysdeps(metadata['sysdeps'])

    # Check if the installer exists before trying to run it
    installer_path = metadata['installer']
    if not os.path.isfile(installer_path):
        logger.error("Installer not found: %s", installer_path)
        return

    # Log the installer path and attempt to run it
    logger.info("Running installer: %s", installer_path)
    run_installer(installer_path)

    with open(PKGLIST, 'a') as f:
        f.write(f"{metadata['name']}=>{metadata['version']}\n")

def extract(file: str, output: str) -> None:
    """Extract a zip file to a specified output directory."""
    with zipfile.ZipFile(file, 'r') as zipball:
        zipball.extractall(output)
        logger.info("Extracted %s to %s", file, output)

def work_id(path: str) -> None:
    """Download a tarball and install the package."""
    ln, url, name = parse_install_data(path)
    logger.info("Downloading tarball for %s", name)
    download(url, CACHE, ln)
    extract(os.path.join(CACHE, ln), os.path.join(CACHE, f'{name}-ex'))
    install_folder(os.path.join(CACHE, f'{name}-ex'))

def clean(cache: str) -> None:
    """Clean the cache directory."""
    try:
        shutil.rmtree(cache)
        logger.info("Cleaned cache at %s", cache)
    except Exception as e:
        logger.error("Error cleaning cache: %s", e)

def check_server(conf: str, test: str) -> bool:
    """Check if a package exists on the server."""
    cfg = load_yaml(conf)
    if not cfg:
        return False

    server = cfg['Server']['url']
    request_url = os.path.join(server, test)
    try:
        urllib.request.urlopen(request_url)
        return True
    except urllib.error.HTTPError as e:
        return e.code not in (404, 403, 500)
    except urllib.error.URLError:
        return False

def net_dl(conf: str, rf: str) -> None:
    """Download a package from the server."""
    if check_server(conf, rf):
        cfg = load_yaml(conf)
        tdl = os.path.join(cfg['Server']['url'], f'{rf}.prf')
        download(tdl, CACHE, f'{rf}.prf')
        work_id(os.path.join(CACHE, f'{rf}.prf'))
    else:
        logger.warning("Package %s not found", rf)

def echo_help() -> None:
    """Display help information."""
    print("P32 - Open Source Windows Package Manager")
    print("Available Actions:")
    print("  install       - Install a Package from the server")
    print("  help          - Display this message")
    print("  install-local - Install a local Package")
    print(f"You may want to modify the {HOME}/.p32/config.conf file to select another server")

def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: p32 install <package_name>")
        sys.exit(1)

    package_name = sys.argv[2]
    action = sys.argv[1]

    config_path = os.path.join(HOME, '.p32/config.conf')
    if not os.path.isfile(config_path):
        create_conf()

    try:
        if action == "install":
            net_dl(config_path, package_name)
        elif action == "help":
            echo_help()
        elif action == "install-local":
            extract(package_name, os.path.join(CACHE, f'{package_name}-ex'))
            install_folder(os.path.join(CACHE, f'{package_name}-ex'))
            clean(CACHE)
        else:
            print("Please run: p32 help")
    except Exception as e:
        logger.error("An error occurred: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[3] == "--verbose":
        logger.setLevel(logging.DEBUG)
    main()