#!/usr/bin/env python3
"""将已验收、可匿名拉取的发布镜像同步到 latest，不回退到较旧版本。"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def version_number(value):
    if not re.fullmatch(r'v\d+\.\d+\.\d+', value):
        raise ValueError('版本必须为 vX.Y.Z')
    return tuple(map(int, value[1:].split('.')))


def promote(version, manifest, repository, run=subprocess.run):
    number = version_number(version)
    if manifest['version'] != version:
        raise ValueError('发布清单与版本不一致')
    releases = json.loads(run(['gh', 'release', 'list', '--repo', repository, '--limit', '1000',
        '--json', 'tagName,isDraft,isPrerelease'], check=True, capture_output=True, text=True).stdout)
    for release in releases:
        tag = release['tagName']
        if not release['isDraft'] and not release['isPrerelease'] and re.fullmatch(r'v\d+\.\d+\.\d+', tag) and version_number(tag) > number:
            print('已有更新的正式版本，保留当前 latest：'+tag)
            return False
    registry = 'ghcr.io/'+repository.split('/')[0].lower()
    aliases = []
    # 在修改任何标签前检查两个源镜像，避免引用错误的本地构建。
    for service, name in [('api', 'api'), ('web', 'webui')]:
        tag = registry+'/courseflow-'+name+':'+version
        expected = manifest['images'][service]
        if expected['tag'] != tag:
            raise ValueError('镜像地址不属于本次发布')
        image = json.loads(run(['docker', 'image', 'inspect', tag], check=True, capture_output=True, text=True).stdout)[0]
        if image['Config']['Labels'].get('org.opencontainers.image.version') != version or image['Id'] != expected['id'] or expected['digest'] not in image['RepoDigests']:
            raise ValueError('本地镜像与已验收的发布清单不一致')
        aliases.append((tag, registry+'/courseflow-'+name+':latest'))
    for tag, latest in aliases:
        run(['docker', 'tag', tag, latest], check=True)
    for _, latest in aliases:
        run(['docker', 'push', latest], check=True)
    print('API 与 WebUI 的 latest 已同步至 '+version)
    return True


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    repository = os.environ.get('GITHUB_REPOSITORY', 'Course-Flow-Lab/courseflow-docker')
    promote(sys.argv[1], json.loads((root/'dist/release.json').read_text()), repository)
    registry = 'ghcr.io/'+repository.split('/')[0].lower()
    (root/'dist/images.latest.env').write_text('API_IMAGE='+registry+'/courseflow-api:latest\nWEB_IMAGE='+registry+'/courseflow-webui:latest\n')
