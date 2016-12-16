#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# -*- coding: utf-8 -*-
# Author: Akira Funahasi <funa@bio.keio.ac.jp>
# Last modified: Sat, 17 Dec 2016 05:14:51 +0900
# 
import errno
import datetime
import json
import os
import re
import sys
import time
import uuid

def per_section(it, is_delimiter=lambda x: x.isspace()):
    # http://stackoverflow.com/questions/25226871/splitting-textfile-into-section-with-special-delimiter-line-python
    ret = []
    for line in it:
        if is_delimiter(line):
            if ret:
                yield ret  # OR  ''.join(ret)
                ret = []
        else:
            ret.append(line.rstrip())  # OR  ret.append(line)
    if ret:
        yield ret

def touch(fname, times=None):
    os.utime(fname, times)

def is_header(line):
    # is date header (ex.) "2016-12-05  Akira Funahashi  <my@email.address>"
    p = re.compile('^\d{4}-\d{1,2}-\d{1,2}\s+.+<.*@.+>$')
    return p.match(line)

def get_namespace(header):
    namespace = ''
    m = re.compile('^\d{4}-\d{1,2}-\d{1,2}\s+.+<.*@(.+)>$').match(header)
    if m:
        namespace = m.group(1) 
    return namespace

def get_unixtimestamp(header):
    datestr = '1997-01-01 15:00:00'
    m = re.compile('^(\d{4}-\d{1,2}-\d{1,2})\s+.+<.*@.+>$').match(header)
    if m:
        datestr = m.group(1) + ' 15:00:00'
    return int(time.mktime(datetime.datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S").timetuple()))

def generate_uuid(namespace, unixtimestamp, tag, title):
    return str(uuid.uuid3(uuid.NAMESPACE_URL, 'https://' + namespace + '/' + str(unixtimestamp) + '/' + tag + '/' + title + '/'))

def create_notebook(name):
    path = name + '.qvnotebook'
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
    notebook = {
            "name": "ChangeLog Memo",
            "uuid": "clmemo"
            }
    f = open(os.path.join(path, "meta.json"), "w")
    json.dump(notebook, f, ensure_ascii=False, indent=2)
    return path

def create_note(uuid, unixtimestamp, tag, title, data):
    meta = {
            "created_at": unixtimestamp,
            "tags": [ tag ],
            "title": title,
            "updated_at": unixtimestamp,
            "uuid": uuid
            }
    content = {
            "title": title,
            "cells": [
                {
                    "type": "markdown",
                    "data": data
                    }
                ]
            }
    return meta, content

def dump_note(path, dict_meta, dict_content):
    for uuid, meta in dict_meta.iteritems():
        # key == uuid, value = meta
        unixtimestamp = meta["created_at"]
        content = dict_content[uuid]
        note_path = os.path.join(path, str(uuid) + '.qvnote')
        try:
            os.makedirs(note_path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(note_path):
                pass
            else:
                raise
        path_meta = os.path.join(note_path, "meta.json")
        f_meta = open(path_meta, "w")
        json.dump(meta, f_meta, ensure_ascii=False, indent=2)
        f_meta.close()
        path_content = os.path.join(note_path, "content.json")
        f_content = open(path_content, "w")
        json.dump(content, f_content, ensure_ascii=False, indent=2)
        f_content.close()
        touch(path_meta, (unixtimestamp, unixtimestamp))
        touch(path_content, (unixtimestamp, unixtimestamp))
        touch(note_path, (unixtimestamp, unixtimestamp))

def main():
    if len(sys.argv) != 2:
        print "Usage: %s ChangeLog.txt" % sys.argv[0]
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename) as f:
        sections = list(per_section(f))  # default delimiter
        #sections = list(per_section(f, lambda line: line.startswith('#'))) # comment

    dict_meta = dict()
    dict_content = dict()
    namespace = ''
    unixtimestamp = 0
    tag = ''
    title = ''
    uuid = ''
    count = 0
    for section in sections:
        is_duplicate = False
        if len(section) == 1 and is_header(section[0]):
            # header
            namespace = get_namespace(section[0])
            unixtimestamp = get_unixtimestamp(section[0])
        else:
            # body
            #print "=== BEGIN"
            data = ''
            for line in section:
                if re.match('^;$', line):
                    line = ''    # convert ';' to blank line
                m = re.compile('^\s+\*\s+(.+):\s+(.+)$').match(line)
                if m:
                    # title
                    tag = m.group(1)
                    title = m.group(2)
                    uuid = generate_uuid(namespace, unixtimestamp, tag, title)
                    count += 1
                else:
                    # contents (memo)
                    if re.match('^    ', line):
                        data += line.lstrip('    ') + os.linesep
                    else:
                        data += line + os.linesep
            (meta, content) = create_note(uuid, unixtimestamp, tag, title, data)
            if uuid in dict_meta:
                v = dict_content[uuid]
                data2 = v["cells"][0]["data"]
                if data2 != data:  # same uuid already exists. ChangeLog might include a wrong format.
                    is_duplicate = True
                    print "key = " + str(uuid) + " already exists! ChangeLog might include a wrong format."
                    print "will add\n" + content["cells"][0]["data"] + "\nto [" + v["title"] + "]"
                    (meta, content) = create_note(uuid, unixtimestamp, tag, title, data)
                    v["cells"].append(content["cells"][0])

            if not is_duplicate:
                dict_meta[uuid] = meta
                dict_content[uuid] = content
            #print "=== END\n"

    # create notebook directory and notes
    print "Exporting notes to ChangeLogMemo.qvnotebook ..."
    notebook_dir = create_notebook('ChangeLogMemo')
    dump_note(notebook_dir, dict_meta, dict_content)

if __name__ == "__main__":
    main()
