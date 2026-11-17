#!/usr/bin/env python3
"""Publish a tested panel fix, preserving the original RC7 firmware assets."""
import hashlib,json,os,pathlib,shutil,subprocess,tempfile
REPO='MusMat17/openwrt_lt500-v2';TAG='lt500-rc7-warp-state-fix';CHANNEL='lt500-panel-lite'
root=pathlib.Path('tmp/warp-state-fix');out=root/'release';out.mkdir(exist_ok=True)
pkg=root/'zapret-manager-lt500_5.064-3_mipsel_24kc.ipk'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gh(*args):return subprocess.check_output(['gh',*map(str,args)],text=True)
shutil.copyfile(pkg,out/pkg.name)
notes=pathlib.Path('docs/LT500v2-WARP-state-fix-RU.md');shutil.copyfile(notes,out/'INSTALL-WARP-FIX-RU.md')
manifest={'format':1,'board':'cudy,lt500-v2','capability':'awg2-i1-tun-steer214-panel5-lite','version':'5.064-3','file':pkg.name,'sha256':sha(pkg)}
(out/'lt500-panel.json').write_text(json.dumps(manifest,indent=2)+'\n')
info={'build_commit':os.environ['GITHUB_SHA'],'base_panel':'5.064-2','panel':'5.064-3','kind':'panel-only','kernel_and_modules':'unchanged','tests':['RC7 failure reproduced','setup and fresh-process detection','all 3 tunnels','orphan cleanup','foreign interfaces retained','delta install and failure rollback','actual image MIPS opkg'],'live_router_test':False}
(out/'BUILD-INFO.json').write_text(json.dumps(info,indent=2)+'\n')
(out/'WARP-FIX-SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='WARP-FIX-SHA256SUMS'))
files=sorted(p for p in out.iterdir() if p.is_file());assert len(files)==5
def release(tag):return next((r for r in json.loads(gh('api','repos/'+REPO+'/releases?per_page=100')) if r['tag_name']==tag),None)
def verify(tag,paths):
 r=release(tag);assets={a['name']:a for a in r['assets']}
 for p in paths:
  a=assets[p.name];data=subprocess.check_output(['gh','api',f"repos/{REPO}/releases/assets/{a['id']}",'-H','Accept: application/octet-stream'])
  assert len(data)==p.stat().st_size==a['size'] and hashlib.sha256(data).hexdigest()==sha(p),p.name
 print('Remote bytes verified:',tag,flush=True)
 return r
if not release(TAG):gh('release','create',TAG,'--target',os.environ['GITHUB_SHA'],'--title','LT500v2 RC7 — WARP state fix — Zapret Manager 5.064-3','--notes-file',notes,'--draft','--prerelease',*files)
r=verify(TAG,files)
if r['draft']:gh('api','--method','PATCH',f"repos/{REPO}/releases/{r['id']}",'-F','draft=false','-F','prerelease=true','-f','make_latest=false')
verify(TAG,files)
# Only advance the compatible panel channel. Never replace RC7's immutable image/ZIP.
channel=release(CHANNEL);assert channel and not channel['draft']
with tempfile.TemporaryDirectory() as td:
 gh('release','download',CHANNEL,'--pattern','lt500-panel.json','--dir',td)
 prior=json.loads((pathlib.Path(td)/'lt500-panel.json').read_text())
 assert prior['capability']==manifest['capability'] and prior['version'] in ('5.064-2','5.064-3')
 if prior['version']=='5.064-3':assert prior==manifest,'Do not overwrite a different package with the same version'
 assets={a['name']:a for a in channel['assets']}
 if pkg.name not in assets:gh('release','upload',CHANNEL,out/pkg.name)
 else:verify(CHANNEL,[out/pkg.name])
 verify(CHANNEL,[out/pkg.name])
 gh('release','upload',CHANNEL,out/'lt500-panel.json','--clobber')
verify(CHANNEL,[out/pkg.name,out/'lt500-panel.json'])
rc7=release('v2.0-zapret-rc7');assert rc7 and any(a['name'].endswith('RC7-zapret-bundle.zip') for a in rc7['assets'])
notice='> WARP в RC7: доступно исправление панели [5.064-3](https://github.com/'+REPO+'/releases/tag/'+TAG+'). После установки исходного RC7 обновите панель; перепрошивка не требуется.\n\n'
if TAG not in (rc7.get('body') or ''):
 n=root/'rc7-notice.md';n.write_text(notice+(rc7.get('body') or ''))
 gh('release','edit','v2.0-zapret-rc7','--notes-file',n)
print('Published panel-only WARP fix; original RC7 image and earlier releases retained',flush=True)
print(sha(pkg)+'  '+pkg.name,flush=True)
