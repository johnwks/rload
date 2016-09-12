#!/usr/bin/env python

# pylint: disable=missing-docstring, locally-disabled, invalid-name, line-too-long, anomalous-backslash-in-string, too-many-return-statements, no-member, too-many-locals, too-many-branches, too-many-statements

import os
import sys
import getopt
import ConfigParser
import sqlite3
import logging

from jnpr.junos import Device
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

    if ((cfgfile is None) or (loadfile is None)):
        usage()

    host = args[0]

    try:
        cf = open(cfgfile, 'r')
    except IOError:
        print 'ERROR: Unable to open CFG file'
        return
    cf.close()

    config = ConfigParser.ConfigParser()
    config.read(cfgfile)

    SQLDB = config.get('DevicesDB', 'path')
    if SQLDB is None:
        print 'ERROR: Unable to get DB file from CFG file'
        return

    db = sqlite3.connect(SQLDB)
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM Devices WHERE Hostname = ? COLLATE NOCASE LIMIT 1''', (host,))
    rows1 = cursor.fetchone()
    if rows1 is None:
        print 'ERROR: Device does not exist in DB'
        return
    else:
        host = rows1[0]
        ip = rows1[1]
        proxy = rows1[4]
        authid = rows1[5]
    db.close()

    authsection = 'Auth' + str(authid)
    user = config.get(authsection, 'username')
    passwd = config.get(authsection, 'password')

    if proxy != 0:
        proxysection = 'Proxy' + str(proxy)
        sshconfig = config.get(proxysection, 'sshconfig')

    devnull = open(os.devnull, 'w')
    sys.stderr = devnull

    logging.raiseExceptions = False

    dev = Device(ip, user=user, password=passwd, ssh_config=sshconfig, gather_facts=False)
    try:
        dev.open()
    except ConnectAuthError:
        print 'ERROR: Authentication failed.'
        return
    except ConnectRefusedError:
        print 'ERROR: Connection refused.'
        return
    except ConnectTimeoutError:
        print 'ERROR: Connection timed out.'
        return
    except ConnectError:
        print 'ERROR: Connection failed.'
        return

    print 'Connected to device %s' %(host)
#    dev.bind(cu=Config)

    print "Locking the configuration"
#    try:
#        dev.cu.lock()
#    except LockError:
#        print "ERROR: Unable to lock configuration"
#        dev.close()
#        return

    print "Loading configuration changes"
#    try:
#        dev.cu.load(path=loadfile, merge=True)
#    except IOError:
#        print "ERROR: Unable to open configuration file"
#        return

    print "Candidate configuration:"
#    dev.cu.pdiff()

    if noprompt == 1:
        commit_confirm = "Y"
    else:
        commit_confirm = raw_input('Do you want to commit the configuration(Y/N)? ')

    if commit_confirm in ["y", "Y"]:
        print "Committing the configuration"
#        try:
#            dev.cu.commit(comment=comment)
#        except CommitError:
#            print "ERROR: Unable to commit configuration"
#            print "Unlocking the configuration"
#            try:
#                dev.cu.unlock()
#            except UnlockError:
#                print "ERROR: Unable to unlock configuration"
#            dev.close()
#            return
        print "Unlocking the configuration"
#        try:
#            dev.cu.unlock()
#        except UnlockError:
#            print "ERROR: Unable to unlock configuration"
    else:
        print "Not committing the changes"

    dev.close()

if __name__ == "__main__":
    main()
