#!/usr/bin/env python

# pylint: disable=missing-docstring, locally-disabled, invalid-name, line-too-long, anomalous-backslash-in-string, too-many-arguments, too-many-locals, too-many-branches, too-many-statements

import os
import sys
import getopt
import logging
from rcmdclass import Device, RcmdError
from jnpr.junos import Device as jnprDevice
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import ConnectAuthError, ConnectRefusedError, ConnectTimeoutError, ConnectError, LockError, UnlockError, CommitError


def usage():
    print 'Usage:\n\t', sys.argv[0], '-i config-file -c load-file [ -m comment -y ] device'
    print '''
        -i config-file  Config file with user credentials.
        -c load-file    Configurations in file to be applied to device.
        -m comment      Commit comment in "quotes".
        -y              Assume YES for commit confirm.
'''
    sys.exit(2)


def main():
    reload(sys)
    sys.setdefaultencoding('utf-8')

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'i:c:m:y')
    except getopt.GetoptError:
        usage()

    cfgfile = None
    loadfile = None
    comment = None
    noprompt = 0

    for opt, arg in opts:
        if opt == '-i':
            cfgfile = arg
        elif opt == '-c':
            loadfile = arg
        elif opt == '-m':
            comment = arg
        elif opt == '-y':
            noprompt = 1
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

    dev = jnprDevice(dev1.ip, user=dev1.username, password=dev1.password, ssh_config=dev1.sshconfig, gather_facts=False)
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

    print 'Connected to device %s' %(host)
    dev.bind(cu=Config)

    print "Locking the configuration"
    try:
        dev.cu.lock()
    except LockError:
        print "ERROR: Unable to lock configuration"
        dev.close()
        sys.exit(1)

    print "Loading configuration changes"
    try:
        dev.cu.load(path=loadfile, merge=True, ignore_warning=True)
    except IOError:
        print "ERROR: Unable to open configuration file"
        sys.exit(1)

    print "Candidate configuration:"
    dev.cu.pdiff()

    if noprompt == 1:
        commit_confirm = "Y"
    else:
        commit_confirm = raw_input('Do you want to commit the configuration(Y/N)? ')

    if commit_confirm in ["y", "Y"]:
        print "Committing the configuration"
        try:
            dev.cu.commit(comment=comment)
        except CommitError:
            print "ERROR: Unable to commit configuration"
            print "Unlocking the configuration"
            try:
                dev.cu.unlock()
            except UnlockError:
                print "ERROR: Unable to unlock configuration"
            dev.close()
            sys.exit(1)
        print "Unlocking the configuration"
        try:
            dev.cu.unlock()
        except UnlockError:
            print "ERROR: Unable to unlock configuration"
    else:
        print "Not committing the changes"

    dev.close()

if __name__ == '__main__':
    main()
