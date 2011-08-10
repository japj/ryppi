import json
import tarfile
import os
import errno
import shutil
import sys

# Work around python 2/3 differences for urllib
try:
    import urllib2
    doUrlOpen = urllib2.urlopen
except ImportError as e:
    import urllib.request
    doUrlOpen = urllib.request.FancyURLopener().open

# Replace for tarfile.nts method in python 3, as it breaks on b"\x80" in header
def my_nts(s, encoding, errors):
    p = s.find(b"\0")
    if p != -1:
        s = s[:p]
    if s == b"\x80":
      return
    return s.decode(encoding, errors)

class NpmRegistry(object):
    NPM_BASE_DIR = r".\node_modules"
    NPM_BASE_URL = "http://registry.npmjs.org"
    NPM_TMP_DIR = ".tmp"

    def __init__(self):
        self.tmpPath = os.path.join(NpmRegistry.NPM_BASE_DIR, NpmRegistry.NPM_TMP_DIR)

    def getMetaDataForPkg(self, pkg):
        url = "%s/%s/latest" % (NpmRegistry.NPM_BASE_URL, pkg)
        response = doUrlOpen(url)
        data = response.read().decode('utf-8')
        metadata = json.loads(data)
        return metadata

    def cleanupDir(self, cleanPath):
        shutil.rmtree(cleanPath, ignore_errors=True)

    def saveAndExtractPackage(self, metaData):
        destPath = os.path.abspath(os.path.join(NpmRegistry.NPM_BASE_DIR, metaData['name']))
        url = metaData['dist']['tarball']
        print('Installing %s into %s ...' % (url, destPath))
        self.cleanupDir(self.tmpPath)
        self.cleanupDir(destPath)
        try:
            os.makedirs(self.tmpPath)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        filename = url.split('/')[-1]
        tmpFilePath = os.path.join(NpmRegistry.NPM_BASE_DIR, NpmRegistry.NPM_TMP_DIR, filename)
        response = doUrlOpen(url)
        tmpfile = open(tmpFilePath, 'wb')
        tmpfile.write(response.read())
        tmpfile.close()
        try:
            tar = tarfile.open(tmpFilePath)
        except tarfile.ReadError:
            tarfile.nts = my_nts
            tar = tarfile.open(tmpFilePath)
        packageDir = tar.getmembers()[0].name.split('/')[0] # First entry of tar wil contain destination path
        tar.extractall(path = self.tmpPath)
        tar.close()
        srcPath = os.path.join(self.tmpPath, packageDir)
        shutil.move(srcPath, destPath)
        self.cleanupDir(self.tmpPath)
        return destPath

    def installDependencies(self, topDir):
        # Recursive install dependencies
        print('Going to install dependencies of %s ...' % topDir)
        curDir = os.getcwd()
        os.chdir(topDir)
        metaData = json.loads(open('package.json', 'r').read())
        for dep in metaData.get('dependencies', []):
            metaDep = self.getMetaDataForPkg(dep)
            depPath = self.saveAndExtractPackage(metaDep)
            self.installDependencies(depPath)
        os.chdir(curDir) # Go back to original directory

def get_installed():
    dirs = os.listdir(r".\node_modules")
    meta = []
    for dir in dirs:
        dir = os.path.join(r".\node_modules", dir, "package.json")
        if not os.path.exists(dir):
            continue;
        f = open(dir, 'r')
        data = f.read()
        f.close()
        meta.append(json.loads(data))
    return meta

def install(pkg):
    # Installs pkg into ./node_modules
    npm = NpmRegistry()
    meta = npm.getMetaDataForPkg(pkg)
    destPath = npm.saveAndExtractPackage(meta)
    npm.installDependencies(destPath)
    print('Install done.')

def deps():
    npm = NpmRegistry()
    npm.installDependencies(os.getcwd())
    print('Dependencies done.')

def update():
    npm = NpmRegistry()
    pkgs = get_installed()
    for pkg in pkgs:
        meta = npm.getMetaDataForPkg(pkg['name'])
        if meta['version'] != pkg['version']:
            install(pkg['name'])

def usage():
    print ("""
Usage:
  python ryppi.py deps                  - Install dependencies from package.json file.
  python ryppi.py install <pkg> [<pkg>] - Install package(s), and it's/there dependencies.
""")
    sys.exit()

if __name__ == '__main__':
    params = len(sys.argv)
    if params < 2:
        usage()
    if sys.argv[1] == "install":
        if params < 3:
            usage()
        for i in range(2, params):
            install(sys.argv[i])
    elif sys.argv[1] == "deps":
        deps()
    elif sys.argv[1] == "update":
        update()
    else:
        usage()