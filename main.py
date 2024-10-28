import yaml
import urllib.request
import os
import subprocess
import zipfile
import shutil
CACHE = os.path.join(os.getenv('APPDATA'), 'P32-Cache')
HOME = os.getenv('HOME')
PKGLIST = os.path.join(HOME, '.p32/pkglist')
def parse_meta(file):
    try:
        with open(file, 'r') as f:
            cfg = yaml.safe_load(f)

        package = cfg['Package']
        return {
            'name': package['Name'],
            'version': package['Version'],
            'maintainer': package['Maintainer'],
            'summary': package['Summary'],
            'largedesc': package['Description'],
            'sysdeps': package.get('SysDeps', '').split(','),
            'deps': package['Dependencies'].split(','),
            'optdeps': package['Optdeps'],
            'installer': package['Installer']
        }

    except FileNotFoundError:
        print(f"Error: File '{file}' not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
    except KeyError as e:
        print(f"Missing key in configuration: {e}")
    return None

def download(url, destpath, destname):
    output = os.path.join(destpath, destname)
    try:
        urllib.request.urlretrieve(url, output)
        print(f"Downloaded: {output}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def install(path):
    try:
        subprocess.run([path], check=True)
        print(f"Installed: {path}")
    except subprocess.CalledProcessError as e:
        print(f"Error installing {path}: {e}")

def sync(url, path):
    download(url, CACHE, path)
    install(os.path.join(CACHE, path))

def handlesysdeps(sysdeps):
    for sysdep in sysdeps:  # Iterate over sysdeps
        if sysdep == "redist.2019":
            download("https://aka.ms/vs/17/release/vc_redist.x64.exe", CACHE, 'r19.exe')
            install(os.path.join(CACHE, 'r19.exe'))
        elif sysdep == "net4":
            sync('https://download.microsoft.com/download/9/5/A/95A9616B-7A37-4AF6-BC36-D6EA96C8DAAE/dotNetFx40_Full_x86_x64.exe', 'net5.exe')
        else:
            print(f"P32: FATAL: No Working Dependency Found for {sysdep}")

def install_folder(path):
    meta = os.path.join(path, 'manifest.yaml')
    metadata = parse_meta(meta)
    print(f"Installing Dependencies for {metadata['name']}")
    if metadata and 'sysdeps' in metadata and metadata['sysdeps']:
        print("Installing System Dependencies")
        handlesysdeps(metadata['sysdeps'])
    else:
        print("No system dependencies to install.")
    if metadata and 'deps' in metadata and metadata['deps']:
        install(metadata['deps'])
    subprocess.run([metadata['installer']], check=True)
    print("Writting Data to the Package List")
    with open(PKGLIST, 'a') as f:
        name = metadata['name']
        version = metadata['version']
        f.write(f'{name}=>{version}\n')
        f.close()
def parse_installdata(path):
    with open(path, 'r') as c:
        cfg = yaml.safe_load(path)
        name = cfg['Retrievefile']['Name']
        url = cfg['Retrievefile']['URL']
        ln = cfg['Retrievefile']['local']
        return ln, url, name
def extract(file, output):
    with zipfile.ZipFile(file, 'r') as zipball:
        zipball.extractall(output)

def workid(path):
    par = parse_installdata(path)
    url = par['url']
    ln = par['ln']
    name = par['name']
    print(f"Downloading Tarball for {name}")
    download(url, CACHE, ln)
    out = os.path.join(CACHE, ln)
    location = os.path.join(CACHE, f'{name}-ex')
    extract(out, location)

def clean(cache):
    try:
        shutil.rmtree(CACHE)
        print(f"Cleaned cache at {CACHE}")
    except Exception as e:
        print(f"Error cleaning cache: {e}")