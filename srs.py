######################################################################
# $Id: srs.py 625 2013-09-24 21:46:06Z janin $
#
# File: srs.py
#
# Copyright 2012, 2013 International Computer Science Institute
# See the file LICENSE for licensing terms.
#
# System for Running Systems python library.
#
# For documentation and tutorial, see doc subdirectory.
#
# Current subsystems:
#
#   Config - Configuration Management
#
# Versions
#
#  Initial version: Feb 28, 2012 Adam Janin
#
#  Version 0.2: April 3, 2012 Adam Janin.
#
# Changes to Config
#
# Based on suggestions from Arlo Faria, the separate namespace for
# macros was removed. You can now refer to any previous variable with
# the $name convention. SDEFINE remains as a way to call a shell, but
# uses the same namespace as variables. Variable values are expanded
# as they're read.
#
# Removed the calls to readvars and readdocs. Instead, all variables
# are read in when you create a Config.
#
#  Version 0.3: April 12, 2012 Adam Janin
#
# Changes to Config
#
# Added write() to dump a config file's variables.
# Added set() to set a variable.
# Added adddoc() to add a doc string to a variable.
#
#  Version 0.4: January 21, 2013 Adam Janin
#
# Changes to Config
#
# In Config.write(), dollar signs in values are now replaced with $$
# so that when they're read in again, they remain $.
#
# Added Config.dumpsh() to print variables in a form suitable for
# use with eval in bourne shell.
#
# Added Config.dumpcsh() for use with csh.
#
# Added Config.dumpmatlab() for use with matlab.
#
#  Version 0.41: February 20, 2013 Adam Janin
#
# In Config, relative INCLUDE paths are now computed relative
# to the source config file.
#
#  Version 0.5: March 20, 2013 Adam Janin
#
# Added Config.dumpperl() for use with perl. Takes the name of a hash.
#
# TODO
#
#

import logging
import string
import subprocess
import sys
import datetime
import re
import os.path

VERSION = 0.5

class MacroError(Exception):
    '''Thrown by Config when a macro definition or use has problems.'''
    def __init__(self, msg, configfile, line):
        self.msg = msg
        self.configfile = configfile
        self.line = line
    def __str__(self):
        return '%s at line %d of config file %s'%(self.msg, self.line, self.configfile)

class ConfigDocString:
    '''Stores a documentation string for a particular variable.'''
    def __init__(self, configfile, line, comment):
        self.configfile = configfile
        self.line = line
        self.comment = comment.strip()
    def __str__(self):
        return '(Line %d of config file %s)\n%s\n'%(self.line, self.configfile, self.comment)

class Config:
    '''
    System for Running Systems configuration file handler.
    '''

    class _VarEntry:
        '''Initially empty namespace to store variables'''
        def __getitem__(self, var):
            return getattr(self, var)

    def __init__(self, *filenames):

        # Where to store variables read from config file.
        # Allows use c.vars.confvar in addition to c.get('confvar')
        # Values will be strings
        self.vars = Config._VarEntry()

        # Allows use of c.docs.confvar.
        # Values will be a list of type ConfigDocString
        self.docs = Config._VarEntry()
        
        # Top level config files
        self._topfiles = filenames

        # Name of config file we're currently traversing
        self._curconfigfilename = None

        # Line number of config file we're currently traversing
        self._curconfigfileline = None

        # List of all the config files used in this Config
        self._included_files = []

        self._readvars()

    def __contains__(self, var):
        return hasattr(self.vars, var)
        
    def get(self, var, default=None):
        '''Returns variables's value, or default (None if not specified)'''
        if hasattr(self.vars, var):
            return getattr(self.vars, var)
        else:
            return default

    def set(self, name, val):
        '''Set a variable's value.'''
        setattr(self.vars, name, val)
        if not hasattr(self.docs, name):
            setattr(self.docs, name, [])

    def getdoc(self, var):
        '''Get variables doc strings. Returns a list of type ConfigDocString'''
        return getattr(self.docs, var)

    def adddoc(self, name, docstr, filename='[unknown]', linenumber=0):
        docentry = ConfigDocString(filename, linenumber, docstr)
        if not hasattr(self.docs, name):
            setattr(self.docs, name, [])
        if not hasattr(self.vars, name):
            setattr(self.vars, name, None)
        getattr(self.docs, name).insert(0, docentry)

    def getdocstring(self, var):
        '''Get the full string representing the doc strings of the variable.'''
        ret = ''
        for elem in getattr(self.docs, var):
            comment = elem.comment.strip()
            if comment != '':
                ret = ret + elem.__str__()
        return ret

    def macroexpand(self, instr):
        '''Do macro expansion of instr and return the string result.'''
        ret = instr
        # Use the current vars as keys, removing system-specific
        # ones (that all are like __name__).
        usedict = { akey: self.vars.__dict__[akey] for akey in self.vars.__dict__.keys() if not (akey.startswith('__') and akey.endswith('__')) }
        try:
            ret = string.Template(instr).substitute(usedict)
        except KeyError as err:
            raise MacroError('Undefined variable in \'%s\''%(instr), self._curconfigfilename, self._curconfigfileline)
        except ValueError as err:
            raise MacroError('Malformed or illegal value \'%s\''%(instr), self._curconfigfilename, self._curconfigfileline)
        return ret

    def _readvars(self):
        '''
        Read all variables from the config files into this instance of Config.
        '''
        for topfile in self._topfiles:
            logging.info('Reading from config file %s', topfile)
            self._readvars_from_file(topfile)

    def _readvars_from_file(self, configfile):
        '''Read variables and comments from a config file'''
        self._included_files.append(configfile)
        self._curconfigfilename = configfile
        curcomments = [] # list of comment strings in the current comment block.
        lastblank = False  # True if we just read a blank line
        with open(configfile) as f:
            self._curconfigfileline = 0
            for line in f:
                self._curconfigfileline += 1
                line = line.strip()
                if line == '':
                    lastblank = True
                    continue
                if line[0] == '#':
                    if lastblank:
                        curcomments = []
                    curcomments.append(line[1:].strip())
                    lastblank = False
                    continue
                lastblank = False
                try:
                    (cmd, args) = line.split(None, 1)
                except ValueError:
                    raise ValueError('Invalid line \'%s\' at line %d in config file %s'%(line, self._curconfigfileline, configfile))
                cmd = cmd.strip()
                args = args.strip()
                if cmd == 'INCLUDE':
                    curcomments = []
                    includefile = self.macroexpand(args)
                    #print "jooddang : ", includefile
                    if not os.path.isabs(includefile):
                        # The following computes includefile relative to
                        # the directory where configfile lives.
                        includefile = os.path.normpath(os.path.join(os.path.dirname(configfile), includefile))
                    logging.info('Including %s at line %d in %s',
                                 includefile, self._curconfigfileline, configfile)
                    linenumber = self._curconfigfileline

                    self._readvars_from_file(includefile)

                    self._curconfigfileline = linenumber
                    self._curconfigfilename = configfile
                elif cmd == 'SDEFINE':
                    self._handle_sdefine(line, curcomments)
                    curcomments = []

                # Just a plain variable definition.
                elif cmd not in self.vars.__dict__:
                    logging.debug('Found %s at line %d in %s',
                                  cmd, self._curconfigfileline, configfile)
                    setattr(self.vars, cmd, self.macroexpand(args))
                    self._newdoc(cmd, curcomments)
                    curcomments = []
                else:
                    self._newdoc(cmd, curcomments)
                    curcomments = []

    def _handle_sdefine(self, line, curcomments):
        try:
            (cmd, args) = line.strip().split(None, 1)
        except ValueError:
            raise ValueError('Invalid SDEFINE \'%s\' at line %d in config file %s'%(line, self._curconfigfileline, self._curconfigfilename))
        cmd = cmd.strip()
        args = args.strip()
        if cmd != 'SDEFINE':
            raise ValueError('Invalid SDEFINE line \'%s\' at line %d in config file %s'%(line, self._curconfigfileline, self._curconfigfilename))

        try:
            (name, shellcmd) = args.split(None, 1)
        except ValueError:
            raise MacroError('Invalid sdefine \'%s\''%(line), self._curconfigfilename, self._curconfigfileline)
        
        name = name.strip()
        self._newdoc(name, curcomments)
        # Only set if not already set.
        if name not in self.vars.__dict__:
            logging.debug('Defining %s to command %s at line %d in %s',
                          name, shellcmd, self._curconfigfileline, self._curconfigfilename)

            shellcmd = self.macroexpand(shellcmd)
            proc = subprocess.Popen(shellcmd, shell=True, stdout=subprocess.PIPE)
            (shellout, shellerr) = proc.communicate()
            if proc.returncode != 0:
                logging.warning('\"%s\" returned non-zero exit at line %d of config file %s', line, self._curconfigfileline, self._curconfigfilename)
            shellout = shellout.strip()
            setattr(self.vars, name, shellout)

    def _newdoc(self, name, comments):
        docentry = ConfigDocString(self._curconfigfilename, self._curconfigfileline, '\n'.join(comments))
        if not hasattr(self.docs, name):
            setattr(self.docs, name, [])
        getattr(self.docs, name).insert(0, docentry)

    def dumpsh(self, prefix=''):
        '''Write all values to stdout in a format suitable for use with eval in bourne shell'''
        for varname in sorted(self.vars.__dict__):
            print '%s%s=\'%s\'' % (prefix, varname, string.replace(self.get(varname), '\'', '\'\"\'\"\''))

    def dumpcsh(self, prefix=''):
        '''Write all values to stdout in a format suitable for use with eval in csh shell'''
        for varname in sorted(self.vars.__dict__):
            print 'set %s%s=\'%s\'' % (prefix, varname, string.replace(self.get(varname), '\'', '\'\"\'\"\''))

    def dumpmatlab(self, prefix=''):
        '''Write all values to stdout in a format suitable for use with eval in matlab'''
        for varname in sorted(self.vars.__dict__):
            print '%s%s=\'%s\';' % (prefix, varname, string.replace(self.get(varname), '\'', '\'\''))

    def dumpperl(self, hashname='config'):
        '''Write all values to stdout in a format suitable for use with eval in perl'''
        for varname in sorted(self.vars.__dict__):
            print '$%s{\'%s\'}=\'%s\';' % (hashname, varname, string.replace(self.get(varname), '\'', '\\\''))


    def write(self, fileobj=None, withcomments=False):
        '''Write all values to fileobj. If fileobj is None, write to stdout. If fileobj is a string, write to the file with that name. If fileobj is a file type (e.g. as returned from open), append to it. If withcomments is True, dump the comments associated with each variable.'''
        if fileobj is None:
            f = sys.stdout
        elif isinstance(fileobj, str):
            f = open(fileobj, 'w')
        else:
            f = fileobj

        if withcomments:
            print >>f, '# Config file created on', str(datetime.datetime.now())
            print >>f, '# Files included:'
            print >>f, '# ', '\n#  '.join(self._included_files)
            print >>f, ''
        for varname in sorted(self.vars.__dict__):
            if withcomments:
                for comment in self.getdoc(varname):
                    print >>f, '# (From line %d of %s)'%(comment.line, comment.configfile)
                    for commentline in re.split('\\n', comment.comment):
                        print >>f, '#', commentline
            print >>f, varname, string.replace(self.get(varname), '$', '$$')

            if withcomments:
                print >>f, ''

        if isinstance(fileobj, str):
            f.close()


def which(file):
    for path in os.environ["PATH"].split(":"):
        if os.path.exists(path) is False:
            continue
        if file in os.listdir(path):
            if path[-1] == '/':
                path = path[:-1]
            # return "%s/%s" % (path, file)
            return "%s/" % (path)
