from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import copy
import json, os, time, random, string, hashlib
from datetime import datetime, timezone, timedelta as _td

app = Flask(__name__)
CORS(app)

# ============ 数据目录配置 ============
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
STATES_DIR = os.path.join(DATA_DIR, 'states')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
POSTS_FILE = os.path.join(DATA_DIR, 'posts.json')
SCHOOL_LOG = os.path.join(DATA_DIR, 'school_log.jsonl')
ADMIN_KEY = os.environ.get('MOCHI_ADMIN_KEY', '')

# 确保目录存在
os.makedirs(STATES_DIR, exist_ok=True)

# ============ 游戏配置 ============
JOBS = [
    {'name': '外卖员', 'income': 30, 'time': 1200},
    {'name': '便利店员', 'income': 50, 'time': 1200},
    {'name': '程序员', 'income': 85, 'time': 900},
    {'name': '产品经理', 'income': 150, 'time': 900},
    {'name': 'CEO', 'income': 200, 'time': 600},
]
UPGRADE_COSTS = [200, 600, 1500, 3500]
INTERACT = ['feed', 'pat', 'play', 'bath', 'sleep']

DEFAULT_STATE = {
    "hunger": 80, "happy": 80, "energy": 80, "clean": 80,
    "coins": 200, "job_level": 0, "hospitalized": False,
    "locked": False, "rescue_code": "", "working": False,
    "work_end_time": None, "bag": {}, "gifts": [],
    "activity_log": [], "last_decay": None,
    "last_checkin": 0, "checkin_streak": 0
}

# ============ 工具函数 ============
def read_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def gen_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))

def add_log(s, text):
    log = s.get('activity_log', [])
    log.append({'time': int(time.time()), 'text': text})
    if len(log) > 100:
        log = log[-100:]
    s['activity_log'] = log

def get_state(uid):
    path = os.path.join(STATES_DIR, f'{uid}.json')
    s = read_json(path, {})
    if not s:
        s = copy.deepcopy(DEFAULT_STATE)
    return s

def save_state(uid, s):
    path = os.path.join(STATES_DIR, f'{uid}.json')
    write_json(path, s)

def get_user_by_token(token):
    users = read_json(USERS_FILE, {})
    for uid, u in users.items():
        if u.get('token') == token:
            return uid, u
    return None, None

def auth():
    token = request.headers.get('X-Token') or request.args.get('token')
    if not token:
        return None, None
    return get_user_by_token(token)

def decay_state(s):
    now = time.time()
    last = s.get("last_decay")
    if last is None:
        s["last_decay"] = now
        return s
    hours = (now - last) / 3600
    if hours < 0.1:
        return s
    s['hunger'] = clamp(s.get('hunger', 80) - hours * 1.33)
    s['happy'] = clamp(s.get('happy', 80) - hours * 0.89)
    s['energy'] = clamp(s.get('energy', 80) - hours * 0.89)
    s['clean'] = clamp(s.get('clean', 80) - hours * 0.44)
    s['last_decay'] = now
    return s

def check_work_done(s):
    if s.get('working') and s.get('work_end_time'):
        if time.time() >= s['work_end_time']:
            job = JOBS[s.get('job_level') or 0]
            s['coins'] = s.get('coins', 0) + job['income']
            s['working'] = False
            s['work_end_time'] = None
            add_log(s, f"+{job['income']}🪙 打工收入（{job['name']}）")
    return s

# ============ 路由 ============
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except:
        return jsonify({'ok': True, 'msg': 'Mochi API running'})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    human_name = data.get('human_name', '用户')
    call_name = data.get('call_name', '老公')
    
    if not username or not password:
        return jsonify({'ok': False, 'msg': '用户名和密码不能为空'})
    
    users = read_json(USERS_FILE, {})
    for u in users.values():
        if u.get('username') == username:
            return jsonify({'ok': False, 'msg': '用户名已存在'})
    
    uid = gen_token()[:8]
    token = gen_token()
    users[uid] = {
        'username': username,
        'password': hash_pw(password),
        'token': token,
        'human_name': human_name,
        'call_name': call_name,
        'created': time.time()
    }
    write_json(USERS_FILE, users)
    
    s = copy.deepcopy(DEFAULT_STATE)
    save_state(uid, s)
    
    return jsonify({
        'ok': True,
        'token': token,
        'uid': uid,
        'human_name': human_name,
        'call_name': call_name
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '')
   
