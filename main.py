import json
import threading
import time
import os
import logging
from urllib.request import urlopen, Request
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

HOST = "0.0.0.0"
POLL_INTERVAL = 5
RETRY_DELAY = 5
MAX_HISTORY = 300

history_md5 = []
last_sid_md5 = None
lock_md5 = threading.Lock()

def get_tai_xiu(d1, d2, d3):
    total = d1 + d2 + d3
    return "Xỉu" if total <= 10 else "Tài"

def update_history(history, lock, result):
    with lock:
        history.insert(0, result.copy())
        if len(history) > MAX_HISTORY:
            history.pop()

def poll_md5():
    global last_sid_md5
    url = "https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=g8&gid=vgmn_101"
    while True:
        try:
            req = Request(url, headers={"User-Agent": "Python-Proxy/1.0"})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("status") == "OK" and isinstance(data.get("data"), list):
                for game in data["data"]:
                    if game.get("cmd") == 2006:
                        sid = game.get("sid")
                        d1, d2, d3 = game.get("d1"), game.get("d2"), game.get("d3")
                        md5_code = game.get("hash") or game.get("md5") or game.get("code")

                        if sid and sid != last_sid_md5 and None not in (d1, d2, d3):
                            last_sid_md5 = sid
                            total = d1 + d2 + d3
                            ket_qua = get_tai_xiu(d1, d2, d3)
                            result = {
                                "Phien": sid,
                                "Xuc_xac_1": d1,
                                "Xuc_xac_2": d2,
                                "Xuc_xac_3": d3,
                                "Tong": total,
                                "Ket_qua": ket_qua,
                                "Ma_MD5": md5_code,
                                "id": "S77SIMON"
                            }
                            update_history(history_md5, lock_md5, result)
                            logger.info(f"[MD5] Phiên {sid} - Tổng: {total}, KQ: {ket_qua}, MD5: {md5_code}")

        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu MD5: {e}")
            time.sleep(RETRY_DELAY)

        time.sleep(POLL_INTERVAL)

# FastAPI app
app = FastAPI()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Lịch sử Tài Xỉu MD5</title>
    <style>
        body { font-family: Arial, sans-serif; background:#111; color:#eee; text-align:center; padding:20px; }
        h1 { color:#0ff; }
        table { width:100%; border-collapse:collapse; margin-top:20px; }
        th,td { padding:8px; border:1px solid #333; }
        th { background:#222; color:#0ff; }
        tr:nth-child(even) { background:#1a1a1a; }
        .md5 { font-size:12px; color:#ccc; word-break:break-all; }
    </style>
</head>
<body>
    <h1>Lịch sử Tài Xỉu MD5</h1>
    <div id="history">Đang tải...</div>

    <script>
    async function fetchData(){
        try{
            const res = await fetch('/data');
            const json = await res.json();
            const data = json.data || [];
            let html = '<table><thead><tr><th>Phiên</th><th>Xúc xắc</th><th>Tổng</th><th>Kết quả</th><th>Mã MD5</th></tr></thead><tbody>';
            data.forEach(item=>{
                html += `<tr>
                    <td>${item.Phien}</td>
                    <td>${item.Xuc_xac_1}, ${item.Xuc_xac_2}, ${item.Xuc_xac_3}</td>
                    <td>${item.Tong}</td>
                    <td>${item.Ket_qua}</td>
                    <td class="md5">${item.Ma_MD5}</td>
                </tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('history').innerHTML = html;
        }catch(e){
            document.getElementById('history').innerHTML = '<p style="color:red;">Không tải được dữ liệu API</p>';
        }
    }
    fetchData();
    setInterval(fetchData,10000);
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
@app.get("/txmd5", response_class=HTMLResponse)
def index():
    return HTML_TEMPLATE

@app.get("/data")
def get_data():
    with lock_md5:
        return {"total": len(history_md5), "data": history_md5}

# Main
if __name__ == "__main__":
    import uvicorn
    threading.Thread(target=poll_md5, daemon=True).start()
    uvicorn.run(app, host=HOST, port=int(os.environ.get("PORT", 10000)))