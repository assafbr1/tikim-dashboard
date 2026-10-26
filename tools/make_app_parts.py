#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
פיצול קוד האתר (site.html) לפרוסות קטנות שאפשר להעלות ל-GitHub פרוסה אחת בכל קריאה של push_files.

שימוש:
  python3 make_app_parts.py --site site.html --out <תיקיית פלט>

הקוד נדחס ב-gzip (רמה 9, mtime 0, ולכן דטרמיניסטי) ומקודד ב-base64; הטקסט מפוצל לפרוסות של עד
CHUNK תווים: app.b64.part-00.txt, app.b64.part-01.txt וכן הלאה. בנוסף נכתבים app.b64.sha256 (ה-sha256
של טקסט ה-base64 המלא) ו-app.manifest.json ({"parts", "sha256", "builtAt", "htmlBytes"}) ש-index.html
של האתר קורא. הפעולה publish-build מפרסמת את הקבצים ל-main רק אחרי אימות.
"""
import argparse, base64, datetime, gzip, hashlib, json, os

CHUNK = 10000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    html = open(a.site, 'rb').read()
    b64 = base64.b64encode(gzip.compress(html, 9, mtime=0)).decode('ascii')
    sha = hashlib.sha256(b64.encode('ascii')).hexdigest()
    chunks = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
    os.makedirs(a.out, exist_ok=True)
    names = []
    for i, c in enumerate(chunks):
        name = f'app.b64.part-{i:02d}.txt'
        with open(os.path.join(a.out, name), 'w', encoding='ascii', newline='') as f:
            f.write(c)
        names.append(name)
    with open(os.path.join(a.out, 'app.b64.sha256'), 'w', encoding='ascii', newline='') as f:
        f.write(sha + '\n')
    manifest = {'parts': len(chunks), 'sha256': sha,
                'builtAt': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'htmlBytes': len(html)}
    with open(os.path.join(a.out, 'app.manifest.json'), 'w', encoding='ascii', newline='') as f:
        f.write(json.dumps(manifest, separators=(',', ':')) + '\n')
    print(f'site.html: {len(html)} בתים; base64: {len(b64)} תווים, sha256 {sha}')
    print(f'פרוסות: {len(chunks)} (עד {CHUNK} תווים כל אחת): ' + ', '.join(names))


if __name__ == '__main__':
    main()
