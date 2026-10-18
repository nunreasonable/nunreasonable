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


def render_counter(total):
    from PIL import Image, ImageSequence
    sprites = []
    for digit in str(total).zfill(7):
        with Image.open(ROOT / 'assets/moe-counter' / f'{digit}.gif') as image:
            frames = [(frame.convert('RGBA'), frame.info.get('duration', 40))
                      for frame in ImageSequence.Iterator(image)]
        sprites.append(frames)
    width = sum(frames[0][0].width for frames in sprites)
    height = max(frames[0][0].height for frames in sprites)
    cycle = max(sum(duration for _, duration in frames) for frames in sprites)
    output = []
    for time in range(0, cycle, 40):
        canvas = Image.new('RGBA', (width, height))
        x = 0
        for frames in sprites:
            elapsed = time % sum(duration for _, duration in frames)
            for frame, duration in frames:
                if elapsed < duration:
                    break
                elapsed -= duration
            canvas.alpha_composite(frame, (x, height - frame.height))
            x += frame.width
        palette = canvas.convert('RGB').quantize(colors=255)
        palette.paste(255, mask=canvas.getchannel('A').point(lambda alpha: 255 if alpha == 0 else 0))
        palette.info['transparency'] = 255
        output.append(palette)
    output[0].save(ROOT / 'assets/downloads.gif', save_all=True,
                   append_images=output[1:], duration=40, loop=0,
                   transparency=255, disposal=2, optimize=False)


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
    render_counter(total)
    (ROOT / 'assets/downloads.json').write_text(
        json.dumps({'total': total, 'repositories': dict(sorted(counts.items()))}, indent=2) + '\n')
    print(f'{total:,} release asset downloads across {len(counts)} repositories with downloads')


if __name__ == '__main__':
    main()
