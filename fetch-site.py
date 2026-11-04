from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from urllib.parse import quote
import hashlib,json,stat,time,urllib.request,zipfile

def sha(data):
 return hashlib.sha256(data).hexdigest()

def safe_path(value):
 p=PurePosixPath(value)
 assert value and not p.is_absolute() and '..' not in p.parts and p.as_posix()==value and '\\' not in value, 'Unsafe asset path'
 return value

raw=Path('site-manifest.json').read_bytes()
assert sha(raw)=='4b91b2a65da3a9f22e50f4c57fb3fd2a2c4a63a9cf40235285aed057aa098d19', 'Manifest does not match this release'
manifest=json.loads(raw)
archive=Path('site-code.zip')
assert sha(archive.read_bytes())==manifest['code_sha256'], 'Code archive mismatch'
root=Path('_site')
assert not root.is_symlink(), 'Unsafe output directory'
root.mkdir(exist_ok=True)
expected={safe_path(i['path']):i for i in manifest['files']}
assert len(expected)==len(manifest['files']), 'Duplicate asset paths'
with zipfile.ZipFile(archive) as bundle:
 seen=set()
 for item in bundle.infolist():
  name=safe_path(item.filename)
  assert not item.is_dir() and name in expected and 'origin' not in expected[name], 'Unexpected code entry'
  assert name not in seen and not stat.S_ISLNK(item.external_attr>>16), 'Unsafe archive entry'
  seen.add(name)
  data=bundle.read(item)
  spec=expected[name]
  assert len(data)==spec['bytes'] and sha(data)==spec['sha256'], 'Code checksum mismatch: '+name
  target=root/name
  assert target.resolve().is_relative_to(root.resolve()), 'Unsafe code output path'
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(data)
 assert seen=={name for name,i in expected.items() if 'origin' not in i}, 'Missing code files'

def fetch(item):
 name=safe_path(item['path'])
 origin=item['origin']
 assert origin in ('https://qz1859202-prog.github.io/liangma-111', 'https://qz1859202-prog.github.io/liangma-444'), 'Unexpected asset origin'
 target=root/name
 assert target.resolve().is_relative_to(root.resolve()), 'Unsafe remote output path'
 target.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(5):
  try:
   req=urllib.request.Request(origin+'/'+quote(name,safe='/'),headers={'User-Agent':'Liangma-Pages-Release/2.0'})
   with urllib.request.urlopen(req,timeout=90) as response:data=response.read()
   assert len(data)==item['bytes'] and sha(data)==item['sha256'], 'Asset checksum mismatch: '+name
   target.write_bytes(data)
   return
  except Exception:
   if attempt==4:raise
   time.sleep(2**attempt)

remote=[i for i in manifest['files'] if 'origin' in i]
with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,remote))
(root/'.nojekyll').touch()
films=list(root.glob('films/*/index.m3u8'))
assert len(films)==10, 'Expected 10 complete HLS films'
for film in films:
 for line in film.read_text().splitlines():
  if line and not line.startswith('#'):
   relative=safe_path(line.strip())
   assert (film.parent/relative).is_file(), 'Missing HLS segment: '+relative
assert len([i for i in expected if i.startswith('films/')])==217
assert (root/'index.html').is_file()
print('Verified '+manifest['edition']+' portfolio: '+str(len(expected))+' assets, 10 complete films, independent public Pages deployment.')
