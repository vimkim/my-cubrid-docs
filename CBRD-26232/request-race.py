#!/usr/bin/env python3
from pathlib import Path
import re, hashlib
import argparse, subprocess
parser = argparse.ArgumentParser(description='Extract the pinned PR8547 request code for a standalone race probe.')
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
src = args.source.resolve(strict=True)
out = args.output.resolve()
expected = '02bebe81790980ef8e3ffd7767a444d035603261'
actual = subprocess.check_output(['git', '-C', str(src), 'rev-parse', 'HEAD'], text=True).strip()
if actual != expected:
    raise SystemExit('Source HEAD must be ' + expected + ', got ' + actual)
if subprocess.run(['git', '-C', str(src), 'diff', '--quiet', 'HEAD', '--', 'src/storage/file_io.c', 'src/base/porting.h']).returncode:
    raise SystemExit('Production source files must match HEAD')
out.mkdir(parents=True, exist_ok=True)
f=(src/'src/storage/file_io.c').read_text()
p=(src/'src/base/porting.h').read_text()
def extract(text, pat):
    m=re.search(pat,text,re.M)
    if not m: raise ValueError(pat)
    a=m.start(); b=text.index('{',m.end()-1); depth=1; i=b+1
    while depth:
        if text[i]=='{': depth+=1
        elif text[i]=='}': depth-=1
        i+=1
    return text[a:i]
blocks=[]
for pat in [r'^struct fileio_volinfo\n',r'^typedef union fileio_apply_function_arg\n',r'^struct fileio_volinfo_header\n']:
    x=extract(f,pat)
    if pat.startswith('^typedef'): x+=' APPLY_ARG;'
    else: x+=';'
    blocks.append(x)
for name in ['INC','CAS','TAS']:
    blocks.append(extract(p,rf'^template <[^\n]*inline [^\n]*ATOMIC_{name}_32 '))
for ret,name in [(r'static FILEIO_VOLUME_INFO \*','fileio_find_volume_info_by_id'),('static void','fileio_start_writeback'),('bool','fileio_writeback_temp_pages'),('static bool','fileio_writeback_requested_volume')]:
    blocks.append(extract(f,rf'^{ret}\n{name} \('))
header=r'''
#define SERVER_MODE
#define HAVE_ATOMIC_BUILTINS
#include <atomic>
#include <cassert>
#include <cerrno>
#include <climits>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <pthread.h>
#include <thread>
#include <fcntl.h>
using UINT32=uint32_t;
using VOLID=short;
using THREAD_ENTRY=void;
using FILEIO_LOCKF_TYPE=int;
using FILEIO_VOLUME_INFO=struct fileio_volinfo;
using FILEIO_VOLUME_HEADER=struct fileio_volinfo_header;
#define FILEIO_VOLINFO_INCREMENT 32
#define NULL_VOLID -1
#define NULL_VOLDES -1
#define LOG_MAX_DBVOLID 32766
#define PRM_ID_TEMP_WRITEBACK_SIZE 1
#define ARG_FILE_LINE __FILE__,__LINE__
#define er_log_debug(...) ((void)0)
static int threshold=256;
static int prm_get_integer_value(int) { return threshold; }
static int hints=0;
static bool inject_mark=false;
static int probe_sync_file_range(int, long, long, unsigned);
#define sync_file_range probe_sync_file_range
'''
body='\n\n'.join(blocks)
# Declaration belongs before functions, after production structures.
pos=body.index('template <')
body=body[:pos]+'static FILEIO_VOLUME_HEADER fileio_Vol_info_header {};\n'+body[pos:]
main=r'''
static int probe_sync_file_range(int fd, long offset, long bytes, unsigned flags) {
  assert(fd==17 && offset==0 && bytes==0 && flags==SYNC_FILE_RANGE_WRITE);
  ++hints;
  if(inject_mark) { inject_mark=false; assert(fileio_writeback_temp_pages(nullptr,0,256,true)); }
  return 0;
}
int main(int argc,char**) {
  FILEIO_VOLUME_INFO chunk[32] {};
  FILEIO_VOLUME_INFO *chunks[]={chunk};
  chunk[0].vdes=17;
  fileio_Vol_info_header.volinfo=chunks;
  fileio_Vol_info_header.max_perm_vols=32;
  fileio_Vol_info_header.next_temp_volid=LOG_MAX_DBVOLID;
  fileio_Vol_info_header.num_volinfo_array=1;
  if(argc>1) {
    threshold=1;
    std::atomic<bool> go {false};
    std::thread producer([&] { while(!go.load()){}; for(int i=0;i<100000;i++) fileio_writeback_temp_pages(nullptr,0,1,true); });
    std::thread consumer([&] { go.store(true); APPLY_ARG a {}; for(int i=0;i<100000;i++) fileio_writeback_requested_volume(nullptr,&chunk[0],&a); });
    producer.join(); consumer.join();
    std::puts("concurrent flag read/write completed");
  } else {
    for(int i=0;i<255;i++) assert(!fileio_writeback_temp_pages(nullptr,0,1,true));
    assert(fileio_writeback_temp_pages(nullptr,0,1,true));
    assert(!fileio_writeback_temp_pages(nullptr,0,256,true));
    APPLY_ARG a {};
    inject_mark=true;
    fileio_writeback_requested_volume(nullptr,&chunk[0],&a);
    assert(a.vdes==1 && chunk[0].temp_writeback_requested==1);
    fileio_writeback_requested_volume(nullptr,&chunk[0],&a);
    assert(a.vdes==2 && chunk[0].temp_writeback_requested==0 && hints==2);
    fileio_writeback_requested_volume(nullptr,&chunk[0],&a);
    assert(a.vdes==2);
    std::puts("PASS: 256-page threshold, pending-request coalescing, producer mark during syscall preserved for next pass, empty pass terminates");
  }
}
'''
(out/'request_probe.cpp').write_text(header+body+main)
(out/'extraction.txt').write_text('Pinned file_io.c SHA256 '+hashlib.sha256(f.encode()).hexdigest()+'\nExact extracted production structs/functions; only type aliases, parameter getter and sync syscall boundary supplied by harness. Atomic templates extracted verbatim from pinned porting.h.\n')
