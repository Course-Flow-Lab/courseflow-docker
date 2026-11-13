#!/usr/bin/env python3
"""从固定公开提交生成可独立安装的模块包及 GitHub Pages 下载目录。"""
import argparse
import gzip
import hashlib
import html
import io
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def prepare(lock, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for ident, source in lock['modules'].items():
        target = destination/ident
        if target.exists(): shutil.rmtree(target)
        url = 'https://codeload.github.com/'+source['repository']+'/tar.gz/'+source['commit']
        with urllib.request.urlopen(url, timeout=120) as response: data = response.read()
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            members = archive.getmembers()
            prefix = members[0].name.split('/')[0]+'/'
            for member in members:
                if member.name.startswith(prefix):
                    member.name = member.name[len(prefix):]
                    if member.name: archive.extract(member, target, filter='data')
        (target/'SOURCE.json').write_text(json.dumps({**source, 'archive_sha256':hashlib.sha256(data).hexdigest()},ensure_ascii=False,indent=2)+'\n')


def pack(source, compiled, info, output):
    manifest = json.loads((source/'courseflow.module.json').read_text())
    paths = {}
    declared = ['courseflow.module.json',manifest['runtime']['entry'],*manifest['runtime'].get('files',[]),'LICENSE','README.md','SOURCE.json']
    for relative in dict.fromkeys(declared):
        if Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('模块文件必须位于安装包内')
        candidate = compiled/relative if (compiled/relative).exists() else source/relative
        if not candidate.exists(): raise FileNotFoundError(candidate)
        if candidate.is_dir():
            for file in candidate.rglob('*'):
                if '__pycache__' in file.parts or file.suffix in ('.pyc','.pyo'): continue
                if file.is_file(): paths[str(Path(relative)/file.relative_to(candidate))] = file
        else: paths[relative] = candidate
    # 依赖的第三方许可证若由打包器另存，必须随包分发。
    for file in compiled.glob('*.LEGAL.txt'): paths[file.name] = file
    contents = {relative:file.read_bytes() for relative,file in paths.items()}
    contents['INSTALL.md'] = f'''# {manifest['name']}安装包

版本：{manifest['version']}；模块编号：{manifest['id']}；框架要求：{manifest['engines']['framework']}。

运行环境：{info['requirements']}。本包已包含运行产物，无需在服务器上编译。

Docker 用户请运行 `./scripts/courseflow module install /绝对路径/本安装包.tgz`。
独立 Framework 用户先停止使用同一数据目录的服务，再运行 `npm run cli -- module add /绝对路径/本安装包.tgz`。
超星仍需安装 requirements.txt 中的 Python 依赖；Docker 发行版已经提供。

完整安装、配置和回退说明：https://github.com/Course-Flow-Lab/courseflow-docker/blob/main/docs/modules.md

固定源码：https://github.com/{info['repository']}/tree/{info['commit']}
源码归档：https://github.com/{info['repository']}/archive/{info['commit']}.tar.gz
'''.encode()
    filename = info['repository'].split('/')[-1]+'-'+manifest['version']+'-'+info['target']+'-'+info['commit'][:7]+'.tgz'
    destination = output/filename
    with destination.open('wb') as raw, gzip.GzipFile(fileobj=raw,filename='',mode='wb',mtime=0) as compressed, tarfile.open(fileobj=compressed,mode='w',format=tarfile.PAX_FORMAT) as archive:
        for relative, content in sorted(contents.items()):
            entry = tarfile.TarInfo('package/'+relative)
            entry.size = len(content); entry.mtime = 0; entry.mode = 0o755 if relative==manifest['runtime']['entry'] else 0o644
            archive.addfile(entry, io.BytesIO(content))
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    (output/(filename+'.sha256')).write_text(digest+'  '+filename+'\n')
    return {'id':manifest['id'],'name':manifest['name'],'version':manifest['version'],'module_api':manifest['moduleApi'],
        'framework':manifest['engines']['framework'],'entry':manifest['runtime']['entry'],'target':info['target'],
        'requirements':info['requirements'],'file':'modules/'+filename,'sha256':digest,'bytes':destination.stat().st_size,
        'source':info,'license':'GPL-3.0-only' if manifest['id']=='cx' else 'MIT'}


def site(items, destination):
    (destination/'catalog.json').write_text(json.dumps({'schema_version':1,'modules':items},ensure_ascii=False,indent=2)+'\n')
    (destination/'.nojekyll').write_text('')
    rows = []
    for item in items:
        e = lambda value: html.escape(str(value), quote=True)
        rows.append(f'''<article><h2>{e(item['name'])} <small>{e(item['version'])}</small></h2>
<p>{e(item['requirements'])}</p><dl><dt>框架版本</dt><dd>{e(item['framework'])}</dd><dt>模块编号</dt><dd><code>{e(item['id'])}</code></dd>
<dt>许可</dt><dd>{e(item['license'])}</dd></dl><p><a class="download" href="{e(item['file'])}" download>下载 .tgz</a>
<a href="{e(item['file'])}.sha256" download>SHA-256 校验文件</a></p><details><summary>来源与校验值</summary><p><a href="https://github.com/{e(item['source']['repository'])}/tree/{e(item['source']['commit'])}">查看固定源码提交</a></p><code>{e(item['sha256'])}</code></details></article>''')
    (destination/'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Courseflow 模块下载</title>
<style>body{margin:0;background:#f4f6fa;color:#172333;font:16px/1.7 system-ui,sans-serif}main{max-width:1050px;margin:auto;padding:40px 24px}h1{line-height:1.3}header p{max-width:780px;color:#526173}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}article{background:white;border:1px solid #dce3ed;border-radius:16px;padding:24px}h2{font-size:22px;margin-top:0}small{color:#667085;font-size:15px}a{color:#2456bd}a.download{display:inline-block;background:#2456bd;color:white;padding:8px 14px;border-radius:8px;text-decoration:none;margin:0 12px 12px 0}dl{display:grid;grid-template-columns:90px 1fr;font-size:14px}dt{color:#667085}dd{margin:0}code{overflow-wrap:anywhere;font-size:13px}footer{padding-top:24px;color:#526173}</style>
<main><header><p>Courseflow · 平台模块</p><h1>下载模块，安装到自己的服务器</h1><p>下载前核对框架版本与运行环境，安装前验证 SHA-256。安装包已包含编译产物与许可证；无需在服务器上安装 Rust 或运行 npm 构建。超星源码包仍需要 Python 依赖，Docker 发行版已提供。</p>
<p><a href="https://github.com/Course-Flow-Lab/courseflow-docker/blob/main/docs/modules.md">阅读模块安装手册</a> · <a href="catalog.json">机器可读目录</a> · <a href="https://github.com/Course-Flow-Lab/courseflow-docker/releases">GitHub Releases 历史安装包</a></p></header><section class="grid">'''+''.join(rows)+'''</section><footer><p>智慧树与超星已预装于 Docker 发行版，通常无需重复安装。U校园为可选模块。统一题库属于框架内置能力，无需另装。</p><p>验证使用合成账号、离线 fixture 和禁用网络的容器，不代表真实课程已验收。</p></footer></main></html>''')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','pack'])
    parser.add_argument('--sources',type=Path,default=ROOT/'.build/modules/source')
    parser.add_argument('--compiled',type=Path,default=ROOT/'.build/modules/compiled')
    parser.add_argument('--output',type=Path,default=ROOT/'dist/modules-site')
    args = parser.parse_args()
    lock = json.loads((ROOT/'module-sources.lock.json').read_text())
    if args.action=='prepare': prepare(lock,args.sources); return
    args.output.mkdir(parents=True,exist_ok=True)
    packages = args.output/'modules'; packages.mkdir(exist_ok=True)
    items = [pack(args.sources/ident,args.compiled/ident,source,packages) for ident,source in lock['modules'].items()]
    (packages/'SHA256SUMS').write_text(''.join(item['sha256']+'  '+Path(item['file']).name+'\n' for item in items))
    site(items,args.output)
    print(json.dumps({'modules':[item['id'] for item in items],'output':str(args.output)},ensure_ascii=False))


if __name__=='__main__': main()
