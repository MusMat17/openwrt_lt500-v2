#!/usr/bin/env python3
"""Materialize the pinned panel's literal payloads and cache keys in SquashFS."""
import hashlib,pathlib,re,sys
root=pathlib.Path(sys.argv[1]);source=(root/'usr/libexec/zapret-manager-installer').read_text()
assert '_st_warp_recover_if() {' in source
blocks={};target=None;buf=[]
for line in source.splitlines(keepends=True):
 if target is not None:
  if line.strip()=='ZM_INSTALLER_EOF':blocks[target]=''.join(buf);target=None;buf=[]
  else:buf.append(line)
 elif "<< 'ZM_INSTALLER_EOF'" in line:
  if line.startswith('sed '):target='/opt/zapret-manager-luci/backend.sh'
  else:
   m=re.match(r'''cat > ['"]([^'"]+)['"] <<''',line);assert m,line
   target=m[1].replace('$_zmi_st/','/opt/zapret-manager-luci/')
assert len(blocks)==57 and target is None
blocks['/usr/libexec/rpcd/zapret-manager']=blocks.pop('/opt/zapret-manager-luci/rpcd-plugin.zm-new')
build_id='1794873608' # stable RC8 asset cache key; independent of first-boot clock
files={}
for name,body in blocks.items():
 body=body.replace('@ZM_VERSION@','5.064').replace('__ZM_BUILD__',build_id).replace('__ZMW_BUILD__',build_id)
 mode=0o755 if name in ('/opt/zapret-manager-luci/backend.sh','/usr/libexec/rpcd/zapret-manager') else 0o644
 p=root/name.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body);p.chmod(mode);files[name.lstrip('/')]=mode
resources=sorted(n.removeprefix('/www/luci-static/resources/') for n in blocks if n.startswith('/www/luci-static/resources/') and n.endswith(('.js','.css')))
p=root/'www/luci-static/resources/zapret-manager/build.txt';p.write_text(build_id+'\n'+'\n'.join(resources)+'\n');p.chmod(0o644);files[str(p.relative_to(root))]=0o644
for name in ('zms','zmw'):
 p=root/'usr/bin'/name;p.write_text('#!/bin/sh\nexec /usr/libexec/lt500-panel-apply "$@"\n');p.chmod(0o755);files[str(p.relative_to(root))]=0o755
support=root/'usr/share/lt500';support.mkdir(parents=True,exist_ok=True)
installer_hash=hashlib.sha256((root/'usr/libexec/zapret-manager-installer').read_bytes()).hexdigest()
(support/'panel-installer.sha256').write_text(installer_hash+'\n')
# A disabled Web UI deliberately hides this one HTML file. Keep it out of repair.
manifest=''.join(hashlib.sha256((root/name).read_bytes()).hexdigest()+f' {mode:o} '+name+'\n' for name,mode in sorted(files.items()) if name!='www/zm-webui.html')
(support/'panel-rom.files').write_text(manifest)
for p in (support/'panel-installer.sha256',support/'panel-rom.files'):p.chmod(0o644)
print('Preinstalled',len(blocks),'panel payloads plus cache index and CLI wrappers; ROM manifest entries:',len(manifest.splitlines()))
