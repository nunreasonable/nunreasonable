import base64
import struct
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

OWNER = 'nunreasonable'
ROOT = Path(__file__).resolve().parents[1]


def github(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-download-counter'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urlopen(Request('https://api.github.com/' + path, headers=headers), timeout=60) as response:
        return json.load(response)


def pages(path):
    page = 1
    while True:
        batch = github(f'{path}?per_page=100&page={page}')
        yield from batch
        if len(batch) < 100:
            break
        page += 1


def main():
    counts = {}
    for repo in pages(f'users/{OWNER}/repos'):
        if repo['owner']['login'].lower() != OWNER:
            continue
        count = sum(asset['download_count']
                    for release in pages(f'repos/{repo["full_name"]}/releases')
                    if not release['draft']
                    for asset in release['assets'])
        if count:
            counts[repo['name']] = count
    total = sum(counts.values())
    if total == 0:
        raise RuntimeError('No downloads returned; keep the previous counter instead of rendering a visit count.')
    digits = str(total).zfill(7)
    parts = []
    left = 0
    height = 0
    for digit in digits:
        data = (ROOT / 'assets/moe-counter' / f'{digit}.gif').read_bytes()
        width, h = struct.unpack('<HH', data[6:10])
        height = max(height, h)
        encoded = base64.b64encode(data).decode('ascii')
        parts.append(f'<image x="{left}" width="{width}" height="{h}" href="data:image/gif;base64,{encoded}"/>')
        left += width
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{left}" height="{height}" viewBox="0 0 {left} {height}" role="img" aria-label="{total} release file downloads">'
           f'<title>{total:,} release file downloads</title>' + ''.join(parts) + '</svg>\n')
    (ROOT / 'assets/downloads.svg').write_text(svg)
    (ROOT / 'assets/downloads.json').write_text(
        json.dumps({'total': total, 'repositories': dict(sorted(counts.items()))}, indent=2) + '\n')
    print(f'{total:,} release asset downloads across {len(counts)} repositories with downloads')


if __name__ == '__main__':
    main()
