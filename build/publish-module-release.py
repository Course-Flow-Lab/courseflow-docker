#!/usr/bin/env python3
"""将已验收的模块包同步为独立 Release，保留历史文件且不改变容器最新版。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def release_assets(site):
    site=site.resolve()
    catalog=json.loads((site/'catalog.json').read_text())
    assets=[site/'catalog.json',site/'modules/SHA256SUMS']
    for item in catalog['modules']:
        file=(site/item['file']).resolve()
        if file.parent!=site/'modules' or file.suffix!='.tgz': raise ValueError('模块文件不在发布目录内')
        if digest(file)!=item['sha256']: raise ValueError('模块校验值不一致：'+file.name)
        checksum=file.with_name(file.name+'.sha256')
        if checksum.read_text()!=item['sha256']+'  '+file.name+'\n': raise ValueError('模块校验文件不一致')
        assets.extend([file,checksum])
    if len({file.name for file in assets})!=len(assets): raise ValueError('Release 附件名称重复')
    checksums=''.join(item['sha256']+'  '+Path(item['file']).name+'\n' for item in catalog['modules'])
    if (site/'modules/SHA256SUMS').read_text()!=checksums: raise ValueError('总校验文件与目录不一致')
    hashes={file.name:digest(file) for file in assets}
    key=hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12]
    return 'modules-'+key,assets,hashes,catalog


def verify_download(tag,repository,hashes,run):
    with tempfile.TemporaryDirectory(prefix='courseflow-release-check-') as directory:
        args=['gh','release','download',tag,'--repo',repository,'--dir',directory]
        for name in hashes: args.extend(['--pattern',name])
        run(args,check=True)
        for name,value in hashes.items():
            if digest(Path(directory)/name)!=value: raise ValueError('Release 附件与已验收文件不一致：'+name)


def publish(site,repository,target,run=subprocess.run):
    tag,assets,hashes,catalog=release_assets(site)
    existing=run(['gh','release','view',tag,'--repo',repository,'--json','isDraft,assets'],capture_output=True,text=True)
    if existing.returncode==0:
        info=json.loads(existing.stdout)
        if not info['isDraft']:
            if {asset['name'] for asset in info['assets']}!=set(hashes): raise ValueError('已发布 Release 的附件列表不一致')
            verify_download(tag,repository,hashes,run)
            return tag
    elif 'release not found' not in (existing.stderr or '').lower() and '404' not in (existing.stderr or ''):
        raise RuntimeError('无法查询模块 Release：'+(existing.stderr or '未知错误'))
    rows='\n'.join(f"| {item['name']} | {item['version']} | {item['requirements']} | `{Path(item['file']).name}` |" for item in catalog['modules'])
    notes=f'''独立平台模块安装包，与本批 GitHub Pages 下载文件使用相同 SHA-256。

| 模块 | 版本 | 运行环境 | 安装附件 |
| --- | --- | --- | --- |
{rows}

附件包含各模块 `.tgz`、对应校验文件、总校验文件 `SHA256SUMS` 和来源目录 `catalog.json`。

[安装手册](https://github.com/Course-Flow-Lab/courseflow-docker/blob/main/docs/modules.md) · [模块下载页](https://course-flow-lab.github.io/courseflow-docker/)

安装前运行 `sha256sum -c SHA256SUMS`。Docker 中可使用 `./scripts/courseflow module install /绝对路径/模块包.tgz`。

包内包含许可证、源码提交与中文安装说明。发布检查使用合成账号与离线 fixture，不使用真实平台账号。
'''
    with tempfile.TemporaryDirectory(prefix='courseflow-release-notes-') as directory:
        file=Path(directory)/'notes.md';file.write_text(notes)
        if existing.returncode!=0:
            run(['gh','release','create',tag,'--repo',repository,'--target',target,'--title','Courseflow 平台模块安装包 '+tag.removeprefix('modules-'),
                '--notes-file',str(file),'--draft','--latest=false'],check=True)
        run(['gh','release','upload',tag,'--repo',repository,*map(str,assets),'--clobber'],check=True)
        verify_download(tag,repository,hashes,run)
        run(['gh','release','edit',tag,'--repo',repository,'--draft=false','--latest=false'],check=True)
    return tag


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--site',type=Path,default=Path(__file__).resolve().parents[1]/'dist/modules-site')
    args=parser.parse_args()
    repository=os.environ.get('GITHUB_REPOSITORY','Course-Flow-Lab/courseflow-docker')
    target=os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    tag=publish(args.site,repository,target)
    url='https://github.com/'+repository+'/releases/tag/'+tag
    print(url)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as output: output.write('tag='+tag+'\nurl='+url+'\n')
