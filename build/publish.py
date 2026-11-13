#!/usr/bin/env python3
"""Publish tested local images, digest locks, and online/offline release bundles."""
import gzip,hashlib,json,os,re,shutil,subprocess,sys,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
version=sys.argv[1];assert re.fullmatch(r'v\d+\.\d+\.\d+',version)
repo=os.environ.get('GITHUB_REPOSITORY','Course-Flow-Lab/courseflow-docker');registry='ghcr.io/'+repo.split('/')[0].lower()
existing=subprocess.run(['gh','release','view',version,'--repo',repo,'--json','isDraft'],stdout=subprocess.PIPE,text=True,stderr=subprocess.DEVNULL)
if existing.returncode==0:
    assert json.loads(existing.stdout)['isDraft'],'Release is already published; use a new version'
dist=root/'dist';dist.mkdir(exist_ok=True);manifest={'version':version,'platform':'linux/amd64','sources':json.loads((root/'sources.lock.json').read_text()),'images':{}}
refs=[]
for service,name in [('api','api'),('web','webui')]:
    local='courseflow-'+name+':'+version;remote=registry+'/courseflow-'+name+':'+version
    subprocess.run(['docker','tag',local,remote],check=True);subprocess.run(['docker','push',remote],check=True)
    image=json.loads(subprocess.check_output(['docker','image','inspect',remote]))[0]
    digest=next(x for x in image['RepoDigests'] if x.startswith(registry+'/courseflow-'+name+'@'))
    manifest['images'][service]={'tag':remote,'digest':digest,'id':image['Id']};refs.append(remote)
for filename,key in [('images.lock.env','digest'),('images.offline.env','tag')]:
    (dist/filename).write_text('API_IMAGE='+manifest['images']['api'][key]+'\nWEB_IMAGE='+manifest['images']['web'][key]+'\n')
manifest['source_archives']=json.loads((root/'.build/context/source-archives.json').read_text())
(dist/'release.json').write_text(json.dumps(manifest,indent=2)+'\n')
package=dist/'package'
if package.exists():shutil.rmtree(package)
package.mkdir()
for name in ['README.md','LICENSE','.env.example','compose.yaml','scripts','security','licenses','docs','examples','sources.lock.json']:
    source=root/name
    if source.is_dir():shutil.copytree(source,package/name,dirs_exist_ok=True)
    else:shutil.copy2(source,package/name)
for name in ['images.lock.env','release.json']:shutil.copy2(dist/name,package/name)
online=dist/f'courseflow-docker-{version}.tar.gz'
with tarfile.open(online,'w:gz') as tar:tar.add(package,arcname='courseflow-docker')
process=subprocess.Popen(['docker','save',*refs],stdout=subprocess.PIPE)
with gzip.open(package/'images.tar.gz','wb',compresslevel=1) as stream:shutil.copyfileobj(process.stdout,stream)
if process.wait():raise RuntimeError('docker save failed')
shutil.copy2(dist/'images.offline.env',package/'images.offline.env')
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
(package/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(package))+'\n' for p in sorted(package.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
offline=dist/f'courseflow-docker-{version}-linux-amd64-offline.tar.gz'
with tarfile.open(offline,'w:gz',compresslevel=1) as tar:tar.add(package,arcname='courseflow-docker')
assets=[online,offline,dist/'images.lock.env',dist/'images.offline.env',dist/'release.json']
(dist/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in assets));assets.append(dist/'SHA256SUMS')
notes=dist/'release-notes.md';notes.write_text(f'''Courseflow Docker {version}（Linux amd64）。

下载并解压 `courseflow-docker-{version}.tar.gz`，将 `.env.example` 复制为 `.env`，设置 `PUBLIC_URL`，依次执行 `./scripts/courseflow init` 和 `./scripts/courseflow up`。

离线包包含 API、WebUI 镜像和 SHA-256 校验文件；`load` 在目标 Docker 上生成不可变的本地镜像 ID 锁文件，详见 `docs/offline.md`。

API 与 WebUI 镜像发布到 GHCR，正式版本同时更新两个镜像的 `latest` 标签。已有部署可先更新部署仓库，再运行 `./scripts/courseflow update latest`；也可传入本次发布的 `images.lock.env` 升级到指定版本。

数据保存在容器之外，更新时保留一份已验证备份，启动失败自动回退。`release.json` 记录源码提交与镜像 digest。CI 使用离线模块契约及部署、恢复测试，不使用真实平台账号。
''')
if existing.returncode:
    subprocess.run(['gh','release','create',version,'--repo',repo,'--target',os.environ.get('GITHUB_SHA','main'),'--title','Courseflow Docker '+version,'--notes-file',str(notes),'--draft'],check=True)
subprocess.run(['gh','release','upload',version,'--repo',repo,*map(str,assets),'--clobber'],check=True)
print('Draft release uploaded; publish only after anonymous pull verification passes')
