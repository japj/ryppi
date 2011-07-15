import urllib2
import json
import tarfile
import os
import errno
import shutil
import sys

class NpmRegistry(object):
    NPM_BASE_DIR = r".\node_modules"
    NPM_BASE_URL = "http://registry.npmjs.org"
    NPM_TMP_DIR = ".tmp"
    
    def __init__(self):
        self.tmpPath = os.path.join(NpmRegistry.NPM_BASE_DIR, NpmRegistry.NPM_TMP_DIR)
         
    def getMetaDataForPkg(self, pkg):
        """
        """
        url = "%s/%s/latest" % (NpmRegistry.NPM_BASE_URL, pkg)
        response = urllib2.urlopen(url)
        data = response.read()
        metadata = json.loads(data)
        return metadata
    
    def cleanupDir(self, cleanPath):
        shutil.rmtree(cleanPath, ignore_errors=True)

    def saveAndExtractPackage(self, metaData):
        """
        """
        destPath = os.path.abspath(os.path.join(NpmRegistry.NPM_BASE_DIR, metaData["name"]))
        url = metaData['dist']['tarball']
        
        print "installing %s into %s" % (url, destPath)
        
        self.cleanupDir(self.tmpPath)
        self.cleanupDir(destPath)
        
        try:
            os.makedirs(self.tmpPath)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        
        filename = url.split("/")[-1] 
        tmpFilePath = os.path.join(NpmRegistry.NPM_BASE_DIR, NpmRegistry.NPM_TMP_DIR, filename)
        response = urllib2.urlopen(url)
        tmpfile = open(tmpFilePath,'wb')
        tmpfile.write(response.read())
        tmpfile.close()
        tar = tarfile.open(tmpFilePath)
        packageDir = tar.getmembers()[0].name.split('/')[0] # first entry of tar wil contain destination path
        tar.extractall(path = self.tmpPath)
        srcPath = os.path.join(self.tmpPath, packageDir)
        shutil.move(srcPath, destPath)
        return destPath
        
    def installDependencies(self, topDir):
        """ recursive install dependencies
        """
        print 'going to install dependencies of %s' % topDir
        curDir = os.getcwd()
        os.chdir(topDir)
        metaData = json.loads(open("package.json","r").read())        
        for dep in metaData.get('dependencies', []):
            metaDep = self.getMetaDataForPkg(dep) 
            depPath = self.saveAndExtractPackage(metaDep)
            self.installDependencies(depPath)
        
        # go back to original directory
        os.chdir(curDir)

def install(pkg):
    """ Installs pkg into ./node_modules
    """
    npm = NpmRegistry()
    meta = npm.getMetaDataForPkg(pkg)    
    destPath = npm.saveAndExtractPackage(meta)
    npm.installDependencies(destPath)
    print 'install done'
    
def deps():
    npm = NpmRegistry()
    npm.installDependencies(os.getcwd())
    print 'deps done'

def usage():
    print """
Usage:
  ryppi deps          - Install dependencies from package.json file. (default)
  ryppi install <pkg> - Install a package, and nest its deps.
"""
    # TODO:
    #  ryppi rm <pkg>      - Remove a package, or all of them if no args.
    #  ryppi ls            - Show installed packages.
    sys.exit()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        
    if sys.argv[1] == "install":
        if len(sys.argv) != 3:
            usage()
        install(sys.argv[2])
    elif sys.argv[1] == "deps":
        deps()
    else:
        usage()