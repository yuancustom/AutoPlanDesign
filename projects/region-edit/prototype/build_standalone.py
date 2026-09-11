"""Build a self-contained HTML from the committed prototype. No network or model."""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent

def build(destination: Path) -> None:
    if destination.exists():
        raise FileExistsError('Choose a new output path; existing files are not overwritten')
    document = (ROOT / 'index.html').read_text(encoding='utf-8')
    def asset(name: str) -> str:
        path = (ROOT / name).resolve()
        if path.parent != ROOT or not path.is_file():
            raise ValueError(f'Unexpected prototype asset: {name}')
        return path.read_text(encoding='utf-8')
    document = re.sub(r'<link rel="stylesheet" href="([^"]+)">',
                      lambda m: '<style>\n' + asset(m[1]) + '</style>', document)
    document = re.sub(r'<script src="([^"]+)"></script>',
                      lambda m: '<script>\n' + asset(m[1]).replace('</script', r'<\/script') + '</script>', document)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding='utf-8')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.out)
    print(args.out)
