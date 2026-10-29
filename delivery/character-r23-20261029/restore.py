from pathlib import Path
import json,hashlib,os
root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
for name,info in manifest.items():
    target=root/name
    if info['parts']>1:
        tmp=target.with_name(target.name+'.rebuilding')
        try:
            h=hashlib.sha256(); count=0
            with tmp.open('wb') as dst:
                for i in range(1,info['parts']+1):
                    source=target.with_name(target.name+f'.part{i:03d}')
                    with source.open('rb') as src:
                        while chunk:=src.read(1024*1024):
                            dst.write(chunk);h.update(chunk);count+=len(chunk)
            if h.hexdigest()!=info['sha256'] or count!=info['size']:
                raise ValueError('分卷校验失败: '+name)
            os.replace(tmp,target)
        finally:
            tmp.unlink(missing_ok=True)
    else:
        h=hashlib.sha256()
        with target.open('rb') as src:
            while chunk:=src.read(1024*1024): h.update(chunk)
        if h.hexdigest()!=info['sha256'] or target.stat().st_size!=info['size']:
            raise ValueError('文件校验失败: '+name)
    print('已校验',name)
print('全部文件重组及校验完成')
