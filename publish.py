"""posts.json에서 status가 approved인 다음 게시물 하나를 인스타그램에 올린다.

필요한 환경 변수 (GitHub Secrets에 저장):
  IG_USER_ID       인스타그램 프로페셔널 계정 ID
  IG_ACCESS_TOKEN  Instagram API (Instagram 로그인 방식) 장기 액세스 토큰
  MEDIA_BASE_URL   out/ 폴더가 공개로 열려 있는 주소. 예) https://raw.githubusercontent.com/<아이디>/<저장소>/main/out
선택:
  IG_POST_AS       "image"(기본) 또는 "reel"
  GRAPH_VERSION    기본 v25.0
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
API = f"https://graph.instagram.com/{os.environ.get('GRAPH_VERSION', 'v25.0')}"

def call(path, params, method="POST"):
    data = urllib.parse.urlencode({**params, "access_token": os.environ["IG_ACCESS_TOKEN"]})
    if method == "GET":
        req = urllib.request.Request(f"{API}/{path}?{data}")
    else:
        req = urllib.request.Request(f"{API}/{path}", data=data.encode(), method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def main():
    cfg_path = ROOT / "posts.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    post = next((p for p in cfg["posts"] if p.get("status") == "approved"), None)
    if not post:
        print("올릴 approved 게시물이 없습니다."); return
    uid, base = os.environ["IG_USER_ID"], os.environ["MEDIA_BASE_URL"].rstrip("/")
    as_reel = os.environ.get("IG_POST_AS", "image") == "reel"
    caption = post["caption"]

    if as_reel:
        c = call(f"{uid}/media", {"media_type": "REELS", "video_url": f"{base}/{post['id']}.mp4", "caption": caption})
    else:
        c = call(f"{uid}/media", {"image_url": f"{base}/{post['id']}.jpg", "caption": caption})
    cid = c["id"]
    for _ in range(30):  # 업로드 처리 완료까지 대기 (릴스는 시간이 걸림)
        st = call(cid, {"fields": "status_code"}, method="GET").get("status_code")
        if st == "FINISHED": break
        if st == "ERROR": sys.exit(f"처리 실패: {post['id']}")
        time.sleep(10)
    res = call(f"{uid}/media_publish", {"creation_id": cid})

    post["status"] = "published"
    post["published_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    post["media_id"] = res.get("id")
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"게시 완료: {post['id']} -> {res}")

if __name__ == "__main__":
    main()
