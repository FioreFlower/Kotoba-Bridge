"""Collect installed runtime licenses for an inspectable Windows distribution."""
import argparse
import importlib.metadata
from pathlib import Path
import shutil
import sys


def collect(output):
    output.mkdir(parents=True, exist_ok=True)
    index = []
    for name in ('mss', 'Pillow', 'PyInstaller'):
        distribution = importlib.metadata.distribution(name)
        found = []
        for item in distribution.files or []:
            if 'license' not in item.name.lower() and 'copying' not in item.name.lower():
                continue
            source = Path(distribution.locate_file(item))
            if source.is_file():
                destination = output / name / str(item).replace('..', '_')
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                found.append(destination.relative_to(output).as_posix())
        if not found:
            raise RuntimeError('Missing installed license files for ' + name)
        index.append(name + ' ' + distribution.version + '\n' + '\n'.join(found))
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        raise RuntimeError('Python distribution LICENSE.txt is missing')
    shutil.copyfile(python_license, output / 'CPython-LICENSE.txt')
    tcl_root = Path(sys.base_prefix) / 'tcl'
    tcl_files = list(tcl_root.rglob('license.terms')) + list(tcl_root.rglob('license.txt'))
    for source in tcl_files:
        destination = output / 'Tcl-Tk' / source.relative_to(tcl_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    # Official Windows Python's LICENSE.txt also includes Tcl/Tk notices; keep it
    # even when this distribution has no separate Tcl license. Review before release.
    (output / 'INDEX.txt').write_text('\n\n'.join(index) + '\n\nCPython-LICENSE.txt includes bundled software notices.\nReview actual frozen dependencies before release.\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    collect(parser.parse_args().output)
