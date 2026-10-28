from pathlib import Path
for first in Path(__file__).parent.rglob("*.part001"):
    target = first.with_name(first.name[:-8])
    parts = sorted(first.parent.glob(target.name + ".part[0-9][0-9][0-9]"))
    with target.open("wb") as dst:
        for part in parts:
            with part.open("rb") as src:
                while chunk := src.read(1024 * 1024): dst.write(chunk)
    print(target)
