#!/usr/bin/env python
# Script name: gtlike2simFastConverter.py
# Version: 1.0 (20th March 2013)
# Description: Converts an XML file from the gtlike format to the gtobssim format
# Author(s): G.Vianello (giacomov@slac.stanford.edu), M. Razzano (massimiliano.razzano@pi.infn.it)

from uw.utilities.xml_parsers import parse_sources
from optparse import OptionParser
import uw.like.roi_monte_carlo
import os,sys


#Get Script name
ScriptName = os.path.split(sys.argv[0])[1].split('.')[0]

#######################################################
# put here your general variables...
#######################################################


######################################################
def convert(input,output,emin,emax):
  if (output=='None'):
    output=input[:-4]+'_simlibrary.xml'
    print 'Using default output name:',output

  ps,ds=parse_sources(input)
  sources = ps
  sources.extend(ds)
  directory = os.path.dirname(output)
  if(directory==''):
    directory = os.path.abspath('.')
  else:
    directory = os.path.abspath(directory)
  pass
  
  mc = uw.like.roi_monte_carlo.MCModelBuilder(sources,
                                              savedir=directory,
                                              emin=float(emin),
                                              emax=float(emax))
  mc.build(output)
  print 'File saved as',output
  return output


##################################################
#     Main
##################################################
if __name__=='__main__':
  usg = "\033[1;31m%prog -e emin -E emax inputfilename\033[1;m \n"

  desc = "\033[34mThis script converts a gtlike-style XML model file to a gtobssim source library file \033[0m \n"

  parser=OptionParser(description=desc,usage=usg)
  parser.add_option("-e","--emin",type="float",default=100.,help="minimum energy (MeV) for the integration of the source model")
  parser.add_option("-E","--emax",type="float",default=600000.,help="maximum energy (MeV) for the integration of the source model")
  parser.add_option("-o","--output",type="string",default="None",help="output XML file name (if not specified, a default name will be used")

  (options,args) = parser.parse_args()

  eMin=options.emin
  eMax=options.emax
  OutputFileName=options.output

  print '************************************'
  print '** '+ScriptName
  print '************************************'

  InputFileName=''
  
  if (len(args)==0):
    print 'Error. No input file provided. Exit!'
    print 'Run gtlike2simFastConverter -h for help'
    sys.exit(1)
  else:
    InputFileName = args[0]


  print '\n**Input XML file:',InputFileName

  print '\n**Input parameters:'
  for key, val in parser.values.__dict__.iteritems():
    print key,':', val

  convert(InputFileName,OutputFileName,eMin,eMax)
