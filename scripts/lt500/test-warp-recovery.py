#!/usr/bin/env python3
"""Reproduce partial ownership + stale cache using the actual panel functions."""
import base64, json, os, pathlib, re, shlex, subprocess, sys, tempfile

original = pathlib.Path(sys.argv[1]).read_text()
fixed = pathlib.Path(sys.argv[2]).read_text()
shell = shlex.split(os.environ.get('LT500_TEST_SHELL', 'sh'))
peer = 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo='
def key(n): return base64.b64encode(bytes([n])*32).decode()
def fn(source, name):
    lines=source.splitlines()
    candidates=[i for i,x in enumerate(lines) if x.startswith(name+'()')]
    i=next((i for i in candidates if not lines[i].endswith('}')),candidates[-1])
    if lines[i].endswith('}'):return lines[i]+'\n'
    j=next(j for j in range(i+1,len(lines)) if lines[j]=='}')
    return '\n'.join(lines[i:j+1])+'\n'
names=['_st_own','_st_owns','_st_warp_on','_st_warp_ext','_st_warp_own','_st_warp_field','_st_with','_st_wif','_st_wconf','_st_wifs_all','_st_wifs_auto','_st_wifs_every','_st_wnet','_st_warp_register','_st_warp_up','do_steer_warp_setup','_st_exit','_st_tunnels_json','do_steer_warp_remove']
def functions(source):
    parts=[fn(source,n) for n in names]
    if '_st_warp_recover_if() {' in source:
        parts += [fn(source,n) for n in ['_st_warp_recover_if','_st_warp_recover_all']]
    return '\n'.join(parts)

with tempfile.TemporaryDirectory() as directory:
    root=pathlib.Path(directory); state=root/'state'; state.mkdir(); runtime=root/'run';runtime.mkdir()
    db=root/'uci.json'; bindir=root/'bin';bindir.mkdir(); env=dict(os.environ,PATH=str(bindir)+':'+os.environ['PATH'])
    # Keys are synthetic. The UCI fixture implements just the actual get/set/delete calls.
    uci=bindir/'uci'
    uci.write_text('#!/usr/bin/env python3\n'+f'db={str(db)!r}\n'+'''import json,pathlib,sys
p=pathlib.Path(db);d=json.loads(p.read_text());a=[x for x in sys.argv[1:] if x not in ('-q','-X')];cmd=a.pop(0)
if cmd=='get':
 if a[0] not in d:sys.exit(1)
 print(d[a[0]])
elif cmd=='set':
 k,v=a[0].split('=',1);d[k]=v;p.write_text(json.dumps(d))
elif cmd=='delete':
 k=a[0];d={x:v for x,v in d.items() if x!=k and not x.startswith(k+'.')};p.write_text(json.dumps(d))
elif cmd in ('commit','revert'):pass
elif cmd=='show':
 for k,v in d.items():print(k+'='+repr(v))
else:raise RuntimeError(cmd)
''');uci.chmod(0o755)
    def reset():
        for p in state.iterdir():
            if p.is_file():p.unlink()
        d={}
        for n,wi in enumerate(['zmwarp','zmwarp2','zmwarp3'],1):
            d.update({f'network.{wi}':'interface',f'network.{wi}.proto':'amneziawg',f'network.{wi}.private_key':key(n),f'network.{wi}.addresses':'172.16.0.2/32',f'network.{wi}.mtu':'1280',f'network.{wi}.awg_i1':'fixture-mask',f'network.{wi}_peer':'amneziawg_'+wi,f'network.{wi}_peer.public_key':peer,f'network.{wi}_peer.description':'WARP '+('' if n==1 else str(n)),f'network.{wi}_peer.route_allowed_ips':'0',f'network.{wi}_peer.endpoint_host':'162.159.192.'+str(n),f'network.{wi}_peer.endpoint_port':'1701'})
            conf=state/('warp.conf' if n==1 else f'warp{n}.conf')
            # Only the second interface remains in the registry. First/third
            # cached keys were regenerated while old UCI interfaces survived.
            conf.write_text(f'[Interface]\nPrivateKey = {key(n if n==2 else n+10)}\n[Peer]\nPublicKey = {peer}\n');conf.chmod(0o600)
        db.write_text(json.dumps(d));(state/'owned').write_text('engine\nnet zmwarp2\n');(state/'exit').write_text('warp\n')
        (state/'warp.up').write_text('zmwarp HEL\nzmwarp2 HKG\nzmwarp3 HEL\n')
        return d
    globals=f'''ST_DIR={shlex.quote(str(state))}; ST_RUN={shlex.quote(str(runtime))}; JOBS_DIR="$ST_RUN"
ST_OWNED="$ST_DIR/owned"; ST_WARP_CONF="$ST_DIR/warp.conf"; ST_WARP_IF=zmwarp; ST_WIF1=zmwarp; ST_WCONF1="$ST_WARP_CONF"
ST_WARP_N=3; ST_WARP_MAX=3; ST_OWN_IF=zmwarp4; ST_WARP_UP="$ST_DIR/warp.up"; ST_MODE_RAW=auto; ST_WARP_ZONE=zmwarp
ST_STOP_FLAG="$ST_RUN/stop"; ST_OFF="$ST_DIR/stopped"; ST_EXIT="$ST_DIR/exit"; ST_SUB="$ST_DIR/sub.txt"; ST_SEC=""
ST_WARP_GEO="$ST_DIR/warp.geo"; ST_WARP_UP_AUTO="$ST_DIR/warp.up.auto"; ST_WARP_MODE="$ST_DIR/warp.mode"
ST_WARP_OWN="$ST_DIR/warp.own.conf"; ST_WARP_OWN_KEEP="$ST_DIR/keep.conf"; ST_WARP_PICK="$ST_DIR/warp.pick"; ST_WARP_ORDER="$ST_DIR/warp.order"
ST_TGWS_WARP="$ST_DIR/tgws"; ST_WARP_HS_WAIT=1
'''
    mocks='''
_st_phase() { :; }; _st_installed() { return 0; }; _st_blocker() { :; }; _ensure_deps() { :; }
_st_install_awg() { return 0; }; _st_warp_zone() { :; }; _st_stopped() { return 1; }
_st_warp_ready_if() { return 0; }; _st_warp_alive_if() { return 0; }; _st_colo_of() { echo HEL; }
_st_warp_is_ru() { return 1; }; _st_warp_order() { :; }; _st_tgws_warp() { :; }; _st_warp_geo() { :; }; _st_geo_line() { :; }
_st_warp_scan() { echo 'unexpected endpoint scan' >&2; return 1; }
_awg_keys_get() { echo 'unexpected key registration' >&2; return 1; }
_rb_say() { echo "$*"; }; _rb_warn() { echo "$*"; }; ubus() { :; }; ifdown() { echo "$1" >> "$ST_RUN/down"; }
_st_work() { return 0; }; _st_apply() { echo "apply:$(_st_exit)"; [ "$(_st_exit)" = warp ]; }; _st_selfcheck() { :; }
sleep() { :; }; esc() { printf '%s' "$1"; }; _st_wpeer() { echo "${1}_peer"; }; _st_geo_get() { :; }; _st_if_ru() { return 1; }
_st_ext_leave() { :; }; _st_peers_drop() { :; }; _st_secs() { :; }; _st_mode_vars() { :; }
_st_wfix_set() { :; }; _st_wfix_cron() { :; }; logger() { :; }
'''
    def run(source,cmd,ok=True):
        # Runtime init calls are mocked; UCI mutations remain real fixture writes.
        body=functions(source).replace('/etc/init.d/network reload',':').replace('/etc/init.d/firewall reload',':')
        p=subprocess.run([*shell,'-c',globals+body+mocks+cmd],env=env,text=True,capture_output=True)
        assert (p.returncode==0)==ok,(p.returncode,p.stdout,p.stderr)
        assert not p.stderr,p.stderr
        return p.stdout
    reset();run(original,'_st_warp_on',False)
    old=json.loads(db.read_text());run(fixed,'_st_warp_on')
    assert json.loads(db.read_text())==old,'Recovery must not change working UCI keys, addresses or endpoints'
    assert 'net zmwarp\n' in (state/'owned').read_text()
    # A separate process must see the repaired state, without a new WARP scan.
    assert run(fixed,'_st_exit').strip()=='warp'
    reset();text=run(original,'do_steer_warp_setup',False)
    assert 'состояние интерфейса не сохранено' in text
    reset();text=run(fixed,'do_steer_warp_setup')
    assert 'apply:warp' in text and 'Готово, WARP подключён' in text,text
    assert set((state/'owned').read_text().splitlines())=={'engine','net zmwarp','net zmwarp2','net zmwarp3'}
    tunnels=json.loads(run(fixed,'_st_tunnels_json'));assert len(tunnels)==3,tunnels
    for n in (1,2,3):
        p=state/('warp.conf' if n==1 else f'warp{n}.conf')
        assert 'PrivateKey = '+key(n) in p.read_text()
        assert p.stat().st_mode & 0o777 == 0o600
    # Deletion used to remove only #2; all manager-generated interfaces are now removed.
    reset();run(original,'_st_work() { return 1; }; do_steer_warp_remove')
    assert 'network.zmwarp' in json.loads(db.read_text()) and 'network.zmwarp3' in json.loads(db.read_text())
    reset();run(fixed,'_st_work() { return 1; }; do_steer_warp_remove')
    assert not any(k.startswith('network.zmwarp') for k in json.loads(db.read_text()))
    # Same reserved name, but a foreign key/description/routing mode is not adopted or removed.
    for field,value in [('public_key',key(9)),('description','My server'),('route_allowed_ips','1')]:
        reset();d=json.loads(db.read_text());d['network.zmwarp_peer.'+field]=value;db.write_text(json.dumps(d))
        run(fixed,'_st_warp_on',False)
        assert 'net zmwarp\n' not in (state/'owned').read_text()
        run(fixed,'_st_work() { return 1; }; do_steer_warp_remove')
        assert 'network.zmwarp' in json.loads(db.read_text())
    # Missing cache after an old removal is restored from the still configured interface.
    reset();(state/'warp.conf').unlink();run(fixed,'_st_warp_on');assert (state/'warp.conf').exists()
    run(fixed,'_st_warp_on');assert (state/'owned').read_text().count('net zmwarp\n')==1
print('Reproduced RC7 setup failure and removal of only zmwarp2; fixed setup, fresh status, 3 tunnels, full cleanup, missing cache and foreign-interface refusal')
