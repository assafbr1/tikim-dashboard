#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
בניית קובץ הנתונים המוצפן של אתר הגיבוי (data.enc.txt) ופיצולו לחלקים קטנים
(data.enc.part0.txt, data.enc.part1.txt, ...) שאפשר להעלות ל-GitHub חלק אחר חלק.

שימוש:
  python3 make_data_parts.py --payload payload.json --password <סיסמה> --out <תיקיית פלט>
      בונה data.enc.txt מתוך payload.json (gzip ואז AES-256-GCM עם מפתח PBKDF2-SHA256,
      300000 איטרציות, salt של 16 בתים ו-iv של 12 בתים אקראיים) ואז מפצל.
  python3 make_data_parts.py --from-enc data.enc.txt --out <תיקיית פלט>
      רק מפצל קובץ מוצפן קיים.

מבנה כל חלק: שורה ראשונה כותרת JSON {"v":1,"exportedAt","part","parts","sha256"},
שורה שנייה קטע של עד CHUNK תווים מתוך הטקסט של data.enc.txt. sha256 הוא של הטקסט המלא
של data.enc.txt, זהה בכל החלקים, וכך index.html של האתר מזהה חלקים מערבוב של שתי ריצות.
"""
import argparse, base64, gzip, hashlib, json, os, sys

CHUNK = 10000


def encrypt(payload_text: str, password: str) -> str:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    payload = json.loads(payload_text)
    exported_at = payload.get('exportedAt')
    if not exported_at:
        raise SystemExit('ה-payload חייב לכלול exportedAt')
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(hashes.SHA256(), 32, salt, 300000).derive(password.encode('utf-8'))
    ct = AESGCM(key).encrypt(iv, gzip.compress(payload_text.encode('utf-8'), 9), None)
    enc = {
        'salt': base64.b64encode(salt).decode(), 'iv': base64.b64encode(iv).decode(),
        'ct': base64.b64encode(ct).decode(), 'iters': 300000, 'gzip': True, 'exportedAt': exported_at,
    }
    return json.dumps(enc, separators=(',', ':'))


def split(enc_text: str, out_dir: str):
    enc_text = enc_text.strip()
    meta = json.loads(enc_text)
    sha = hashlib.sha256(enc_text.encode('utf-8')).hexdigest()
    chunks = [enc_text[i:i + CHUNK] for i in range(0, len(enc_text), CHUNK)]
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'data.enc.txt'), 'w', encoding='utf-8', newline='') as f:
        f.write(enc_text)
    names = []
    for i, c in enumerate(chunks):
        header = json.dumps({'v': 1, 'exportedAt': meta.get('exportedAt'), 'part': i,
                             'parts': len(chunks), 'sha256': sha}, separators=(',', ':'))
        name = f'data.enc.part{i}.txt'
        with open(os.path.join(out_dir, name), 'w', encoding='utf-8', newline='') as f:
            f.write(header + '\n' + c + '\n')
        names.append(name)
    print(f'data.enc.txt: {len(enc_text)} תווים, sha256 {sha}')
    print(f'חלקים: {len(chunks)} (עד {CHUNK} תווים כל אחד): ' + ', '.join(names))
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--payload')
    ap.add_argument('--password')
    ap.add_argument('--from-enc')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.from_enc:
        enc_text = open(a.from_enc, encoding='utf-8').read()
    elif a.payload and a.password:
        enc_text = encrypt(open(a.payload, encoding='utf-8').read(), a.password)
    else:
        ap.error('נדרש --from-enc, או --payload יחד עם --password')
    split(enc_text, a.out)


if __name__ == '__main__':
    main()
