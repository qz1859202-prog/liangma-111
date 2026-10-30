from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,json,re,time,urllib.request
manifest=json.loads(Path('site-manifest.json').read_text())
root=Path('_site');root.mkdir(exist_ok=True)
def fetch(item):
 target=root/item['path'];target.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(4):
  try:
   request=urllib.request.Request(manifest['source_origin']+'/'+item['path'],headers={'User-Agent':'Liangma-Pages-Migration/1.0'})
   with urllib.request.urlopen(request,timeout=90) as response:data=response.read()
   if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Checksum mismatch: '+item['path'])
   if target.suffix in ['.html','.js','.css','.json','.webmanifest','.svg']:
    text=data.decode('utf-8')
    text=re.sub(r'(?<![\w:/-])/(assets|films|media|fonts|images|artworks|icons|paintings)/',lambda m:'/'+manifest['repository']+'/'+m.group(1)+'/',text)
    text=text.replace('href="/favicon.svg"','href="/'+manifest['repository']+'/favicon.svg"')
    data=text.encode('utf-8')
   target.write_bytes(data)
   return
  except Exception:
   if attempt==3:raise
   time.sleep(2**attempt)
with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,manifest['files']))
(root/'.nojekyll').touch()
assert (root/'index.html').is_file()
assert len(list(root.glob('films/*/index.m3u8')))==10
print('Verified and prepared',len(manifest['files']),'files for',manifest['repository'])
