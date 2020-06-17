# -*- coding: utf-8 -*-
#!/usr/bin/env python
import os
import sys
import shutil
import re
import requests
import urllib

try:
    from bs4 import BeautifulSoup
except ImportError as e:
    os.system('pip install bs4')
    from bs4 import BeautifulSoup

BASEURL     = "https://www.subtitlecat.com/"
SEARCH_URL  = "index.php?search={keyword}"

LIB_PATH  = "/mnt/gdrive/labels/SOD/STARS"
TMPDIR  = "/opt/work/subs/download"
SUBS = [".srt", ".smi"]
SUBFIX    = ".ko.srt" 
MAX_RETRY = 3
LANGS = [\
        ['Korean','translated from Korean'], \
        ['English','translated from English']]


# TODO: Plex 연동 및 메타 새로고침 처리
PlexUrl='http://127.0.0.1:32400'
PlexToken='--------------------'
UA = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36'

FLIST = list()
SLIST = list()
TLIST = dict()

def get_response(url):
    for i in range(1, MAX_RETRY + 1):
        r = requests.get(url)
        if r.status_code == 200 and len(r.text) > 1024: break

    if i == MAX_RETRY:
        print "failed to get response(url:%s)" % url
        return None

    return r
def is_sub(fname):
    fpath, ext = os.path.splitext(fname)
    if ext in SUBS: return True
    return False

def load_flist(path):
    for f in os.listdir(path):
        fpath = os.path.join(path, f)

        if os.path.isdir(fpath): load_flist(fpath)

        if is_sub(fpath):
            SLIST.append(fpath)
            continue

        if os.path.isdir(fpath) is False:
            print "FPATH: %s" % fpath
            FLIST.append(fpath)

def parse_fname(fname):
    fpath, ext = os.path.splitext(fname)

    name  = fpath[fpath.rfind('/')+1:]
    fpath = fpath[:fpath.rfind('/')+1]

    if name.find(" [") > 0: key = name[:name.find('[')]
    else: key = name

    # XXXX-123cdx 처리 -> XXXX-123
    r = re.compile("cd[0-9]", re.I).search(key)
    if r is not None: key = key[:r.start()]

    return key.strip(), fpath, name, ext

def exist_sub(keyword):
    for sub in SLIST:
        fname = sub[sub.rfind('/')+1:]
        if fname.find(" [") > 0: fname = fname[:fname.find(' [')+1]
        regex = re.compile(fname, re.I)
        if regex.search(keyword) is not None:
            return True
    return False

def prepare_tlist():
    for f in FLIST:
        #print "filename(%s)" % f
        keyword, path, fname, ext = parse_fname(f)

        # 자막파일이 있는 경우 처리
        if exist_sub(f):
            print "sub file aleady exist: remove from target(%s)" % keyword
            if keyword in TLIST: del TLIST[keyword]
            continue
        # 동일품번이 이미 대상목록에 있는 경우
        elif keyword in TLIST:
            print "aleady in target(%s)" % keyword
            continue
        else:
            print "add to target(%s: %s, %s, %s)" % (keyword, path, fname, ext)
            TLIST[keyword] = [path, fname, ext]

    return len(TLIST)

def down_sub(key, url):
    path, name, ext = TLIST[key]

    r = get_response(url)
    if r is None:
        print 'failed to download subfile(key:%s, url:%s)' %(key, url)
        return False
    
    fname = name + SUBFIX
    tmp_f = os.path.join(TMPDIR, fname)
    dst_f = os.path.join(path, fname)

    print "download sub to: %s" % tmp_f
    f = open(tmp_f, mode='wb')
    f.write(r.text.encode('utf-8'))
    f.close()

    print "move     sub to: %s" % dst_f
    shutil.move(tmp_f, dst_f)
    return True

def get_suburl(key):
    url = BASEURL + SEARCH_URL.format(keyword=key)

    print "try to search sublist (%s), url(%s)" % (key, url)
    r = get_response(url)
    if r is None:
        print 'failed to get sublist(key:%s, url:%s)' %(key, url)
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    tab  = soup.find('table', {'class':'table table_index table-hover'})
    if tab.find('td') is None: 
        print 'sub file does not exist(key:%s)' % key
        return None

    trs = tab.find_all('tr')
    for item in LANGS:
        found= False
        lang = item[0]
        regx = re.compile(item[1], re.I)

        print "search for lang(%s)" % lang
        for tr in trs:
            if tr.find('td') is None: continue
            #print "tr: (%s)" % tr

            rx = regx.search(tr.td.text)
            if rx is None: 
                print 'not found subfile for target lang(key:%s, lang:%s)' % (key, lang)
                continue

            print 'found subfile for target lang(key:%s, lang:%s)' % (key, lang)
            found = True
            break

        if found is True:
            uri = tr.td.a['href']
            sublisturl = BASEURL + uri
            enc_uri = uri[uri.rfind('/')+1:uri.rfind('.')]

            r = get_response(sublisturl)
            if r is None:
                print 'failed to get sublist url(key:%s, url:%s)' %(key, sublisturl)
                return False

            soup = BeautifulSoup(r.text, "html.parser")
            # TODO:멀티언어처리
            tdsub = soup.find('td', text='Korean')
            
            if tdsub.parent.find('button') is not None:
                print 'failed to get subfile url'
                return None

            tmpurl = tdsub.find_next('td').a['href']
            suburl = BASEURL + tmpurl[:tmpurl.rfind('/')+1] + enc_uri + tmpurl[tmpurl.rfind('-'):]
            return suburl

    return None

# MAIN
print "load file list..."
load_flist(LIB_PATH)

print "prepare target file list..."
total = prepare_tlist()
curr  = 0

for key, item in TLIST.items():
    curr = curr + 1

    print '[INFO] curr target(%s), current/total(%d/%d)' % (key, curr, total)
    suburl = get_suburl(key)

    if suburl is None:
        print "failed to find subfile(key: %s)" % key
        continue

    print "found sub(url:%s) try to download" % (suburl)
    found = down_sub(key, suburl)
