#!/usr/bin/env python3
"""Host-only published RFC vectors and actual patched extension boundary."""
import argparse, base64, hashlib, json, subprocess, tempfile, tarfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
archive=root/'sources/pass-otp-1.2.0.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='5720a649267a240a4f7ba5a6445193481070049c1d08ba38b00d20fc551c3a67'
src=root/'inspect/pass-otp-1.2.0/otp.bash'
with tarfile.open(archive) as tar:
 assert tar.extractfile('pass-otp-1.2.0/otp.bash').read()==src.read_bytes()
 upstream_append_test=tar.extractfile('pass-otp-1.2.0/test/append.t').read()
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=root/'evidence/otp-stdin-host-20261012.json');options=parser.parse_args()
times=[59,1111111109,1111111111,1234567890,2000000000,20000000000]
expected={'SHA1':['94287082','07081804','14050471','89005924','69279037','65353130'],'SHA256':['46119246','68084774','67062674','91819424','90698825','77737706'],'SHA512':['90693936','25091201','99943326','93441116','38618901','47863826']}
hotp=['755224','287082','359152','969429','338314','254676','287922','162583','399871','520489']
with tempfile.TemporaryDirectory(prefix='synthetic-otp-stdin-') as td:
 d=Path(td);(d/'otp.bash').write_bytes(src.read_bytes())
 (d/'test').mkdir();(d/'test/append.t').write_bytes(upstream_append_test)
 for name in ('pass-otp-stdin.patch', 'pass-otp-private-backend.patch', 'pass-otp-final-line.patch'):
  subprocess.run(['patch','-p1','-i',str(root/'patches'/name)],cwd=d,check=True,capture_output=True)
 text=(d/'otp.bash').read_text();text=text[:text.rindex('case "$1" in')]
 (d/'functions.bash').write_text(text)
 (d/'gpg').write_text('#!/bin/bash\ncat "${@: -1}"\n');(d/'gpg').chmod(0o700)
 backend=d/'backend'
 backend.write_text("#!/usr/bin/python3\nimport sys,os,json,subprocess\nfrom pathlib import Path\ns=sys.stdin.read(); assert s.strip() not in sys.argv; assert sys.argv[-1]=='-'\nPath(os.environ['OTP_OBSERVATION']).write_text(json.dumps({'argv':sys.argv[1:],'stdin_received':bool(s.strip())}))\nargs=['/usr/bin/oathtool']+sys.argv[1:]\nif os.environ.get('OTP_NOW'):args.insert(1,'--now=@'+os.environ['OTP_NOW'])\nif os.environ.get('OTP_FAIL'):sys.exit(7)\nr=subprocess.run(args,input=s,text=True);sys.exit(r.returncode)\n")
 backend.chmod(0o700)
 shell='source "$1"; OATH="$2"; GPG="$3"; GETOPT=/usr/bin/getopt; PREFIX="$4"; PROGRAM=pass; COMMAND=otp; check_sneaky_paths(){ :; }; die(){ echo "$*" >&2; exit 1; }; otp_insert(){ printf "%s" "$3" > "$2"; }; cmd_otp_code demo'
 import os
 env={'PATH':'/usr/bin:/bin','HOME':str(d),'OTP_OBSERVATION':str(d/'observation.json')}
 checks=0
 for alg,size in [('SHA1',20),('SHA256',32),('SHA512',64)]:
  key=(b'1234567890'*7)[:size];secret=base64.b32encode(key).decode().rstrip('=')
  for timestamp,want in zip(times,expected[alg]):
   (d/'demo.gpg').write_text(f'otpauth://totp/Synthetic?secret={secret}&algorithm={alg}&digits=8&period=30\n')
   r=subprocess.run(['/bin/bash','-c',shell,'test',str(d/'functions.bash'),str(backend),str(d/'gpg'),str(d)],env={**env,'OTP_NOW':str(timestamp)},capture_output=True,text=True)
   assert r.returncode==0 and r.stdout.strip()==want,(alg,timestamp,r.stderr,r.stdout)
   observation=json.loads((d/'observation.json').read_text());assert secret not in ' '.join(observation['argv']) and observation['stdin_received'];checks+=1
 secret=base64.b32encode(b'12345678901234567890').decode()
 for counter,want in enumerate(hotp):
  r=subprocess.run(['/usr/bin/oathtool','-b','--hotp',f'--counter={counter}','-'],input=secret+'\n',capture_output=True,text=True);assert r.returncode==0 and r.stdout.strip()==want;checks+=1
 (d/'demo.gpg').write_text(f'otpauth://hotp/Synthetic?secret={secret}&counter=0\n')
 r=subprocess.run(['/bin/bash','-c',shell,'test',str(d/'functions.bash'),str(backend),str(d/'gpg'),str(d)],env=env,capture_output=True,text=True)
 assert r.returncode==0 and r.stdout.strip()==hotp[1] and 'counter=1' in (d/'demo.gpg').read_text();checks+=1
 before=(d/'demo.gpg').read_bytes()
 r=subprocess.run(['/bin/bash','-c',shell,'test',str(d/'functions.bash'),str(backend),str(d/'gpg'),str(d)],env={**env,'OTP_FAIL':'1'},capture_output=True,text=True)
 assert r.returncode!=0 and (d/'demo.gpg').read_bytes()==before;checks+=1
 for uri in ['bad://Synthetic?secret='+secret,'otpauth://totp/?secret='+secret,'otpauth://totp/Synthetic?issuer=x','otpauth://hotp/Synthetic?secret='+secret+'&counter=invalid']:
  (d/'invalid-uri').write_text(uri)
  r=subprocess.run(['/bin/bash','-c','source \"$1\"; die(){ echo \"$*\" >&2; exit 1; }; otp_parse_uri \"$(cat \"$2\")\"','test',str(d/'functions.bash'),str(d/'invalid-uri')],capture_output=True,text=True)
  assert r.returncode!=0 and secret not in r.stderr and uri not in r.stderr;checks+=1
 record={'scope':'Host oathtool2.6.14 and patched extension functions; synthetic plaintext stubs, not encrypted/native acceptance','passed':True,'checks':checks,'coverage':['18 RFC6238 TOTP extension vectors; seed stdin and absent backend argv','10 RFC4226 HOTP backend vectors','HOTP upstream increment-before-code preserved','Backend failure leaves HOTP counter unchanged'],'patch_sha256':hashlib.sha256((root/'patches/pass-otp-stdin.patch').read_bytes()).hexdigest()}
 options.output.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
