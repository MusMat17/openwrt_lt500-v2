#!/usr/bin/env python3
"""Regression: recovered WARP interfaces survive a fresh panel process."""
import pathlib,re,subprocess,sys,tempfile
source=pathlib.Path(sys.argv[1]).read_text()
def fn(name):
 m=re.search(r'^'+re.escape(name)+r'\(\) \{[\s\S]*?^\}',source,re.M)
 if m: return m.group()
 m=re.search(r'^'+re.escape(name)+r'\(\) \{.*\}$',source,re.M)
 assert m,name
 return m.group()
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)
 (p/'warp.conf').write_text('[Interface]\nPrivateKey = fixture-private\n[Peer]\nPublicKey = fixture-peer\n')
 (p/'network-key').write_text('fixture-private')
 body=fn('_st_warp_on')+r'''
_st_warp_ext() { return 1; }
_st_owns() { grep -qxF "$1" "$ST_OWNED" 2>/dev/null; }
_st_own() { mkdir -p "$ST_DIR"; grep -qxF "$1" "$ST_OWNED" 2>/dev/null || echo "$1" >> "$ST_OWNED"; }
uci() {
 case "$*" in
  *network.zmwarp.proto) echo amneziawg ;;
  *network.zmwarp.private_key) cat "$ST_DIR/network-key" ;;
  *network.zmwarp_peer.public_key) echo fixture-peer ;;
  *) return 1 ;;
 esac
}
_st_warp_on
'''
 env=f'ST_DIR="{p}"; ST_OWNED="$ST_DIR/owned"; ST_WARP_CONF="$ST_DIR/warp.conf"; ST_WARP_IF=zmwarp\n'
 def run(expected):
  r=subprocess.run(['sh','-c',env+body],capture_output=True,text=True)
  assert r.returncode==expected,(r.returncode,r.stderr)
 run(0)
 assert (p/'owned').read_text()=='net zmwarp\n'
 run(0) # fresh process / panel reload
 assert (p/'owned').read_text()=='net zmwarp\n'
 (p/'owned').unlink()
 (p/'network-key').write_text('foreign-private')
 run(1)
 assert not (p/'owned').exists()
 (p/'warp.conf').unlink()
 run(1)
 # No endpoint/exit: explicit tunnel-ready apply must fail, not report success.
 mocks=r'''
_st_tun_hook() { :; }; _st_cat_fresh() { return 0; }; _st_tch_on() { return 1; }
_st_sel() { echo youtube; }; _st_exit() { echo none; }; _st_work_main() { return 0; }
_st_secs_work() { return 1; }; _st_spec_clear() { :; }; _st_down() { :; }
_rb_say() { :; }; _rb_warn() { :; }
ST_RUN="'''+str(p)+r'''"; ST_CAT_OFF="$ST_RUN/off"; touch "$ST_CAT_OFF"
_st_apply0 tunnel_ready
'''
 r=subprocess.run(['sh','-c',fn('_st_apply0')+mocks],capture_output=True,text=True)
 assert r.returncode==1,(r.returncode,r.stderr)
print('WARP regression passed: persisted ownership, fresh-process detection, foreign key refusal, no false tunnel-ready success')
