try:
    import json
except ImportError:
    import simplejson as json # needed on python 2.5
import tarfile
import os
import errno
import shutil
import sys

# Work around python 2/3 differences for urllib
#
# apparently urlib has undergone some different changes in all the different
# python versions which means that depending on the version, urlopen is at
# different places aswell as the different behaviour in errorhandling
# (i.e. location of HTTPError and thrown exceptions during 'empty'/not found
#  packages).
#
# The below part tries to work around all issues and I have tested existing and
# non existing packages for installation and errorhandling.
 
# python 2.5 (ok, if you install simplejson by hand)
# python 2.6 (ok)
# python 2.7 (ok)
# python 3.0 (ok)
# python 3.1 (ok)
# python 3.2 (ok)

# also note that exception handling in different python versions is incompatible
# i.e. except ImportError, e: will not work in python3+ and
#      except ImportError as e: will not work in python2.5

try:
    import urllib2
    HTTPError = urllib2.HTTPError
    doUrlOpen = urllib2.urlopen
except ImportError:
    import urllib.request
    try:
        import urllib.error
        HTTPError = urllib.error.HTTPError
    except ImportError:
        HTTPError = urllib.HTTPError
    doUrlOpen = urllib.request.FancyURLopener().open
    
    

# Replace for tarfile.nts method in python 3, as it breaks on b"\x80" in tar headers
# note: use bytes([0]) because python 2.5 does not know about b"\x80" syntax 
def my_nts(s, encoding, errors):
    p = s.find(bytes([0]))
    if p != -1:
        s = s[:p]
    if s == bytes([0x80]):
      return
    return s.decode(encoding, errors)

modules_dir = r'.\node_modules'
tmp_dir = os.path.join(modules_dir, '.tmp')

def cleanupDir(cleanPath):
    shutil.rmtree(cleanPath, ignore_errors = True)

def pkg_not_found_error(pkg):
    print('No module named "%s" in package registry! Aborting!' % pkg)
    sys.exit()    

def getMetaDataForPkg(pkg):
    url = '%s/%s/latest' % ('http://registry.npmjs.org', pkg)
    try:
        response = doUrlOpen(url)
        data = response.read().decode('utf-8')
    except HTTPError:
        pkg_not_found_error(pkg)
    except ValueError:
        # python 3.2 raises ValueError if reading empty data (not existing package)
        pkg_not_found_error(pkg)
    
    metadata = json.loads(data)
    return metadata

def saveAndExtractPackage(metaData):
    destPath = os.path.join(modules_dir, metaData['name'])
    url = metaData['dist']['tarball']
    filename = url.split('/')[-1]
    tmpFilePath = os.path.join(tmp_dir, filename)
    if os.path.isfile(tmpFilePath): # Make sure we don't re-download and reinstall anything
        return destPath
    print('Installing %s into %s ...' % (url, destPath))
    cleanupDir(destPath)
    try:
        os.makedirs(tmp_dir)
    except OSError: #, e:
        # assume we always get EEXIST due to python exception differences
        pass                                   
        #if e.errno != errno.EEXIST:
        #    raise
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
    tar.extractall(path = tmp_dir)
    tar.close()
    srcPath = os.path.join(tmp_dir, packageDir)
    shutil.move(srcPath, destPath)
    return destPath

def installDependencies(pkgDir):
    # Recursive install dependencies
    print('Checking dependencies for %s ...' % pkgDir.split('\\')[-1])
    metaData = json.loads(open(os.path.join(pkgDir, 'package.json'), 'r').read())
    for dep in metaData.get('dependencies', []):
        install(dep)

def get_installed():
    dirs = os.listdir(modules_dir)
    meta = []
    for dir in dirs:
        dir = os.path.join(modules_dir, dir, 'package.json')
        if not os.path.exists(dir):
            continue;
        f = open(dir, 'r')
        data = f.read()
        f.close()
        meta.append(json.loads(data))
    return meta

def install(pkg):
    # Installs pkg(s) into .\node_modules
    meta = getMetaDataForPkg(pkg)
    destPath = saveAndExtractPackage(meta)
    installDependencies(destPath)

def deps():
    installDependencies(os.getcwd())
    print('Dependencies done.')

def update():
    pkgs = get_installed()
    for pkg in pkgs:
        meta = getMetaDataForPkg(pkg['name'])
        if meta['version'] != pkg['version']:
            install(pkg['name'])

def usage():
    print ("""
Usage:
  python ryppi.py deps                  - Install dependencies from package.json file.
  python ryppi.py install <pkg> [<pkg>] - Install package(s), and it's/there dependencies.
  python ryppi.py update                - Checks for different version of packages in online repository, and updates as needed.
Example:
  python ryppi.py install express socket.io mongolian underscore
""")
    sys.exit()

if __name__ == '__main__':
    cleanupDir(tmp_dir)
    params = len(sys.argv)
    if params < 2:
        usage()
    if sys.argv[1] == 'install':
        if params < 3:
            usage()
        for i in range(2, params):
            install(sys.argv[i])
    elif sys.argv[1] == 'deps':
        deps()
    elif sys.argv[1] == 'update':
        update()
    else:
        usage()
    cleanupDir(tmp_dir)
    print('All done.')
