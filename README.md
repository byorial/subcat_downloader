# subcat_downloader
subtitilecat (AV)자막 다운로더

# 기본기능
SJVA에 의해 처리된 파일 - 품번 [원본파일명] 형태의 영상파일의 자막을 검색하여 subtitlecat에서 자동 다운로드 
다운로드는 일단 한국어 자막파일만 대상으로 함

# 사용자 설정값
```
LIB_PATH  = "/mnt/gdrive/labels/S1/SSNI"  # 라이브러리 경로: 상위폴더 지정시 하위까지 검색함
TMPDIR  = "/opt/work/subs/download"       # 자막 다운로드 임시경로 
MV2LIB = True                             # 다운된 자막파일을 LIB경로로 이동할지 여부(False의 경우 임시 경로로만 다운로드)
SUBS = [".srt", ".smi"]                   # 자막파일로 인식할 파일(이미 자막이 있는 경우 SKIP처리 대상)
SUBFIX    = ".ko.srt"                     # 자막파일 SUBFIX
MAX_RETRY = 3                             # 자막파일 다운로드 시도 횟수
# 다운로드 대상 자막 언어: 원본이 한국어인 경우 -> 영어인경우 순서로 찾음
LANGS = [['Korean','translated from Korean'], \
        ['English','translated from English']]
JOBFPATH = '/opt/work/subs/.joblist.json' # 작업내역 기록 파일

# for Plex
PLEX_PATH_RULE = ['/mnt/gdrive', '/mnt/gdrive']	 # Plex 경로변환
PlexUrl  ='http://127.0.0.1:32400'		 # Plex URL
PlexToken='--------------------'		 # Plex token(스크립트로 실행시 사용'
```
