"""투혼(闘魂) 스타일 생성기: posts.json -> out/<id>.jpg (+ 릴스용 out/<id>.mp4)
사용법: python render.py [--video] [--all]"""
import json, html, sys, subprocess, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.resolve()
e = lambda s: html.escape(s)

def content(cfg, p):
    b = e(cfg["brand"])
    if p.get("type") == "emblem":
        return "emblem", (f'<div class="wash"></div><div class="splat"></div><div class="big brush">{b}</div>'
                          f'<div class="tag">{e(p["line"])}<small>{b} · {e(cfg["brand_kr"])}</small></div>')
    return "quote", (f'<div class="mark brush">{b}</div><div class="center">'
                     f'<div class="latin">{e(p["latin"])}</div><div class="kr">{e(p["kr"])}</div>'
                     f'<div class="line"></div><div class="body">{e(p["body"])}</div></div><div class="sign"><i></i><b>{b}</b></div>')

def main():
    video = "--video" in sys.argv
    force = "--all" in sys.argv
    cfg = json.loads((ROOT / "posts.json").read_text(encoding="utf-8"))
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    out = ROOT / "out"; out.mkdir(exist_ok=True)
    tmp = ROOT / "_page.html"
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i, p in enumerate(cfg["posts"]):
            if not force and (out / f"{p['id']}.jpg").exists():
                continue  # 이미 만든 게시물은 건너뜀 (--all 이면 전부 다시)
            cls, body = content(cfg, p)
            tmp.write_text(tpl.replace("{{cls}}", cls).replace("{{content}}", body).replace("{{seed}}", str(7 + i)), encoding="utf-8")
            pg.goto(tmp.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(400)
            jpg = out / f"{p['id']}.jpg"
            pg.screenshot(path=str(jpg), type="jpeg", quality=93)
            (out / f"{p['id']}_caption.txt").write_text(p["caption"], encoding="utf-8")
            if video and shutil.which("ffmpeg"):
                # 8초, 천천히 줌인하는 릴스용 영상 (음악은 인스타 앱에서 추가)
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(jpg), "-vf",
                    "scale=2160:2700,zoompan=z='min(zoom+0.0006,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=240:s=1080x1350:fps=30,format=yuv420p",
                    "-t", "8", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(out / f"{p['id']}.mp4")], check=True)
            print("done", p["id"])
        b.close()
    tmp.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
