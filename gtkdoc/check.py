# -*- python; coding: utf-8 -*-
#
# gtk-doc - GTK DocBook documentation generator.
# Copyright (C) 2007  David Nečas
#               2007-2017  Stefan Sauer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

#
# Script      : gtkdoc-check
# Description : Runs various checks on built documentation and outputs test
#                results. Can be run druring make check, by adding this to the
#                documentations Makefile.am: TESTS = $(GTKDOC_CHECK)
#

# Support both Python 2 and 3
from __future__ import print_function

import os
import re
import subprocess
from glob import glob


class FileFormatError(Exception):

    def __init__(self, detail):
        self.detail = detail


def grep(regexp, lines, what):
    pattern = re.compile(regexp)
    for line in lines:
        for match in re.finditer(pattern, line):
            return match.group(1)
    raise FileFormatError(what)


def check_empty(filename):
    with open(filename) as f:
        count = sum(1 for line in f if line.strip())
    return count


def check_includes(filename):
    # Check that each XML file in the xml directory is included in doc_main_file
    with open(filename) as f:
        lines = f.read().splitlines()
        num_missing = 0
        for include in glob('xml/*.xml'):
            try:
                next(line for line in lines if include in line)
            except StopIteration:
                num_missing += 1
                print('%s:1:E: doesn\'t appear to include "%s"' % (filename, xml_file))

    return num_missing


def get_variable(env, lines, variable):
    value = env.get(variable,
                    grep(r'^\s*' + variable + '\s*=\s*(\S+)', lines, variable))
    return value


def read_file(filename):
    with open(filename) as f:
        return f.read().splitlines()


def run_tests(workdir, doc_module, doc_main_file):
    checks = 4

    print('Running suite(s): gtk-doc-' + doc_module)

    # Test #1
    statusfilename = os.path.join(workdir, doc_module + '-undocumented.txt')
    statusfile = read_file(statusfilename)
    try:
        undocumented = int(grep(r'^(\d+)\s+not\s+documented\.\s*$',
                                statusfile, 'number of undocumented symbols'))
        incomplete = int(grep(r'^(\d+)\s+symbols?\s+incomplete\.\s*$',
                              statusfile, 'number of incomplete symbols'))
    except FileFormatError as e:
        print('Cannot find %s in %s' % (e.detail, statusfilename))
        return checks  # consider all failed

    total = undocumented + incomplete
    if total:
        print(doc_module + '-undocumented.txt:1:E: %d undocumented or incomplete symbols' % total)

    # Test #2
    undeclared = check_empty(os.path.join(workdir, doc_module + '-undeclared.txt'))
    if undeclared:
        print(doc_module + '-undeclared.txt:1:E: %d undeclared symbols\n' % undeclared)

    # Test #3
    unused = check_empty(os.path.join(workdir, doc_module + '-unused.txt'))
    if unused:
        print(doc_module + '-unused.txt:1:E: %d unused documentation entries\n' % unused)

    # Test #4
    missing_includes = check_includes(os.path.join(workdir, doc_main_file))

    # Test Summary
    failed = (total > 0) + (undeclared != 0) + (unused != 0) + (missing_includes != 0)
    rate = 100.0 * (checks - failed) / checks
    print("%.1f%%: Checks %d, Failures: %d" % (rate, checks, failed))
    return failed


def run(options=None):
    """Runs the tests.

    Returns:
      int: a system exit code.
    """

    # Get parameters from test env, if not there try to grab them from the makefile
    # We like Makefile.am more but builddir does not necessarily contain one.
    makefilename = 'Makefile.am'
    if not os.path.exists(makefilename):
        makefilename = 'Makefile'
    makefile = read_file(makefilename)

    # For historic reasons tests are launched in srcdir
    workdir = os.environ.get('BUILDDIR', None)
    if not workdir:
        workdir = '.'

    try:
        doc_module = get_variable(os.environ, makefile, 'DOC_MODULE')
        doc_main_file = get_variable(os.environ, makefile, 'DOC_MAIN_SGML_FILE')
    except FileFormatError as e:
        print('Cannot find %s in %s' % (e.detail, makefilename))
        return 1

    doc_main_file = doc_main_file.replace('$(DOC_MODULE)', doc_module)

    return run_tests(workdir, doc_module, doc_main_file)
