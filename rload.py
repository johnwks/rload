#!/usr/bin/env python

# pylint: disable=missing-docstring, locally-disabled, invalid-name, line-too-long, anomalous-backslash-in-string, too-many-arguments, too-many-locals, too-many-branches, too-many-statements

import os
import sys
import getopt
import json
import logging
from rcmdclass import Device, RcmdError
from jnpr.junos import Device as jnprDevice     # Name clash with rcmdclass's Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import ConnectAuthError, ConnectRefusedError, ConnectTimeoutError, ConnectError, LockError, UnlockError, CommitError


def usage():
    print 'Usage:\n\t', sys.argv[0], '-i config-file -c load-file device'
    print '''
        -i config-file      Config file with user credentials.
        -c load-file        Configurations in file to be applied to device.
        -t var-file         JSON file containing variables for config template. 
        -m comment          Commit comment.
        -y                  Assume YES for commit confirm.
        --mode config_mode  config_mode = (shared|private|exclusive). Default is shared.
        --load load_option  load_option = (replace|merge|override). Default is replace.
        -w                  Ignore warnings in configs.
        -l                  Do not lock configuration.
'''
    sys.exit(2)


def main():
    reload(sys)
    sys.setdefaultencoding('utf-8')

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'i:c:t:m:ywl', ['mode=', 'load='])
    except getopt.GetoptError:
        usage()

    cfgfile = None
    loadfile = None
    varfile = None
    comment = None
    noprompt = False
    config_mode = 'shared'
    load_option = 'replace'
    iwarn = False
    lock = True

    for opt, arg in opts:
        if opt == '-i':
            cfgfile = arg
        elif opt == '-c':
            loadfile = arg
        elif opt == '-t':
            varfile = arg
            try:
                jfile = open(varfile, 'r')
            except IOError:
                print 'ERROR: Unable to open %s' %(varfile)
                sys.exit(1)
            vardata = json.load(jfile)
        elif opt == '-m':
            comment = arg
        elif opt == '-y':
            noprompt = True
        elif opt == '-w':
            iwarn = True
        elif opt == '-l':
            lock = False
        elif opt == '--mode':
            if arg.lower() == 'private':
                config_mode = 'private'
            elif arg.lower() == 'exclusive':
                config_mode = 'exclusive'
            elif arg.lower() == 'shared':
                config_mode = 'shared'
            else:
                print 'Invalid config mode'
                sys.exit(1)
        elif opt == '--load':
            if arg.lower() == 'replace':
                load_option = 'replace'
            elif arg.lower() == 'merge':
                load_option = 'merge'
            elif arg.lower() == 'override':
                load_option = 'override'
            else:
                print 'Invalid load_option'
                sys.exit(1)
        else:
            usage()

    if (cfgfile is None) or (loadfile is None):
        usage()

    host = args[0]

    try:
        dev1 = Device(cfgfile=cfgfile, host=host)
    except RcmdError as e:
        print e.value
        sys.exit(1)

    devnull = open(os.devnull, 'w')
    sys.stderr = devnull
    logging.raiseExceptions = False

    dev = jnprDevice(dev1.ip, user=dev1.username, password=dev1.password, port=22, ssh_config=dev1.sshconfig, gather_facts=False)
    try:
        dev.open()
    except ConnectAuthError:
        print 'ERROR: Authentication failed.'
        sys.exit(1)
    except ConnectRefusedError:
        print 'ERROR: Connection refused.'
        sys.exit(1)
    except ConnectTimeoutError:
        print 'ERROR: Connection timed out.'
        sys.exit(1)
    except ConnectError:
        print 'ERROR: Connection failed.'
        sys.exit(1)

    print 'Connected to device %s (%s mode - %s)' %(host, config_mode, load_option)

    cu = Config(dev, mode=config_mode)

    if lock is True:
        print 'Locking the configuration'
        try:
            cu.lock()
        except LockError:
            print 'ERROR: Unable to lock configuration'
            dev.close()
            sys.exit(1)

    if varfile is None:
        print 'Loading configuration changes'
        try:
            if load_option == 'replace':
                cu.load(path=loadfile, ignore_warning=iwarn)
            elif load_option == 'merge':
                cu.load(path=loadfile, merge=True, ignore_warning=iwarn)
            elif load_option == 'override':
                cu.load(path=loadfile, overwrite=True, ignore_warning=iwarn)
        except IOError:
            print 'ERROR: Unable to open configuration file'
            sys.exit(1)
    else:
        print 'Loading configuration changes (from Jinja2 template)'
        try:
            if load_option == 'replace':
                cu.load(template_path=loadfile, template_vars=vardata, ignore_warning=iwarn)
            elif load_option == 'merge':
                cu.load(template_path=loadfile, template_vars=vardata, merge=True, ignore_warning=iwarn)
            elif load_option == 'override':
                cu.load(template_path=loadfile, template_vars=vardata, overwrite=True, ignore_warning=iwarn)
        except IOError:
            print 'ERROR: Unable to open configuration file'
            sys.exit(1)

    print 'Candidate configuration:'
    cu.pdiff()

    if noprompt is True:
        commit_confirm = 'Y'
    else:
        commit_confirm = raw_input('Do you want to commit the configuration(Y/N)? ')

    if commit_confirm in ['y', 'Y']:
        print 'Committing the configuration'
        try:
            cu.commit(comment=comment)
        except CommitError:
            print 'ERROR: Unable to commit configuration'
            if lock is True:
                print 'Unlocking the configuration'
                try:
                    cu.unlock()
                except UnlockError:
                    print 'ERROR: Unable to unlock configuration'
            dev.close()
            sys.exit(1)
        if lock is True:
            print 'Unlocking the configuration'
            try:
                cu.unlock()
            except UnlockError:
                print 'ERROR: Unable to unlock configuration'
    else:
        print 'Not committing the changes'

    dev.close()

if __name__ == '__main__':
    main()
