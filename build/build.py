#!/usr/bin/env python3
import argparse,json,os,subprocess,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--prefix',default='courseflow');p.add_argument('--version',default='dev');p.add_argument('--prepared',action='store_true');args=p.parse_args()
if not args.prepared:subprocess.run(['python3',str(root/'build/prepare.py')],check=True)
context=root/'.build/context';lock=json.loads((root/'sources.lock.json').read_text())
shutil.copytree(root/'build',context/'tools',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
for file in ['api.Dockerfile','web.Dockerfile','nginx.conf','test-source.mjs']:
    shutil.copy2(root/'build'/file,context/file)
env=dict(os.environ)
if subprocess.run(['docker','buildx','version'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:env['DOCKER_BUILDKIT']='0'
common=['docker','build','--platform',lock['platform']]
for k,v in lock['base_images'].items():common+=['--build-arg',k.upper()+'_IMAGE='+v]
for k,v in lock['components'].items():common+=['--build-arg',k.upper()+'_REVISION='+v['commit']]
common+=['--build-arg','RELEASE_VERSION='+args.version]
for target,name,file in [('test','api-tests','api.Dockerfile'),('runtime','api','api.Dockerfile'),(None,'webui','web.Dockerfile')]:
    cmd=common+['-t',args.prefix+'-'+name+':'+args.version,'-f',str(context/file)]
    if target:cmd+=['--target',target]
    subprocess.run(cmd+[str(context)],env=env,check=True)
(root/'.build/images.lock.env').write_text('API_IMAGE='+args.prefix+'-api:'+args.version+'\nWEB_IMAGE='+args.prefix+'-webui:'+args.version+'\n')
