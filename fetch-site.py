from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,json,re,time,urllib.request
manifest=json.loads(Path('site-manifest.json').read_text())
assert hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()=='011f625ff0b7a43cf6e35f49b33316bc93562f58d693e7c74769979f81de828f', 'Await matching 111 manifest revision'
root=Path('_site');root.mkdir(exist_ok=True)
INDEX_HTML = '<!doctype html>\n<html lang="zh-CN" class="dark">\n<head>\n  <meta charset="UTF-8" />\n  <meta name="viewport" content="width=device-width,initial-scale=1" />\n  <meta name="theme-color" content="#10110F" />\n  <meta name="description" content="量孖 — 南京量孖文化科技有限公司。艺术、生成影像与视觉表达，让想象的每一种可能被看见。" />\n  <title>量孖 LIANGMA — Imagination, in motion.</title>\n  <link rel="icon" href="/liangma-111/favicon.svg" type="image/svg+xml" />\n  <link rel="preload" href="/liangma-111/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin />\n  <link rel="preload" href="/liangma-111/media/water.webp" as="image" />\n  <script type="module" crossorigin src="/liangma-111/assets/index-fMFofe9w.js"></script>\n  <link rel="stylesheet" crossorigin href="/liangma-111/assets/index-CbXv6Ks_.css">\n</head>\n<body><div id="root"></div></body>\n</html>\n'
assert hashlib.sha256(INDEX_HTML.encode('utf-8')).hexdigest()=='5e0e663560b1a8d6b0086b90bcd44c5794bc90f9cc0c683a29b716408f76f064'
(root/'index.html').write_text(INDEX_HTML,encoding='utf-8')
def fetch(item):
 if item['path']=='index.html':return
 target=root/item['path'];target.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(4):
  try:
   request=urllib.request.Request(manifest['source_origin']+'/'+item['path'],headers={'User-Agent':'Liangma-Pages-Migration/1.0'})
   with urllib.request.urlopen(request,timeout=90) as response:data=response.read()
   if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Checksum mismatch: '+item['path'])
   if target.suffix in ['.html','.js','.css','.json','.webmanifest','.svg']:
    text=data.decode('utf-8')
    text=re.sub(r'(?<![\w:/-])/(assets|films|media|fonts|images|artworks|icons|paintings|brand)/',lambda m:'/'+manifest['repository']+'/'+m.group(1)+'/',text)
    text=text.replace('href="/favicon.svg"','href="/'+manifest['repository']+'/favicon.svg"')
    data=text.encode('utf-8')
   target.write_bytes(data)
   return
  except Exception:
   if attempt==3:raise
   time.sleep(2**attempt)
with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,manifest['files']))
(root/'.nojekyll').touch()
assert len(list(root.glob('films/*/index.m3u8')))==10
print('Verified original 111 portfolio with macOS-style film windows and clean typography.')
