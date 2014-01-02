#!/usr/bin/env python

import subprocess
import os
import re
import logging
import srs


def doRunCommand(State):
    runcmd = ['run-command']
    ######
    ## if single machine
    if State.singleMachine.lower() == 'true':
        runcmd = ['run-command.vm']

    if State.exit_on_error:
        runcmd.append('-exit-on-error')

    # Run on 64 bit machines only
    runcmd.append('-attr x86_64')

    # Machines with local ttmp disk
    runcmd.append('-attr tscratch_tmp')

    # Add extra attrs if any
    for attr in State.extra_attrs:
        runcmd.append('-attr %s'%(attr))
    
    # Log file
    runcmd_logfile = open("%s/run-command.log" %  State.topdir, 'w')

    # Number of jobs
    runcmd.append('-J %d'%(State.njobs))

    # The script file to run
    runcmd.append('-f %s'%(os.path.join(State.topdir, 'run_batches.cmds')))

    runcmdstr = ' '.join(runcmd)
            
    # Create a pipe object to capture stdout and stderr
    runcmd_proc = subprocess.Popen(runcmdstr, shell=True, 
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Monitor run-command's output and look for pattern's matching srs-go's logging
    # Also write both stderr and stdout to run-command.log
    for line in runcmd_proc.stdout:
        runcmd_logfile.write(line)
        line = line.strip()
        match = re.match(r'srs-go:(CRITICAL|ERROR|WARNING|INFO):', line)
        if match:
            level = match.group(1)
            if level == 'CRITICAL' or level == 'ERROR':
                if State.exit_on_error:
                    logging.error('run-command.log: ' + line)
                else:   
                    # if not exiting, downgrade to a mere warning
                    logging.warning('run-command.log: ' + line)
            elif level == 'WARNING':
                logging.warning('run-command.log: ' + line)
            elif level == 'INFO':
                logging.info('run-command.log: ' + line)
        else:
            logging.debug('run-command.log: ' + line)
    runcmd_logfile.close()

    retcode = runcmd_proc.wait()

    write_failed_pvars(State)

    return retcode


def write_failed_pvars(State):
    '''For each failed task (as determined by entries in failed_tasks), write an entry to a file in failed_pvars for each pvar'''
    # Open files for writing.
    for p in State.pvar:
        try:
            p.file = open(os.path.join(State.topdir, 'failed_pvars', p.varname), 'w')
        except IOError as err:
            logging.error('Unable to write parallel variable file for variable %s: %s', p.varname, err.strerror)
            sys.exit(1)

    for failedpath in os.listdir(os.path.join(State.topdir, 'failed_tasks')):
        if re.match('task[0-9]+', failedpath):
            c = srs.Config(os.path.join(State.topdir, 'failed_tasks', failedpath, 'SRS-GO', 'config', 'MASTER.config'))
            for p in State.pvar:
                print >>p.file, c.get(p.varname)

    for p in State.pvar:
        p.file.close()
