#!/usr/bin/env python

# pylint: disable=missing-docstring, locally-disabled, invalid-name, line-too-long, anomalous-backslash-in-string, too-many-arguments, too-many-locals, too-many-branches, too-many-statements

import os
import sys
import argparse
import json
import logging
from rcmdclass import Device, RcmdError
from jnpr.junos import Device as jnprDevice     # Name clash with rcmdclass's Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import ConnectAuthError, ConnectRefusedError, ConnectTimeoutError, ConnectError, LockError, UnlockError, CommitError


def main():
    parser = argparse.ArgumentParser(description='Load configuration file into a JunOS device.')
    parser.add_argument('host', help='Device to configure.')
    parser.add_argument('-i', '--cfgfile', required=True, help='Config file with user credentials.')
    parser.add_argument('-c', '--loadfile', required=True, help='Configurations in file to be applied to device.')
    parser.add_argument('-t', '--varfile', default=None, help='JSON file containing variables for Jinja2 config template.')
    parser.add_argument('-m', '--comment', default=None, help='Commit comment.')
    parser.add_argument('-y', '--noprompt', action='store_true', help='Assume YES for commit confirm.')
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('--shared', dest='config_mode', action='store_const', const='shared', help='Shared config mode (JunOS default).')
    group1.add_argument('--private', dest='config_mode', action='store_const', const='private', help='Private config mode.')
    group1.add_argument('--exclusive', dest='config_mode', action='store_const', const='exclusive', help='Exclusive config mode.')
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument('--replace', dest='load_option', action='store_const', const='replace', help='Replace load mode (JunOS default).')
    group2.add_argument('--merge', dest='load_option', action='store_const', const='merge', help='Merge load mode.')
    group2.add_argument('--override', dest='load_option', action='store_const', const='override', help='Override load mode.')
    group2.add_argument('--update', dest='load_option', action='store_const', const='update', help='Update load mode.')
    parser.add_argument('-w', '--nowarn', dest='iwarn', action='store_true', help='Ignore warnings in configs.')
    parser.add_argument('-l', '--nolock', dest='lock', action='store_false', help='Do not lock configuration.')
    args = parser.parse_args()
    host = args.host
    cfgfile = args.cfgfile
    loadfile = args.loadfile
    varfile = args.varfile
    comment = args.comment
    noprompt = args.noprompt
    config_mode = args.config_mode
    load_option = args.load_option
    iwarn = args.iwarn
    lock = args.lock

    if varfile is not None:
        try:
            jfile = open(varfile, 'r')
        except IOError:
            print(f'ERROR: Unable to open {varfile}')
            sys.exit(1)
        vardata = json.load(jfile)
    if config_mode is None:
        config_mode = 'shared'
    if load_option is None:
        load_option = 'replace'

    try:
        dev1 = Device(cfgfile=cfgfile, host=host)
    except RcmdError as e:
        print(e.value)
        sys.exit(1)

    # devnull = open(os.devnull, 'w')
    # sys.stderr = devnull
    # logging.raiseExceptions = False

    dev = jnprDevice(dev1.ip, user=dev1.username, password=dev1.password, port=22, ssh_config=dev1.sshconfig, gather_facts=False)
    try:
        dev.open()
    except ConnectAuthError:
        print('ERROR: Authentication failed.')
        sys.exit(1)
    except ConnectRefusedError:
        print('ERROR: Connection refused.')
        sys.exit(1)
    except ConnectTimeoutError:
        print('ERROR: Connection timed out.')
        sys.exit(1)
    except ConnectError:
        print('ERROR: Connection failed.')
        sys.exit(1)

    print(f'Connected to device {host} (config mode: {config_mode}, load option: {load_option})')

    cu = Config(dev, mode=config_mode)

    if lock is True:
        print('Locking the configuration')
        try:
            cu.lock()
        except LockError:
            print('ERROR: Unable to lock configuration')
            dev.close()
            sys.exit(1)

    if varfile is None:
        print('Loading configuration changes')
        try:
            if load_option == 'replace':
                cu.load(path=loadfile, ignore_warning=iwarn)
            elif load_option == 'merge':
                cu.load(path=loadfile, merge=True, ignore_warning=iwarn)
            elif load_option == 'override':
                cu.load(path=loadfile, overwrite=True, ignore_warning=iwarn)
            elif load_option == 'update':
                cu.load(path=loadfile, update=True, ignore_warning=iwarn)
        except IOError:
            print('ERROR: Unable to open configuration file')
            sys.exit(1)
    else:
        print('Loading configuration changes (from Jinja2 template)')
        try:
            if load_option == 'replace':
                cu.load(template_path=loadfile, template_vars=vardata, ignore_warning=iwarn)
            elif load_option == 'merge':
                cu.load(template_path=loadfile, template_vars=vardata, merge=True, ignore_warning=iwarn)
            elif load_option == 'override':
                cu.load(template_path=loadfile, template_vars=vardata, overwrite=True, ignore_warning=iwarn)
            elif load_option == 'update':
                cu.load(template_path=loadfile, template_vars=vardata, update=True, ignore_warning=iwarn)
        except IOError:
            print('ERROR: Unable to open configuration file')
            sys.exit(1)

    print('Candidate configuration:')
    cu.pdiff()

    if noprompt is True:
        commit_confirm = 'Y'
    else:
        commit_confirm = input('Do you want to commit the configuration(Y/N)? ')

    if commit_confirm in ['y', 'Y']:
        print('Committing the configuration')
        try:
            cu.commit(comment=comment)
        except CommitError:
            print('ERROR: Unable to commit configuration')
            if lock is True:
                print('Unlocking the configuration')
                try:
                    cu.unlock()
                except UnlockError:
                    print('ERROR: Unable to unlock configuration')
            dev.close()
            sys.exit(1)
        if lock is True:
            print('Unlocking the configuration')
            try:
                cu.unlock()
            except UnlockError:
                print('ERROR: Unable to unlock configuration')
    else:
        print('Not committing the changes')

    dev.close()


if __name__ == '__main__':
    main()
