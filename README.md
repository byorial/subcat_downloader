# subcat_downloader
subtitilecat 자막 다운로더

# 사용자 설정값
```
LIB_PATH  = "/mnt/gdrive/labels/S1/SSNI"  # 라이브러리 경로: 상위폴더 지정시 하위까지 검색함
TMPDIR  = "/opt/work/subs/download"       # 자막 다운로드 임시경로 
SUBS = [".srt", ".smi"]                   # 자막파일로 인식할 파일(이미 자막이 있는 경우 SKIP처리 대상)
SUBFIX    = ".ko.srt"                     # 자막파일 SUBFIX
MAX_RETRY = 3                             # 자막파일 다운로드 시도 횟수
# 다운로드 대상 자막 언어: 원본이 한국어인 경우 -> 영어인경우 순서로 찾음
LANGS = [['Korean','translated from Korean'], \
        ['English','translated from English']]
```
