import urllib2
import json
import tarfile
import os
import errno
import shutil

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
    
    def cleanupTmp(self):
        shutil.rmtree(self.tmpPath, ignore_errors=True)

    def saveAndExtractPackage(self, metaData):
        """
        """
        self.cleanupTmp()
        try:
            os.makedirs(self.tmpPath)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        url = metaData['dist']['tarball']
        filename = url.split("/")[-1] 
        tmpFilePath = os.path.join(NpmRegistry.NPM_BASE_DIR, NpmRegistry.NPM_TMP_DIR, filename)
        print tmpFilePath
        response = urllib2.urlopen(url)
        tmpfile = open(tmpFilePath,'wb')
        tmpfile.write(response.read())
        tmpfile.close()
        tar = tarfile.open(tmpFilePath)
        tar.extractall(path = self.tmpPath)
        srcPath = os.path.join(self.tmpPath, "package")
        destPath = os.path.join(NpmRegistry.NPM_BASE_DIR, metaData["name"])
        shutil.move(srcPath, destPath)
 

def install(pkg):
    """ Installs pkg into ./node_modules
    """
    npm = NpmRegistry()
    meta = npm.getMetaDataForPkg(pkg)
    npm.saveAndExtractPackage(meta)
    
    
install("express")