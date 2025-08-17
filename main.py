import json
import threading
import time
import logging
from urllib.request import urlopen, Request
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Cấu hình log
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

POLL_INTERVAL = 5    # Poll mỗi 5s
RETRY_DELAY = 5
MAX_HISTORY = 300    # Lưu tối đa 300 phiên

lock_md5 = threading.Lock()
history_md5 = []     # Lịch sử MD5
last_sid_md5 = None  # Lưu phiên cuối cùng đã xử lý

# ------------------- Hàm xử lý -------------------
def get_tai_xiu(d1, d2, d3):
    total = d1 + d2 + d3
    return "Xỉu" if total <= 10 else "Tài"

def update_history(history, lock, result):
    with lock:
        history.insert(0, result.copy())
        if len(history) > MAX_HISTORY:
            history.pop()

# ------------------- Luồng polling -------------------
def poll_md5():
    global last_sid_md5
    url = "https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=g8&gid=vgmn_101"
    while True:
        try:
            req = Request(url, headers={'User-Agent': 'Python-Proxy/1.0'})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            if data.get('status') == 'OK' and isinstance(data.get('data'), list):
                for game in data['data']:
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

# ------------------- FastAPI -------------------
app = FastAPI()

# Bật CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def start_background_tasks():
    thread_md5 = threading.Thread(target=poll_md5, daemon=True)
    thread_md5.start()
    logger.info("Đã bắt đầu polling dữ liệu MD5.")

@app.get("/txmd5")
def get_tx_md5():
    with lock_md5:
        return JSONResponse(content={
            "total": len(history_md5),
            "data": history_md5
        })

@app.get("/")
def index():
    return {"message": "API Server for TaiXiu MD5 is running", "endpoint": "/txmd5"}