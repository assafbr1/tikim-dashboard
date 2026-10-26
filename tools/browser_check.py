#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
בדיקת דפדפן של אתר הגיבוי לפני פרסום קוד חדש (וגם לבדיקה מקומית).
מגיש תיקייה שמכילה index.html, קוד האתר (manifest ופרוסות, או app.part0..3) ו-data.enc.txt,
פותח את index.html ב-Chromium (Playwright), ומוודא:
  1. האפליקציה נטענת ומסך הסיסמה (#lock-pw) מופיע, בלי הודעת "שגיאה בטעינת האפליקציה".
  2. מסך הסיסמה מציג "עודכן לאחרונה" (כלומר data.enc.txt נקרא ופוענח כ-JSON).
  3. סיסמה שגויה מחזירה "סיסמה שגויה" (כלומר קוד הפענוח רץ עד הסוף).
  4. אם ניתנה --password: הסיסמה פותחת את האפליקציה ומוצגים כרטיסי תיקים.
הסיסמה האמיתית אינה נדרשת לפרסום; publish-build מריץ בלי --password.

שימוש: python3 browser_check.py --dir <תיקייה> [--password <סיסמה>] [--expect-source manifest|legacy]
"""
import argparse, asyncio, functools, http.server, sys, threading


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):
        pass


def serve(d, port):
    h = functools.partial(_Quiet, directory=d)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


async def run(d, port, password, expect_source):
    from playwright.async_api import async_playwright
    srv = serve(d, port)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page()
            await pg.goto(f'http://127.0.0.1:{port}/index.html')
            await pg.wait_for_selector('#lock-pw', timeout=30000)
            msg = await pg.evaluate("(document.getElementById('msg')||{}).textContent || ''")
            if 'שגיאה בטעינת' in msg:
                raise RuntimeError('שגיאת טעינה: ' + msg)
            src = await pg.evaluate('window.__appSource')
            if expect_source and src != expect_source:
                raise RuntimeError(f'מקור הקוד הוא {src} ולא {expect_source}')
            upd = await pg.inner_text('#lock-updated')
            if 'עודכן לאחרונה' not in upd:
                raise RuntimeError('מסך הסיסמה בלי "עודכן לאחרונה": קובץ הנתונים לא נקרא')
            await pg.fill('#lock-pw', 'wrong-password-check')
            await pg.click('#lock-btn')
            await pg.wait_for_function("document.getElementById('lock-err').textContent.includes('סיסמה שגויה')", timeout=30000)
            cards = None
            if password:
                await pg.fill('#lock-pw', password)
                await pg.click('#lock-btn')
                await pg.wait_for_function("document.getElementById('lock-overlay').style.display==='none'", timeout=30000)
                await pg.wait_for_timeout(1500)
                cards = await pg.evaluate("document.querySelectorAll('.case-card').length")
                if not cards:
                    raise RuntimeError('האפליקציה נפתחה אבל לא הוצגו כרטיסי תיקים')
            await b.close()
            print(f'OK: הקוד נטען ממקור {src}, "{upd.strip()}", סיסמה שגויה נדחית' + (f', סיסמה נכונה פותחת {cards} כרטיסים' if password else ''))
    finally:
        srv.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--password')
    ap.add_argument('--expect-source')
    ap.add_argument('--port', type=int, default=8765)
    a = ap.parse_args()
    try:
        asyncio.run(run(a.dir, a.port, a.password, a.expect_source))
    except Exception as e:
        print(f'FAIL: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
