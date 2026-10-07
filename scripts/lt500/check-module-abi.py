#!/usr/bin/env python3
"""Reject any rootfs module packaged against a foreign kernel ABI."""
import pathlib,re,subprocess,sys
root=pathlib.Path(sys.argv[1]); info=root/'usr/lib/opkg/info'
version=re.search(r'^Version: (.+)$',(info/'kernel.control').read_text(),re.M).group(1)
controls=list(info.glob('kmod-*.control'))
for p in controls:
    text=p.read_text()
    dep=re.search(r'kernel \(= ([^)]+)\)',text)
    assert dep and dep.group(1)==version, f'{p.name}: foreign kernel dependency'
for name in ('tun','amneziawg','udp_tunnel','ip6_udp_tunnel'):
    modules=list((root/'lib/modules').glob(f'*/{name}.ko'))
    assert len(modules)==1, f'Missing/duplicate {name}.ko'
    assert re.search(rb'vermagic=5\.15\.167 ',modules[0].read_bytes()), f'Wrong vermagic: {name}'
print(f'Validated {len(controls)} kernel packages: {version}')
