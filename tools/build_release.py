"""Build a deterministic installable ZIP; no Fusion or third-party packages needed."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ADDIN = ROOT / 'FusionMeshTools'


def build():
    manifest = json.loads((ADDIN / 'FusionMeshTools.manifest').read_text())
    version = manifest['version']
    files = {f'FusionMeshTools/{p.name}': p for p in ADDIN.iterdir()
             if p.is_file() and p.suffix in ('.py', '.manifest')}
    for name in ('README.md', 'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md'):
        files[f'FusionMeshTools/{name}'] = ROOT / name
    for path in (ROOT / 'docs').rglob('*'):
        if path.is_file() and path.suffix in ('.md', '.png', '.svg'):
            files['FusionMeshTools/' + path.relative_to(ROOT).as_posix()] = path
    expected = {'FusionMeshTools/FusionMeshTools.py', 'FusionMeshTools/FusionMeshTools.manifest'}
    if not expected.issubset(files):
        raise RuntimeError('Missing add-in entry point or manifest.')
    for path in ADDIN.glob('*.py'):
        compile(path.read_text(), path.name, 'exec')
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / f'FusionMeshTools-v{version}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip():
            raise RuntimeError('Release ZIP integrity check failed.')
        if any('__pycache__' in n or n.endswith('.pyc') for n in bundle.namelist()):
            raise RuntimeError('Python cache found in release.')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix('.zip.sha256')
    checksum.write_text(f'{digest}  {archive.name}\n')
    print(f'Built {archive.name} ({len(files)} files, {archive.stat().st_size:,} bytes)')
    print(f'SHA-256: {digest}')
    return archive


if __name__ == '__main__':
    build()
