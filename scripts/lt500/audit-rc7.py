import hashlib,io,json,pathlib,re,tarfile,urllib.request,zipfile
work=pathlib.Path('tmp/rc7-audit'); work.mkdir(parents=True,exist_ok=True)
bundle=work/'RC6.zip'
urllib.request.urlretrieve('https://github.com/MusMat17/openwrt_lt500-v2/releases/download/v2.0-zapret-rc6/LT500v2-OpenWrt-23.05.5-RC6-zapret-bundle.zip',bundle)
assert hashlib.sha256(bundle.read_bytes()).hexdigest()=='5a3d3a8e69cfe16bebf44fbf548e145396bf83b4bda7ac1ec2649f2f443154ce'
with zipfile.ZipFile(bundle) as z:
    for name in ['Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc6-sysupgrade.bin','zapret-manager-lt500_5.064-1_mipsel_24kc.ipk']:
        (work/name).write_bytes(z.read(name))
with tarfile.open(work/'zapret-manager-lt500_5.064-1_mipsel_24kc.ipk') as outer:
    member=next(m for m in outer if m.name.endswith('data.tar.gz'))
    with tarfile.open(fileobj=io.BytesIO(outer.extractfile(member).read())) as data:
        member=next(m for m in data if m.name.endswith('/usr/libexec/zapret-manager-installer'))
        source=data.extractfile(member).read().decode()
(work/'installer.sh').write_text(source)
blocks={}
target=None; lines=[]
for line in source.splitlines(keepends=True):
    if target is not None:
        if line.strip()=='ZM_INSTALLER_EOF':
            blocks[target]=''.join(lines)
            target=None;lines=[]
        else: lines.append(line)
    elif "<< 'ZM_INSTALLER_EOF'" in line:
        if line.startswith('sed '):target='/opt/zapret-manager-luci/backend.sh'
        else:
            m=re.search(r'''cat > ['"]([^'"]+)['"]''',line)
            assert m,line
            target=m[1].replace('$_zmi_st/','/opt/zapret-manager-luci/')
for name,body in blocks.items():
    out=work/'payloads'/name.lstrip('/');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(body)
selected=['/www/zm/app.js','/www/zm/app.css','/www/luci-static/resources/view/zapret-manager/style.css','/www/luci-static/resources/zapret-manager/common.js','/opt/zapret-manager-luci/backend.sh','/opt/zapret-manager-luci/mod/steer1.sh','/opt/zapret-manager-luci/mod/steer2.sh','/opt/zapret-manager-luci/mod/zapret.sh','/opt/zapret-manager-luci/mod/system.sh']
for name in selected:
    print('@@BEGIN '+name,flush=True);print(blocks[name],flush=True);print('@@END '+name,flush=True)
