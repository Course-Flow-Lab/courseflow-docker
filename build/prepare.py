#!/usr/bin/env python3
"""Fetch only locked public source archives into an isolated build context."""
import argparse,hashlib,io,json,shutil,tarfile,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=root/'.build/context');args=p.parse_args()
lock=json.loads((root/'sources.lock.json').read_text());out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
hashes={}
for key,item in lock['components'].items():
    name='framework' if key=='framework' else 'courseflow-'+('chaoxing' if key=='cx' else key)
    dest=out/name
    if dest.exists():shutil.rmtree(dest)
    url='https://codeload.github.com/'+item['repository']+'/tar.gz/'+item['commit']
    data=urllib.request.urlopen(url,timeout=120).read();hashes[key]=hashlib.sha256(data).hexdigest()
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        members=tar.getmembers();prefix=members[0].name.split('/')[0]+'/'
        for member in members:
            if not member.name.startswith(prefix):continue
            member.name=member.name[len(prefix):]
            if member.name:tar.extract(member,dest,filter='data')
shutil.copytree(root/'build',out/'tools',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
for name in ['api.Dockerfile','web.Dockerfile','nginx.conf','test-source.mjs']:
    shutil.copy2(root/'build'/name,out/name)
shutil.copy2(root/'sources.lock.json',out/'sources.lock.json')
(out/'source-archives.json').write_text(json.dumps(hashes,indent=2)+'\n')
print(out)
