#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
אימות קוד האתר כפי שהוא ב-main: קורא app.manifest.json ואת הפרוסות app.b64.part-NN.txt מתיקייה
(clone טרי), בודק sha256, מפענח (base64 ואז gunzip), בודק שהתוצאה היא HTML שלם של האתר,
ואם ניתן site.html מקומי, משווה אליו בית לבית.

שימוש:
  python3 verify_site_app.py --dir <תיקיית ה-clone> [--expect-sha <sha256 מתוך app.b64.sha256>]
                             [--site <site.html מקומי>]
מדפיס שורת OK או FAIL עם הסיבה, וקוד יציאה 1 בכישלון. משמש גם את publish-build.
"""
import argparse, base64, gzip, hashlib, json, os, sys

MARKERS = ['lock-overlay', 'decryptEmbedded', '__siteSeed', 'data.enc.txt', 'lock-pw']


def load(d):
    mp = os.path.join(d, 'app.manifest.json')
    if not os.path.isfile(mp):
        raise RuntimeError('app.manifest.json לא נמצא')
    m = json.load(open(mp, encoding='utf-8'))
    n = int(m.get('parts', 0))
    if n <= 0:
        raise RuntimeError('manifest בלי parts')
    b64 = ''
    for i in range(n):
        p = os.path.join(d, f'app.b64.part-{i:02d}.txt')
        if not os.path.isfile(p):
            raise RuntimeError(f'חסרה פרוסה app.b64.part-{i:02d}.txt')
        b64 += open(p, encoding='ascii').read().strip()
    sha = hashlib.sha256(b64.encode('ascii')).hexdigest()
    if m.get('sha256') and m['sha256'] != sha:
        raise RuntimeError('sha256 של הפרוסות אינו תואם ל-manifest')
    sp = os.path.join(d, 'app.b64.sha256')
    if os.path.isfile(sp) and open(sp).read().strip() != sha:
        raise RuntimeError('sha256 של הפרוסות אינו תואם ל-app.b64.sha256')
    return m, n, b64, sha


def decode(b64):
    html = gzip.decompress(base64.b64decode(b64, validate=True))
    return html


def check_html(html: bytes):
    t = html.decode('utf-8')
    s = t.lstrip().lower()
    if not s.startswith('<!doctype html'):
        raise RuntimeError('הקוד אינו מתחיל ב-<!DOCTYPE html>')
    if not t.rstrip().lower().endswith('</html>'):
        raise RuntimeError('הקוד אינו מסתיים ב-</html>')
    if not (100000 <= len(t) <= 400000):
        raise RuntimeError(f'גודל הקוד חריג: {len(t)} תווים')
    missing = [k for k in MARKERS if k not in t]
    if missing:
        raise RuntimeError('חסרות מחרוזות מפתח של האתר: ' + ', '.join(missing))
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--expect-sha')
    ap.add_argument('--site')
    ap.add_argument('--write-html', help='כתיבת ה-HTML המפוענח לקובץ (לבדיקת דפדפן)')
    a = ap.parse_args()
    try:
        m, n, b64, sha = load(a.dir)
        if a.expect_sha and sha != a.expect_sha.strip():
            raise RuntimeError(f'sha256 במאגר ({sha[:12]}) שונה מהצפוי ({a.expect_sha.strip()[:12]}): הפרסום ל-main עדיין לא בוצע או נכשל')
        html = decode(b64)
        t = check_html(html)
        if a.site:
            local = open(a.site, 'rb').read()
            if local != html:
                raise RuntimeError('הקוד ב-main שונה מ-site.html המקומי')
        if a.write_html:
            open(a.write_html, 'wb').write(html)
        print(f'OK: {n} פרוסות, sha256 {sha[:12]}, builtAt {m.get("builtAt")}, {len(t)} תווי HTML' + (', זהה ל-site.html המקומי' if a.site else ''))
    except Exception as e:
        print(f'FAIL: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
