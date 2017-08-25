#!/usr/bin/env python
# Script name: MakeSkyModelFromCatalog.py
# Version: 1.0 (June 2012)
# Author(s): S. Zimmer (zimmer@slac.stanford.edu)
# code that allows simulation of catalog sources in gtobssim
# see: https://confluence.slac.stanford.edu/x/nIB6Bw
# (uses a gtlike xml but implements gleam conversion)
# SZ (OKC/SU) June 2012
# report issues to: 
#
# usage: MakeSkyModelFromCatalog.py <inputfile> --options
########
from uw.like.SpatialModels import *
from uw.like.roi_extended import ExtendedSource
from uw.like.Models import *
from uw.like.roi_monte_carlo import MonteCarlo
from uw.like.pointspec_helpers import PointSource,get_default_diffuse
from uw.utilities.xml_parsers import parse_sources
from tempfile import NamedTemporaryFile
import xml.dom.minidom as xdom
from StringIO import StringIO
from shutil import rmtree, move
from sys import argv
import astropy.io.fits as pyfits
import os
import uw.like.Models
from uw.like.roi_monte_carlo import NoSimulatedPhotons

def AddCatalog(xmlfile,idstart,idstop,tmpbase,diffdir=None):
    if idstart is None:
        idstart = -1
    if idstop is None:
        idstop = 999999999 # huge number!
    # This code takes an xmlfile and creates a new one
    kstring = '<?xml version="1.0" ?>\n<source_library/>'
    xo = xdom.parse(StringIO(kstring))
    xf = xdom.parse(xmlfile)
    sid = 0
    for src in xf.getElementsByTagName("source"):
        if sid>=idstart and sid<idstop:
            xo.childNodes[-1].appendChild(expandSource(src,diffdir=diffdir))
        sid+=1
    oname = tmpbase+'/srccat.xml'
    fo = open(oname,'w')
    fo.write(xo.toxml())
    return oname

def expandSource(xmlnode,diffdir=None):
    #expands the path in an xml node
    spectrum = xmlnode.getElementsByTagName("spectrum")[0]
    spatial = xmlnode.getElementsByTagName("spatialModel")[0]
    obj = [spectrum,spatial]
    baseDir = ""
    if diffdir is None:
        baseDir = os.environ['SKYMODEL_DIR']
    else:
        baseDir = diffdir
    for object in obj:
        if  object.hasAttribute("file"):
            fname=object.getAttribute("file")
            if (len(baseDir)==0):
                baseDir=os.getcwd()
            object.setAttribute("file",os.path.join(baseDir,os.path.basename(fname)))
    return xmlnode
    
    
class summary:
    def __init__(self,**kwargs):
        self.runs = []
        self.__dict__.update(kwargs)
    def print_summary(self):
        print '* run summary *'
        print 'output dir: %s'%os.getenv('SKYMODEL_DIR')
        print 'tagname: %s'%self.runs[0].tag
        for run in self.runs:
            tagname = run.tag.split(";")
            path = os.path.join(os.getenv('SKYMODEL_DIR'),tagname[0])
            if len(tagname)!=1:
                print '---'
                idstart = run.idstart
                idstop = run.idstop
                if run.idstart is None:
                    idstart = -1
                if run.idstop is None:
                    idstop = 99999999 # BIG NUMBER!
                    
                print '%s start id: %i stop id: %i'%(tagname[1],idstart,idstop)
                ppath = os.path.join(path,tagname[1])
                print 'dir %s \t files %i'%(ppath,len(os.listdir(ppath)))
                print '---'
            else:
                print 'dir %s \t files %i'%(path,len(os.listdir(path)))
    def add(self,run):
        self.runs.append(run)

class container:
    def __init__(self,**kwargs):
        self.__dict__.update(kwargs)

def verifyFile(filename):
    # checks whether file is xml or FITS, returns -1 if something else
    fformat = -1
    if os.path.isfile(filename):
        try:
            xf = xdom.parse(filename)
            fformat = 1
        except xml.parsers.expat.ExpatError:
            try:
                pf = pyfits.open(filename)
                fformat = 2
            except IOError:
                raise NotImplementedError("Cannot parse %s, only FITS and xml supported")
            
    return fformat

def checkXML(xmlfile):
    warnings = 0
    xf = xdom.parse(xmlfile)
    for src in xf.getElementsByTagName("source"):
        srcname = str(src.getAttribute("name"))
        spatModel = src.getElementsByTagName("spatialModel")[0]
        filename = None
        if spatModel.hasAttribute("file"):
            filename = str(spatModel.getAttribute("file"))
            if not os.path.isfile(filename):
                print '*ERROR* could not find file %s that is required for source %s'%(filename,srcname)
                warnings+=1
 
    if warnings!=0:
        raise IOError("*ERROR* we found %i errors that may produce errors in the future, please correct them first"%warnings)

def get_nsources(filename,filemode):
    if filemode==1:
        xp = xdom.parse(filename)
        sources = xp.getElementsByTagName("source")
        return len(sources)
    else:
        return 0
    
def cFITS2XML(fitsfile):
    raise NotImplementedError("FITS support comes in a later release")

def removePath(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            rmtree(os.path.join(root, d))
    

def main(inputfile,tag,idstart=None,idstop=None,debug=False,diffdir=None,tstart=0, tstop=8000, ft2file='None', emin=100, emax=1e5, seed=1000,irf='P7SOURCE_V6', dry_run=True, gtifile=None, zmax=None):
    if not diffdir is None:
        diffdir = diffdir.replace("~",os.getenv('HOME'))
    fid = verifyFile(inputfile)
    catalogxml = None
    if fid == 1:
        catalogxml = inputfile
    elif fid == 2:
        catalogxml = cFITS2XML(inputfile)
    if not os.getenv("LSB_JOBID")==None:
        Outdir =  NamedTemporaryFile(dir='/scratch/').name # data is stored in Outdir/raw
    else:
        Outdir =  NamedTemporaryFile(dir='/tmp/').name # data is stored in Outdir/raw
    print '*OUTDIR* %s'%Outdir
    Emin = 10
    Emax = 1e6
    print '*INFO*: current pfile settings',os.getenv('PFILES');
    # AllSky by default, need a ROI object to proceed
    os.mkdir(Outdir)
    modXML = AddCatalog(inputfile,idstart,idstop,Outdir,diffdir=diffdir)
    # now we check whether we have files that refer to nowhere
    checkXML(modXML)
    ps,ds = None,None
    ps,ds=parse_sources(modXML)
    sources = ps+ds
    # this is only necessary to make use of the roi_montecarlo.py code 
    montecarlo_object = MonteCarlo(
        # ST-09-29-00
        sources = sources,
        gtifile=gtifile, 
        zmax = zmax, 
        tempbase = Outdir,
        irf = irf,
        ft1 = Outdir+'/raw/ft1.fits',
        ft2 = ft2file,
        tstart = tstart,
        tstop = tstop,
        emin = emin,
        emax = emax,
        seed = seed,
        savedir = Outdir+'/raw/'
    )
    montecarlo_object.simulate(dry_run=dry_run)
    # now assemble list of files
    # check if we have parts
    tags = tag.split(";")
    storedir = os.getenv("SKYMODEL_DIR")+"/"
    for t in tags:
        storedir+="/"+t
    print '*INFO* store data here: %s'%storedir
    files = os.listdir(os.path.join(Outdir,'raw'))
    try:
        os.mkdir(storedir)
    except OSError:
        print '*WARNING* dir %s exists already, overwriting'%storedir
        removePath(storedir)
    # now move
    for f in files:
        infile = os.path.join(Outdir+'/raw/',f)
        outfile= os.path.join(storedir,f)
        move(infile,outfile)
    # finally, clean up
    removePath(Outdir)
    
if __name__ == "__main__":
    rootdir = os.environ['PWD']
    usg = "\033[1;31m%prog <xmlfile> --tag=<tagname>\033[1;m \n"

    desc = "\033[34mcode that allows simulation of catalog sources in gtobssim \n(uses a gtlike xml but implements gleam conversion)\n see: https://confluence.slac.stanford.edu/x/nIB6Bw for details\033[0m \n"
  
    from optparse import OptionParser
    parser = OptionParser(description=desc, usage =usg)
    parser.add_option("--tag",dest="tag", default = None, type = str,
                      help = "*REQUIRED* name of the SkyModel, if split, have subdirectories labled with part X")
    parser.add_option("--splitsize",dest="splitsize",default=0, type= int,
                      help = "number of sources per part")
    parser.add_option("--SkyModelDir",dest="rootdir",default=rootdir, type=str,
                      help = "the location of where all SkyModels are stored, use this or set \
                      SKYMODEL_DIR environment variable")
    parser.add_option("--diffdir",dest='diffdir',default=None,type=str,
                      help = 'the location of FITS files if simulating of extended sources, e.g. the location of the FSSC templates for the extended 2FGL sources')
    
    parser.add_option("--emin",dest='emin',default=100,type=float,
                      help = "the minimum energy for the simulation")
    parser.add_option("--emax",dest='emax',default=1e5,type=float,
                      help = "the maximum energy for the simulation")
    parser.add_option("--zmax",dest='zmax',default=None,type=float,
                      help = "the maximum zenith angle for simulated events")
    parser.add_option("--tstart",dest='tstart',default=0,type=float,
                      help = "the minimum time for the simulation")
    parser.add_option("--tstop",dest='tstop',default=8000,type=float,
                      help = "the maximum time for the simulation")
    parser.add_option("--ft2file",dest='ft2file',default=None,type=str,
                      help = "give a valid spacecraft FT2 file")
    parser.add_option("--gtifile",dest='gtifile',default=None,type=str,
                      help = "give a valid FT1 or LTCUBE file to take gti from")
    parser.add_option("--irf",dest='irf',default='P7SOURCE_V6',type=str,
                      help = "the IRF for the simulation")
    parser.add_option("--seed",dest='seed',default=1000,type=int,
                      help = "seed for the simulation")
    parser.add_option("--simulate",dest='dry_run',action='store_false',default=True,
                      help = "if you actually want to simulate something using gtobssim")
    
        
    (opts, arguments) = parser.parse_args()
    inputfile = argv[1]
    if os.getenv("SKYMODEL_DIR") is None:
        os.environ["SKYMODEL_DIR"] = opts.rootdir

    # fix tagname
    no_split = False
    simulations = summary()
    fid = verifyFile(inputfile)
    nsources = get_nsources(inputfile,fid)
    print '*INFO* found %i sources in %s'%(nsources,inputfile)
    if opts.tag is None:
        raise Exception("Need to provide a tagname")
    if opts.splitsize == 0:
        no_split = True #no splitting
        idstart = None
        idstop = None
        c = container(tag = opts.tag, idstart = idstart, idstop = idstop, inputfile=inputfile)
        simulations.add(c)
    else:
        parts = nsources/opts.splitsize
        mod = nsources%opts.splitsize
        idstart = 0
        idstop = opts.splitsize-1
        storedir = os.path.join(os.getenv('SKYMODEL_DIR'),opts.tag)
        try:
            os.mkdir(storedir)
        except OSError:
            print '*WARNING* dir %s exists already, overwriting'%storedir
            removePath(storedir)
        #assemble parts
        for i in range(parts):
            tagname = opts.tag+";part_%i"%i
            c = container(tag = tagname, idstart = idstart, idstop = idstop, inputfile=inputfile)
            simulations.add(c)
            idstart+=opts.splitsize
            idstop+=opts.splitsize
        # rest:
        if mod!=0:
            tagname = opts.tag+";part_%i"%parts
            idstop = nsources
            c = container(tag = tagname, idstart = idstart, idstop = idstop, inputfile=inputfile)
            simulations.add(c)

    # walk through simulations
    Tstart = opts.tstart
    Tstop = opts.tstop
    if not opts.ft2file is None:
        Tstart = None
        Tstop = None
    for run in simulations.runs:
        main(inputfile=run.inputfile,tag=run.tag,idstart=run.idstart,idstop=run.idstop,diffdir=opts.diffdir,tstart=Tstart, tstop=Tstop, ft2file=opts.ft2file, emin=opts.emin, emax=opts.emax, seed=opts.seed,irf=opts.irf, dry_run=opts.dry_run, gtifile=opts.gtifile, zmax=opts.zmax)
    simulations.print_summary()
