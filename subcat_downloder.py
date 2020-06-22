# -*- coding: utf-8 -*-
#!/usr/bin/env python
import sys
if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf-8')
logger = None
import os, traceback
import shutil
import re
import requests
import urllib
import json

try:
    from bs4 import BeautifulSoup
except ImportError as e:
    os.system('pip install bs4')
    from bs4 import BeautifulSoup

BASEURL     = "https://www.subtitlecat.com/"
SEARCH_URL  = "index.php?search={keyword}"

LIB_PATH  = "/mnt/gdrive/labels/S1/SNIS"
TMPDIR  = "/opt/work/subs/download"
MV2LIB = True
SUBS = [".srt", ".smi"]
SUBFIX    = ".ko.srt" 
MAX_RETRY = 3
LANGS = [\
        ['Korean','translated from Korean'], \
        ['English','translated from English']]

FORCEALL = False
JOBFPATH = '/opt/work/subs/.joblist.json'
JOBLIST  = dict()   # 검색진행 목록

# Plex관련 설정
PLEX_PATH_RULE = ['/mnt/gdrive', '/mnt/gdrive']
# ['스크립트 동작서버상의경로', '플렉스서버상의 경로']
#PLEX_PATH_RULE = ['/mnt/gdrive', 'P:']

PlexUrl  ='http://127.0.0.1:32400'
PlexToken='____________________'
Sections = dict()
MediaSoup= dict()


FLIST = list()      # 대상파일 목록: 전체
SLIST = list()      # 자막파일 목록
TLIST = dict()      # 대상파일 목록: 전체 - 자막있는것
DLIST = dict()      # 자막 다운로드 한 목록

def get_response(url):
    for i in range(1, MAX_RETRY + 1):
        try:
            r = requests.get(url)
            if r.status_code == 200 and len(r.text) > 1024: break
        except:
            log('error accured(url:%s)' % url)
            return None

    if i == MAX_RETRY:
        log('failed to get response(url:%s)' % url)
        return None

    return r

def is_sub(fname):
    fpath, ext = os.path.splitext(fname)
    if ext in SUBS: return True
    return False

def load_joblist():
    global JOBLIST

    if os.path.isfile(JOBFPATH):
        with open(JOBFPATH, 'r') as f:
            try:
                JOBLIST = json.load(f)
            except ValueError:
                print 'no data to load(path:%s)' % JOBFPATH
                return 0
        f.close()
        return len(JOBLIST)
    return 0

def save_job():
    global JOBLIST
    if os.path.isfile(JOBFPATH):
        with open(JOBFPATH, 'w+') as f:
            try:
                dic = json.load(f)
                dic.update(JOBLIST)
                JOBLIST = dic
                f.write(json.dump(dic, indent=2))
            except ValueError:
                f.write(json.dump(JOBLIST, indent=2))
    else:
        with open(JOBFPATH, 'w+') as f:
            f.write(json.dump(JOBLIST, indent=2))

    #log('----------------------------")
    #print JOBLIST
    #log('----------------------------")
    f.close()

def add_joblist(key, url, status):
    global JOBLIST
    if status is None:
        JOBLIST.update({key:[url, 0]})
    else:
        JOBLIST.update({key:[url, status.status_code]})
    save_job()

def is_already_search(key):
    global JOBLIST
    try:
        val = JOBLIST[key]
        return True
    except KeyError:
        return False

def load_flist(path):
    for f in os.listdir(path):
        fpath = os.path.join(path, f)

        if os.path.isdir(fpath): load_flist(fpath)

        if is_sub(fpath):
            #log('SPATH: %s' % fpath)
            SLIST.append(fpath)
            continue
        elif os.path.isfile(fpath):
            #log('FPATH: %s' % fpath)
            FLIST.append(fpath)

    return len(FLIST)

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
        if fname.find(" [") > 0: fname = fname[:fname.find(' [')]
        regex = re.compile(fname, re.I)
        if regex.search(keyword) is not None:
            return True
    return False

def prepare_tlist():
    skip_cnt = acnt = bcnt = ccnt = 0
    for f in FLIST:
        #log('filename(%s)' % f)
        keyword, path, fname, ext = parse_fname(f)

        # 동일품번이 이미 대상목록에 있는 경우
        if keyword in TLIST:
            #log('aleady in target(%s)' % keyword)
            acnt = acnt + 1
            continue
        # 자막파일이 있는 경우 처리
        elif exist_sub(f):
            #log('sub file aleady exist: remove from target(%s)' % keyword)
            if keyword in TLIST: del TLIST[keyword]
            bcnt = bcnt + 1
            continue
        elif is_already_search(keyword):
            #log('already searched(key: %s)' % keyword)
            ccnt = ccnt + 1
            continue

        log('add to target(%s: %s, %s, %s)' % (keyword, path, fname, ext))
        TLIST[keyword] = [path, fname, ext]

    skip_cnt = acnt + bcnt + ccnt
    log('skipped files count(%d): dup(%d), exist sub(%d), already searched(%d)' % (skip_cnt, acnt, bcnt, ccnt))
    return len(TLIST)

def get_plex_path(fpath):
    ret = fpath.replace(PLEX_PATH_RULE[0], PLEX_PATH_RULE[1])
    ret = ret.replace('\\', '/') if PLEX_PATH_RULE[1][0] == '/' else ret.replace('/', '\\')
    return ret

def add_to_dlist(key, fpath):
    try:
        DLIST[key] = fpath
    except Exception as e:
        print 'Exception: %s' % e

def down_sub(key, url):
    path, name, ext = TLIST[key]

    r = get_response(url)
    if r is None:
        print 'failed to download subfile(key:%s, url:%s)' %(key, url)
        return False
    
    fname = name + SUBFIX
    tmp_f = os.path.join(TMPDIR, fname)
    dst_f = os.path.join(path, fname)
    video_fpath = os.path.join(path, name + ext)

    log('download sub to: %s' % tmp_f)
    f = open(tmp_f, mode='wb')
    f.write(r.text.encode('utf-8'))
    f.close()
    add_to_dlist(key, video_fpath)
    
    if MV2LIB is True:
        log('move     sub to: %s' % dst_f)
        shutil.move(tmp_f, dst_f)

        # refresh metadata
        if logger is not None:
            try:
                import threading, time, plex
                def func():
                    for i in range(5):
                        time.sleep(60)
                        if plex.LogicNormal.os_path_exists(get_plex_path(dst_f)):
                            plex.LogicNormal.metadata_refresh(filepath=get_plex_path(video_fpath))
                            break
                t = threading.Thread(target=func, args=())
                t.setDaemon(True)
                t.start()
            except Exception as e:
                print('Exception: %s', e)
                print(traceback.format_exc())

    return True

def get_suburl(key):
    url = BASEURL + SEARCH_URL.format(keyword=key)
    log('try to search sublist (%s), url(%s)' % (key, url))
    r = get_response(url)
    add_joblist(key, url, r)

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

        log('search for lang(%s)' % lang)
        for tr in trs:
            if tr.find('td') is None: continue
            #log('tr: (%s)' % tr)

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

def load_sections():
    surl = '/library/sections/?X-Plex-Token={token}'.format(token=PlexToken)
    url = PlexUrl + surl
    r = get_response(url)

    if r is None: return None

    soup = BeautifulSoup(r.text, "html.parser")
    dirs = soup.find_all('directory')

    for directory in dirs:
        section_id = directory['key']
        for location in directory.find_all('location'):
            Sections[location['path']] = section_id

    return len(Sections)
    
def get_section_id(fpath):
    global Sections

    for path in Sections.keys():
        regx = re.compile(path, re.I)
        ret  = regx.search(fpath)
        #log('PATH: (%s), FPATH(%s)' % (path, fpath))
        if ret is not None:
            return Sections[path]
    return None

def get_metakey(section_id, fpath):
    global MediaSoup
    murl = '/library/sections/{section_id}/all?X-Plex-Token={token}'.format(section_id=section_id, token=PlexToken)
    url = PlexUrl + murl

    try:
        soup = MediaSoup[section_id]
    except KeyError:
        r = get_response(url)
        soup = BeautifulSoup(r.text, "html.parser")
        MediaSoup[section_id] = soup

    part = soup.find('part', {'file':fpath})
    if part is not None:
        return part.parent.parent['key']
    
    return None

def update_meta_by_key(metakey):
    url = PlexUrl + metakey + '/refresh?X-Plex-Token={token}'.format(token=PlexToken)

    for i in range(1, MAX_RETRY + 1):
        try:
            log('metadata refresh url(%s)' % url)
            r = requests.put(url)
            if r.status_code == 200: 
                print 'successed to refresh meta(key: %s)' % metakey
                break
        except:
            print 'error accured to refresh meta(key: %s)' % metakey
            return None

    if i == MAX_RETRY:
        print 'failed to refresh meta(key: %s, ret:%d)' % (metakey, r.status_code)
        return None

    return r

def update_metadata():
    if load_sections() is None:
        print 'failed to load sections'
        return

    for key, fpath in DLIST.items():
        print 'try to refresh meta(file:%s)' % fpath

        plex_fpath = get_plex_path(fpath)
        section_id = get_section_id(plex_fpath)

        if section_id is None: 
            print 'failed to get section_id(path:%s)' % fpath
            continue

        metakey = get_metakey(section_id, plex_fpath)
        if metakey is None:
            print 'failed to get metadata(path:%s)' % fpath
            continue

        update_meta_by_key(metakey)

def log(*args):
    global logger
    try:
        if logger is not None:
            logger.debug(*args)
        if len(args) > 1:
            print(args[0] % tuple([str(x) for x in args[1:]]))
        else:
            print(str(args[0]))
        sys.stdout.flush()
    except Exception as e:
        log('Exception %s', e)
        log(traceback.format_exc())

def run(args):
    # MAIN
    job_cnt = load_joblist()
    log('load job list...(count: %d)' % job_cnt)

    flist_cnt = load_flist(LIB_PATH)
    log('load file list...(count: %d)' % flist_cnt)

    total = prepare_tlist()
    log('prepare target file list...(count: %d)' % total)
    curr  = 0

    for key, item in TLIST.items():
        curr = curr + 1
        print '[INFO] curr target(%s), current/total(%d/%d)' % (key, curr, total)

        suburl = get_suburl(key)
    
        if suburl is None:
            log('failed to find subfile(key: %s)' % key)
            continue
    
        log('found sub(url:%s) try to download' % (suburl))
        found = down_sub(key, suburl)

    # 메타 업데이트 처리: 스크립트시
    if logger is None and MV2LIB is True:
        update_metadata()

    log('[INFO] total target(%d), downloaded(%d)' % (total, len(DLIST)))

def main(*args, **kwargs):
    global logger
    if 'forceall' in kwargs:
        FORCEALL = True

    if 'logger' in kwargs:
        logger = kwargs['logger']
        log('=========== SCRIPT START ===========')
        run(args)
        log('=========== SCRIPT END ===========')
    else:
        run(args)

if __name__ == "__main__":
    main()
