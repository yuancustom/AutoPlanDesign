"""Bundle the local classic-script prototype; never fetch external assets."""
from pathlib import Path
import argparse
import re

ROOT = Path(__file__).resolve().parent
STYLES = [f'style-{i}.css' for i in range(1, 4)]
SCRIPTS = ['sample.js'] + [f'app-{i}.js' for i in range(1, 9)]


def build(output: Path) -> None:
    text = (ROOT / 'index.html').read_text(encoding='utf-8')
    css_refs = re.findall(r'<link rel="stylesheet" href="([^"]+)">', text)
    js_refs = re.findall(r'<script src="([^"]+)"></script>', text)
    if css_refs != STYLES or js_refs != SCRIPTS:
        raise ValueError('Unexpected local asset list or script order')
    for name in STYLES:
        content = (ROOT / name).read_text(encoding='utf-8')
        if '</style' in content.lower():
            raise ValueError('Unexpected closing style tag')
        text = text.replace(f'<link rel="stylesheet" href="{name}">', '<style>\n' + content + '\n</style>')
    for name in SCRIPTS:
        content = (ROOT / name).read_text(encoding='utf-8')
        if '</script' in content.lower():
            raise ValueError('Unexpected closing script tag')
        text = text.replace(f'<script src="{name}"></script>', '<script>\n' + content + '\n</script>')
    output = output.resolve()
    if output in [(ROOT / n).resolve() for n in ['index.html', *STYLES, *SCRIPTS]]:
        raise ValueError('Refuse to overwrite source')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding='utf-8')
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    build(parser.parse_args().out)
