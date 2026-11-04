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
assert sha(raw)=='45efb78e93c4fdf54c8b21c2a0482d0818745b9af6d27db3454dce4fff67b243', 'Manifest does not match this release'
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
# Preserve the already deployed media renditions. This release changes text and playback intent only.
media_checksums={}
def preserve_media(pair):
 film,variant=pair
 relative=film.parent.relative_to(root)/variant
 origin='https://qz1859202-prog.github.io/liangma-'+manifest['edition']
 url=origin+'/'+quote(relative.as_posix(),safe='/')
 for attempt in range(5):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Liangma-Media-Preserve/1.0'}),timeout=90) as response:
    data=response.read()
    expected_length=response.headers.get('Content-Length')
   assert len(data)>1000 and b'ftyp' in data[:32], 'Invalid MP4 rendition'
   if expected_length:assert len(data)==int(expected_length), 'Incomplete media download'
   target=root/relative;target.write_bytes(data)
   return relative.as_posix(),{'bytes':len(data),'sha256':sha(data)}
  except Exception:
   if attempt==4:raise
   time.sleep(2**attempt)
with ThreadPoolExecutor(max_workers=4) as pool:
 for name,spec in pool.map(preserve_media,[(film,variant) for film in films for variant in ['playback.mp4','mobile.mp4','preview.mp4']]):media_checksums[name]=spec
assert len(media_checksums)==30
import subprocess,shutil
if not shutil.which('ffmpeg'):
 subprocess.run(['sudo','apt-get','update','-qq'],check=True)
 subprocess.run(['sudo','apt-get','install','-y','-qq','ffmpeg'],check=True)
for film in films:
 print('Preparing smooth rendition: '+film.parent.name,flush=True)
 subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(film.parent/'mobile.mp4'),'-vf',"scale=w='min(640,iw)':h='min(360,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",'-c:v','libx264','-preset','veryfast','-crf','29','-maxrate','400k','-bufsize','800k','-profile:v','main','-pix_fmt','yuv420p','-c:a','aac','-b:a','64k','-movflags','+faststart',str(film.parent/'smooth.mp4')],check=True)
 target=film.parent/'smooth.mp4';data=target.read_bytes();assert len(data)>1000 and data.index(b'moov')<data.index(b'mdat');media_checksums[target.relative_to(root).as_posix()]={'bytes':len(data),'sha256':sha(data)}
assert len(media_checksums)==40

(root/'media-checksums.json').write_text(json.dumps(media_checksums,indent=2))
print('Verified '+manifest['edition']+' portfolio: '+str(len(expected))+' assets, 10 complete films, independent public Pages deployment.')
