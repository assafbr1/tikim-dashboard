#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
אימות נתוני אתר הגיבוי כפי שהם במאגר: קורא את data.enc.part*.txt מתיקייה (למשל clone טרי),
בודק שהכותרות עקביות, שה-sha256 של החיבור תואם, מפענח עם הסיסמה וסופר תיקים, מועדים ומסמכים.

שימוש:
  python3 verify_site_data.py --dir <תיקיית ה-clone> --password <סיסמה> [--min-cases 300]
                              [--expect-sha <sha256 של data.enc.txt המקומי>]
מדפיס שורת OK עם המספרים, או FAIL עם הסיבה, וקוד יציאה 1 בכישלון.
"""
import argparse, base64, gzip, hashlib, json, os, sys


def read_parts(d: str):
    p0 = os.path.join(d, 'data.enc.part0.txt')
    if not os.path.isfile(p0):
        raise RuntimeError('data.enc.part0.txt לא נמצא')
    h0, c0 = open(p0, encoding='utf-8').read().split('\n', 1)
    h0 = json.loads(h0)
    n = int(h0['parts'])
    chunks = [c0.strip()]
    for i in range(1, n):
        p = os.path.join(d, f'data.enc.part{i}.txt')
        if not os.path.isfile(p):
            raise RuntimeError(f'חסר data.enc.part{i}.txt')
        h, c = open(p, encoding='utf-8').read().split('\n', 1)
        h = json.loads(h)
        if h.get('sha256') != h0.get('sha256') or h.get('parts') != n or h.get('part') != i:
            raise RuntimeError(f'כותרת לא עקבית בחלק {i} (ערבוב של שתי ריצות?)')
        chunks.append(c.strip())
    text = ''.join(chunks)
    sha = hashlib.sha256(text.encode('utf-8')).hexdigest()
    if sha != h0.get('sha256'):
        raise RuntimeError('sha256 של החיבור אינו תואם לכותרת')
    return text, n, sha


def decrypt(enc_text: str, password: str) -> dict:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    d = json.loads(enc_text)
    key = PBKDF2HMAC(hashes.SHA256(), 32, base64.b64decode(d['salt']), int(d['iters'])).derive(password.encode('utf-8'))
    pt = AESGCM(key).decrypt(base64.b64decode(d['iv']), base64.b64decode(d['ct']), None)
    if d.get('gzip'):
        pt = gzip.decompress(pt)
    return json.loads(pt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--password', required=True)
    ap.add_argument('--min-cases', type=int, default=300)
    ap.add_argument('--expect-sha')
    a = ap.parse_args()
    try:
        text, n, sha = read_parts(a.dir)
        if a.expect_sha and sha != a.expect_sha:
            raise RuntimeError(f'sha256 במאגר ({sha[:12]}) שונה מהקובץ המקומי ({a.expect_sha[:12]})')
        j = decrypt(text, a.password)
        cases, dls, docs = len(j.get('cases', [])), len(j.get('deadlines', [])), len(j.get('docs', []))
        if cases < a.min_cases:
            raise RuntimeError(f'רק {cases} תיקים בקובץ, פחות מ-{a.min_cases}')
        print(f'OK: {n} חלקים, sha256 {sha[:12]}, exportedAt {j.get("exportedAt")}, '
              f'{cases} תיקים, {dls} מועדים, {docs} מסמכים')
    except Exception as e:
        print(f'FAIL: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
