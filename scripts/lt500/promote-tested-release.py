import hashlib,json,pathlib,subprocess,tempfile
REPO='MusMat17/openwrt_lt500-v2'
TAG='v2.0-zapret-rc8'
OLD={'v2.0-zapret-rc1':405846999,'v2.0-zapret-rc2':407777224,'v2.0-zapret-rc4':432245169,'v2.0-zapret-rc5':443481400,'v2.0-zapret-rc6':444451372,'v2.0-zapret-rc7':448038830,'lt500-rc7-warp-state-fix':448116689}
def gh(*args):return subprocess.check_output(['gh',*map(str,args)],text=True)
def releases():return json.loads(gh('api','repos/'+REPO+'/releases?per_page=100'))
before=releases();r=next(x for x in before if x['tag_name']==TAG);assert r['id']==448575233 and not r['draft']
assets={(a['id'],a['name'],a['size'],a.get('digest')) for a in r['assets']};assert len(assets)==13
protected={x['id'] for x in before if x['tag_name'] not in OLD and x['tag_name']!=TAG}
with tempfile.TemporaryDirectory() as td:
 path=pathlib.Path(td)
 zipname='LT500v2-OpenWrt-23.05.5-RC8-zapret-bundle.zip'
 gh('release','download',TAG,'--repo',REPO,'--pattern',zipname,'--dir',path)
 assert hashlib.sha256((path/zipname).read_bytes()).hexdigest()=='f9ef8c5723e531e50c67f701718cdc5bf8724943907b8503c662dd13b95bf63e'
 body=r['body'].replace('# Cudy LT500v2 — OpenWrt 23.05.5 — RC8','# Cudy LT500v2 — OpenWrt 23.05.5 — v2.0-stable')
 body=body.replace('Предварительный релиз для проверки на устройстве.','Стабильный релиз. Работа сборки подтверждена владельцем Cudy LT500 v2 17.11.2026.')
 body=body.replace('Холодный запуск и реальный трафик на вашем устройстве пока не проверены.','Пользовательская проверка устройства выполнена после автоматических проверок сборки.')
 body=body.replace('RC7, RC6 и отдельный WARP fix сохранены для отката.','Предыдущие RC-релизы удалены по запросу владельца.')
 notes=path/'stable-notes.md';notes.write_text(body)
 gh('release','edit',TAG,'--repo',REPO,'--title','Cudy LT500v2 — OpenWrt 23.05.5 — v2.0-stable','--notes-file',notes,'--prerelease=false','--latest')
stable=next(x for x in releases() if x['tag_name']==TAG)
assert not stable['prerelease'] and not stable['draft']
assert {(a['id'],a['name'],a['size'],a.get('digest')) for a in stable['assets']}==assets
assert json.loads(gh('api','repos/'+REPO+'/releases/latest'))['id']==stable['id']
for tag,ident in OLD.items():
 item=next((x for x in releases() if x['tag_name']==tag),None)
 if item is None:continue
 assert item['id']==ident and item['prerelease'] and not item['draft']
 gh('release','delete',tag,'--repo',REPO,'--yes')
 print('Deleted release: '+tag,flush=True)
after=releases();assert not any(x['tag_name'] in OLD for x in after)
assert protected.issubset({x['id'] for x in after})
print('Promoted checked RC8 to v2.0-stable/latest, kept all 13 assets unchanged; removed 7 old RC releases; v1.0-stable and every panel update channel retained',flush=True)
print(stable['html_url'],flush=True)
