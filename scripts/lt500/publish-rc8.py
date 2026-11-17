#!/usr/bin/env python3
"""Publish the checked RC8 build and verify every remote asset."""
import hashlib,json,os,pathlib,subprocess,tempfile
REPO='MusMat17/openwrt_lt500-v2';TAG='v2.0-zapret-rc8';ROOT=pathlib.Path('bin/targets/ramips/mt76x8/release').resolve()
def gh(*a):return subprocess.check_output(['gh',*map(str,a)],text=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
info=json.loads((ROOT/'BUILD-INFO.json').read_text());assert info['build_commit']==os.environ['GITHUB_SHA']
assert info['manager']['ready_in_squashfs'] and info['validation']['low_space_firstboot'] and info['validation']['squashfs_roundtrip']
files=sorted(p for p in ROOT.iterdir() if p.is_file());assert len(files)==13,[p.name for p in files]
for line in (ROOT/'SHA256SUMS').read_text().splitlines():
 d,n=line.split('  ',1);assert pathlib.Path(n).name==n and sha(ROOT/n)==d
def release(tag):return next((r for r in json.loads(gh('api','repos/'+REPO+'/releases?per_page=100')) if r['tag_name']==tag),None)
if not release(TAG):gh('release','create',TAG,'--target',info['build_commit'],'--title','Cudy LT500v2 — OpenWrt 23.05.5 — v2.0-zapret-rc8','--notes-file',ROOT/'INSTALL-RC8.md','--draft','--prerelease',*files)
def verify():
 r=release(TAG);assets={a['name']:a for a in r['assets']};assert set(assets)=={p.name for p in files}
 for p in files:
  a=assets[p.name];body=subprocess.check_output(['gh','api',f"repos/{REPO}/releases/assets/{a['id']}",'-H','Accept: application/octet-stream'])
  assert len(body)==p.stat().st_size==a['size'] and hashlib.sha256(body).hexdigest()==sha(p),p.name
 print('All 13 remote RC8 assets match the tested build',flush=True)
 return r
r=verify()
if r['draft']:gh('api','--method','PATCH',f"repos/{REPO}/releases/{r['id']}",'-F','draft=false','-F','prerelease=true','-f','make_latest=false')
assert not release(TAG)['draft'];verify()
with tempfile.TemporaryDirectory() as td:
 gh('release','download','lt500-panel-lite','--pattern','lt500-panel.json','--dir',td)
 assert json.loads((pathlib.Path(td)/'lt500-panel.json').read_text())==json.loads((ROOT/'lt500-panel.json').read_text())
assert release('v2.0-zapret-rc7') and release('v2.0-zapret-rc6')
print('RC8 published; previous releases and compatible 5.064-3 panel channel retained',flush=True)
print('https://github.com/'+REPO+'/releases/tag/'+TAG,flush=True)
