#!/usr/bin/env python

'''

@ purpose:

A module intended to read and parse .asl files on disk.

'''

# IMPORT FUNCTIONS FROM COMMON.FUNCTIONS
from .common.functions import stats2

# IMPORT STATIC VARIABLES FROM MAIN
from __main__ import inputdir
from __main__ import outputdir
from __main__ import forensic_mode
from __main__ import no_tarball
from __main__ import quiet

from __main__ import archive
from __main__ import startTime
from __main__ import full_prefix
from __main__ import data_writer

import os
import subprocess
import glob
import csv
import gzip
import logging

import re
from itertools import groupby
from operator import itemgetter
from collections import OrderedDict
from datetime import datetime, timedelta
try:
    from past.builtins import range as xrange
except:
    pass
from .common.dateutil import parser

_modName = __name__.split('_')[-2]
_modVers = '.'.join(list(__name__.split('_')[-1][1:]))
log = logging.getLogger(_modName)


def asl_parse(logfile, logdata, headers, output):
    x = 0
    data = []
    singlelines = {}
    multilines = {}

    for i in logdata:
        x += 1
        if re.search(r'^\d{4}\-\d{2}\-\d{2}', i):
            singlelines[x] = i.rstrip()
        else:
            data.append(x)
            data.append(x - 1)
            data.append(x + 1)
            multilines[x] = i.rstrip()

    data = list(OrderedDict.fromkeys(sorted(data)))
    ranges = []
    #for key, group in groupby(enumerate(data), lambda (index, item): index - item):
    for group in enumerate(data):
        #group = map(itemgetter(1), group)
        if len(group) > 1:
            ranges.append(range(group[0], group[-1]))
        else:
            ranges.append(group[0])

    for u in ranges:
        chain = []
        for z in u:
            if multilines.get(z) is None:
                lno = z
                anchor = singlelines.get(z)
            else:
                val = multilines.get(z).replace('\t', '').replace('  ', '')
                chain.append(val)

        try:
            singlelines[lno] = anchor + ' ' + ''.join(chain)
        except TypeError:
            if not "NOTE:Most system logs have moved" in ''.join(chain):
                log.debug("Line does not resemble an ASL entry: {0}.".format(chain))
        except UnboundLocalError:
            if len(u) > 0:
                log.debug("No ASL data? {0}".format(u))

    for k, v in singlelines.items():
        line = v
        if not 'last message repeated' in line:
            record = OrderedDict((h, '') for h in headers)
            m = re.match(
                r"^(?P<datetime>\d{4}\-\d{2}\-\d{2} \w\w:\w\w:\w\w\.\d{3}Z) (?P<systemname>.*?) (?P<processName>.*?)\[(?P<PID>[0-9]+)\].*?:\s{0,1}(?P<message>.*)", line)
            record['src_file'] = logfile
            record['timestamp'] = m.group('datetime').replace(' ', 'T')
            record['log_systemname'] = m.group('systemname')
            record['processname'] = m.group('processName')
            record['pid'] = m.group('PID')
            record['message'] = m.group('message')

            output.write_entry(record.values())


def module():
    os.environ['TZ'] = 'UTC0'

    headers = ['src_file', 'timestamp', 'log_systemname', 'processname', 'pid', 'message']
    output = data_writer(_modName, headers)

    asl_loc = os.path.join(inputdir,'private/var/log/asl/*.asl')
    varlogasl_inputdir = glob.glob(asl_loc)

    if len(varlogasl_inputdir) == 0:
        log.debug("Files not found in: {0}".format(asl_loc))

    for asllog in varlogasl_inputdir:
        FNULL = open(os.devnull, 'w')
        asl_out, e = subprocess.Popen(
            ["syslog", "-f", asllog, '-T', 'utc.3'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
        if "Invalid Data Store" in asl_out.decode('utf-8'):
            log.debug("Could not parse {0}. Invalid Data Store error reported - file may be corrupted.".format(asllog))
            continue
        if not e:
            oasllog = asl_out.decode('utf-8').split('\n')
            asl_parse(asllog, oasllog, headers, output)
        else:
            log.error("Could not parse ASL logs.")

if __name__ == "__main__":
    print("This is an AutoMacTC module, and is not meant to be run stand-alone.")
    print("Exiting.")
    sys.exit(0)
else:
    module()
