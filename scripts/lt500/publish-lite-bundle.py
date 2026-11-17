#!/usr/bin/env python3
"""Publish only a previously successful RC7 build, verifying every remote byte."""
import hashlib,json,os,pathlib,subprocess
REPO='MusMat17/openwrt_lt500-v2';TAG='v2.0-zapret-rc7';CHANNEL='lt500-panel-lite'
ROOT=pathlib.Path('bin/targets/ramips/mt76x8/release').resolve()
def gh(*args):return subprocess.check_output(['gh',*map(str,args)],text=True)
info=json.loads((ROOT/'BUILD-INFO.json').read_text())
run=json.loads(gh('api','repos/'+REPO+'/actions/runs/'+os.environ['RC7_BUILD_RUN']))
assert run['conclusion']=='success' and run['head_branch']==TAG
assert run['name']=='LT500 RC7 - Lite panel, persistent WARP and offline Zapret startup'
assert run['head_sha']==info['build_commit'],'Artifact must match the successful build commit'
assert info['validation']['squashfs_roundtrip'] and info['validation']['abi']
assert info['kernel']=='5.15.167-1-fbed8e3c789296faf2510c36a7d42ced'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=sorted(p for p in ROOT.iterdir() if p.is_file());assert len(files)==13,[p.name for p in files]
for line in (ROOT/'SHA256SUMS').read_text().splitlines():
 digest,name=line.split('  ',1);assert pathlib.Path(name).name==name and sha(ROOT/name)==digest
line=(ROOT/'LT500v2-OpenWrt-23.05.5-RC7-zapret-bundle.zip.sha256').read_text().strip()
digest,name=line.split('  ',1);assert sha(ROOT/name)==digest
def release(tag):
 return next((r for r in json.loads(gh('api','repos/'+REPO+'/releases?per_page=100')) if r['tag_name']==tag),None)
def verify(tag,paths):
 r=release(tag);assert r
 assets={a['name']:a for a in r['assets']};assert set(assets)=={p.name for p in paths}
 for p in paths:
  a=assets[p.name]
  raw=subprocess.check_output(['gh','api',f"repos/{REPO}/releases/assets/{a['id']}",'-H','Accept: application/octet-stream'])
  assert len(raw)==p.stat().st_size==a['size'] and hashlib.sha256(raw).hexdigest()==sha(p),p.name
  if a.get('digest'):assert a['digest']=='sha256:'+sha(p),p.name
 print(f'Verified {tag}: all {len(paths)} remote assets match build bytes',flush=True)
 return r
def publish(tag,title,notes,paths):
 r=release(tag)
 if r is None:
  gh('release','create',tag,'--target',info['build_commit'],'--title',title,'--notes-file',notes,'--draft','--prerelease',*paths)
 r=verify(tag,paths)
 if r['draft']:gh('api','--method','PATCH',f"repos/{REPO}/releases/{r['id']}",'-F','draft=false','-F','prerelease=true','-f','make_latest=false')
 assert not release(tag)['draft'];verify(tag,paths)
publish(TAG,'Cudy LT500v2 — OpenWrt 23.05.5 — v2.0-zapret-rc7',ROOT/'INSTALL-RC7.md',files)
channel_notes=ROOT.parent/'panel-lite-notes.md'
channel_notes.write_text('Совместимый канал обновлений панели LT500 Lite для RC7. Zapret Manager 5.064-2: без радио, тем и анимаций; исправлено сохранение состояния WARP. Требуется capability awg2-i1-tun-steer214-panel5-lite. Образ прошивки и ядро здесь не обновляются.\n')
publish(CHANNEL,'LT500v2 — совместимые обновления Zapret Manager Lite',channel_notes,[ROOT/'lt500-panel.json',ROOT/'zapret-manager-lt500_5.064-2_mipsel_24kc.ipk'])
assert release('v2.0-zapret-rc6') and release('v2.0-zapret-rc5'),'Earlier releases must be retained'
print('Published RC7 and LT500 Lite panel channel. RC6 and RC5 retained.',flush=True)
print('https://github.com/'+REPO+'/releases/tag/'+TAG,flush=True)
