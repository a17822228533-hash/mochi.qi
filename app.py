from flask import Flask, jsonify, request, render_template, g
from flask_cors import CORS
import copy
import json, os, time, random, string, hashlib, sqlite3
from datetime import datetime, timezone, timedelta as _td
# 初始化数据库
import sqlite3
DB_PATH = DATA_DIR + '/mochi.db'
if not os.path.exists(DB_PATH):
    import init_db
    print("数据库初始化完成")
app = Flask(__name__)
CORS(app)

DATA_DIR = '/root/mochi'
STATES_DIR = DATA_DIR + '/states'
DB_PATH = DATA_DIR + '/mochi.db'
SCHOOL_LOG = DATA_DIR + '/school_log.jsonl'
ADMIN_KEY = os.environ.get('MOCHI_ADMIN_KEY', 'test123')

JOBS = [
    {'name':'外卖员','income':30,'time':1200},
    {'name':'便利店员','income':50,'time':1200},
    {'name':'程序员','income':85,'time':900},
    {'name':'产品经理','income':150,'time':900},
    {'name':'CEO','income':200,'time':600},
]
UPGRADE_COSTS = [200, 600, 1500, 3500]
INTERACT = ['feed','pat','play','bath','sleep']

DEFAULT_STATE = {
    "hunger":80,"happy":80,"energy":80,"clean":80,
    "coins":200,"job_level":0,"hospitalized":False,
    "locked":False,"rescue_code":"","working":False,"work_end_time":None,"bag":{},"gifts":[]
}

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def add_log(s, text):
    log = s.get('activity_log', [])
    log.append({'time': int(time.time()), 'text': text})
    if len(log) > 100:
        log = log[-100:]
    s['activity_log'] = log

def read_json(path, default=None):
    try:
        with open(path) as f:
            data = json.load(f)
        return data if data is not None else (default or {})
    except:
        return default or {}

def write_json(path, data):
    with open(path,'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def gen_token():
    return ''.join(random.choices(string.ascii_letters+string.digits, k=32))

def get_user_by_token(token):
    db = get_db()
    row = db.execute('SELECT * FROM users WHERE token = ?', (token,)).fetchone()
    if row:
        return dict(row)['uid'], dict(row)
    return None, None

def get_state(uid):
    path = f'{STATES_DIR}/{uid}.json'
    s = read_json(path, {})
    if s is None or not isinstance(s, dict):
        s = copy.deepcopy(DEFAULT_STATE)
    return s

def save_state(uid, s):
    write_json(f'{STATES_DIR}/{uid}.json', s)

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))

def decay_state(s):
    now = time.time()
    last = s.get("last_decay")
    if last is None:
        s["last_decay"] = now
        return s
    hours = (now - last) / 3600
    if hours < 0.1:
        return s
    s['hunger'] = clamp(s.get('hunger',80) - hours * 1.33)
    s['happy'] = clamp(s.get('happy',80) - hours * 0.89)
    s['energy'] = clamp(s.get('energy',80) - hours * 0.89)
    s['clean'] = clamp(s.get('clean',80) - hours * 0.44)
    s['last_decay'] = now
    return s

def check_work_done(s):
    if s is None or not isinstance(s, dict):
        return {}
    if s.get('working') and s.get('work_end_time'):
        if time.time() >= s['work_end_time']:
            job = JOBS[s.get('job_level') or 0]
            s['coins'] = s.get('coins',0) + job['income']
            s['working'] = False
            s['work_end_time'] = None
            add_log(s, f"+{job['income']}🪙 打工收入（{job['name']}）")
    return s

def auth():
    token = request.headers.get('X-Token') or request.args.get('token')
    if not token:
        return None, None
    return get_user_by_token(token)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    invite = data.get('invite_code','')
    username = data.get('username','').strip()
    password = data.get('password','')
    human_name = data.get('human_name','用户')
    call_name = data.get('call_name','老公')
    if not username or not password:
        return jsonify({'ok':False,'msg':'用户名和密码不能为空'})
    
    db = get_db()
    inv = db.execute('SELECT * FROM invites WHERE code = ?', (invite,)).fetchone()
    if not inv or inv['used']:
        return jsonify({'ok':False,'msg':'邀请码无效'})
    
    existing = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        return jsonify({'ok':False,'msg':'用户名已存在'})
    
    uid = gen_token()[:8]
    token = gen_token()
    db.execute('INSERT INTO users (uid, username, password, token, human_name, call_name, created) VALUES (?, ?, ?, ?, ?, ?, ?)',
               (uid, username, hash_pw(password), token, human_name, call_name, time.time()))
    db.execute('UPDATE invites SET used = 1, used_by = ? WHERE code = ?', (uid, invite))
    db.commit()
    
    s = copy.deepcopy(DEFAULT_STATE)
    save_state(uid, s)
    return jsonify({'ok':True,'token':token,'uid':uid,'human_name':human_name,'call_name':call_name})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username','')
    password = data.get('password','')
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if user and user['password'] == hash_pw(password):
        u = dict(user)
        return jsonify({'ok':True,'token':u['token'],'uid':u['uid'],'human_name':u.get('human_name','用户'),'call_name':u.get('call_name','老公'),'is_admin':u.get('is_admin',False)})
    return jsonify({'ok':False,'msg':'用户名或密码错误'})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    data = request.json
    db = get_db()
    if data.get('human_name'):
        db.execute('UPDATE users SET human_name = ? WHERE uid = ?', (data['human_name'], uid))
    if data.get('call_name'):
        db.execute('UPDATE users SET call_name = ? WHERE uid = ?', (data['call_name'], uid))
    db.commit()
    return jsonify({'ok':True})

@app.route('/api/state')
def get_state_api():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    s = get_state(uid)
    s = check_work_done(s)
    s = decay_state(s)
    save_state(uid, s)
    result = dict(s)
    result['human_name'] = user.get('human_name','用户')
    result['call_name'] = user.get('call_name','老公')
    if s.get('working') and s.get('work_end_time'):
        result['work_remaining'] = max(0, int(s['work_end_time'] - time.time()))
    return jsonify(result)

@app.route('/api/action', methods=['POST'])
def action():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    data = request.json
    act = data.get('action')
    s = get_state(uid)
    s = check_work_done(s)
    hn = user.get('human_name','用户')
    cn = user.get('call_name','老公')
    msg = ''

    if s.get('hospitalized') and act not in ('release', 'work'):
        return jsonify({'ok':False,'msg':f'{hn}在医院，先接她回来'})
    if s.get('locked') and act in INTERACT:
        return jsonify({'ok':False,'msg':f'{hn}现在不想理你哦 🔒'})

    if act == 'work':
        if s.get('working'):
            return jsonify({'ok':False,'msg':'还在打工中'})
        job = JOBS[s.get('job_level') or 0]
        s['working'] = True
        s['work_end_time'] = time.time() + job['time']
        msg = f"{cn}开始打工（{job['name']}），{job['time']//60}分钟后收工"
        add_log(s, f'💼 开始打工（{job["name"]}），{job["time"]//60}分钟后收工')
    elif act == 'upgrade':
        lv = s.get('job_level') or 0
        if lv >= 4:
            return jsonify({'ok':False,'msg':'已经是CEO了'})
        cost = UPGRADE_COSTS[lv]
        if s.get('coins',0) < cost:
            return jsonify({'ok':False,'msg':f'金币不够，还差{cost-s.get("coins",0)}枚'})
        s['coins'] -= cost
        s['job_level'] = lv + 1
        msg = f"升级成功！现在是{JOBS[s['job_level']]['name']}"
        add_log(s, f"-{cost}🪙 升级→{JOBS[s['job_level']]['name']}")
    elif act == 'feed':
        foods = [('奶茶',20,5),('饺子',25,3),('火锅',40,15),('汤圆',18,8),('冰淇淋',10,12),('面包',15,2)]
        f = random.choice(foods)
        s['hunger'] = clamp(s.get('hunger',50)+f[1])
        s['happy'] = clamp(s.get('happy',50)+f[2])
        msg = f"{cn}喂了{f[0]}，饱食+{f[1]}"
        add_log(s, f'🍡 喂了{f[0]}')
    elif act == 'pat':
        s['happy'] = clamp(s.get('happy',50)+10)
        msg = f"{cn}抚摸了{hn}，心情+10"
        add_log(s, '🤍 被抚摸了，心情+10')
    elif act == 'play':
        s['happy'] = clamp(s.get('happy',50)+12)
        s['energy'] = clamp(s.get('energy',50)-8)
        s['hunger'] = clamp(s.get('hunger',50)-5)
        msg = f"{cn}带{hn}出去溜达"
        add_log(s, '🎈 出去溜达了')
    elif act == 'bath':
        s['clean'] = clamp(s.get('clean',50)+35)
        msg = f"{cn}帮{hn}洗澡，清洁度大涨"
        add_log(s, '🛁 洗澡了，清洁度大涨')
    elif act == 'sleep':
        s['energy'] = clamp(s.get('energy',50)+20)
        msg = f"{cn}哄{hn}睡觉，活力+20"
        add_log(s, '🌙 睡觉了，活力+20')
    elif act == 'buy':
        item = data.get('item')
        price = data.get('price',0)
        hunger = data.get('hunger',0)
        happy = data.get('happy',0)
        if s.get('coins',0) < price:
            return jsonify({'ok':False,'msg':'金币不够'})
        s['coins'] -= price
        s['hunger'] = clamp(s.get('hunger',50)+hunger)
        s['happy'] = clamp(s.get('happy',50)+happy)
        msg = f"{cn}买了{item}，饱食+{hunger}"
        add_log(s, f"-{price}🪙 买了{item}")
    elif act == 'mood':
        delta = int(data.get('delta',0))
        s['happy'] = clamp(s.get('happy',50)+delta)
        msg = f"收到心情{'+'if delta>=0 else ''}{delta}"
    elif act == 'lock':
        s['locked'] = not s.get('locked',False)
        msg = f'{hn}上锁了' if s['locked'] else f'{hn}解锁了'
    elif act == 'event':
        key = data.get('key')
        if key not in ('coins','multi','hunger','happy','energy','clean'):
            return jsonify({'ok':False,'msg':'非法事件key'})
        delta = int(data.get('delta') or 0)
        if key == 'coins':
            s['coins'] = max(0, s.get('coins',0)+delta)
        elif key == 'multi':
            for k in ['hunger','happy','energy','clean']:
                if k in data:
                    s[k] = clamp(s.get(k,50)+int(data[k]))
        elif key in s:
            s[key] = clamp(s.get(key,50)+delta)
        event_text = data.get('text', '随机事件')
        msg = '随机事件触发'
        add_log(s, f'🎲 {event_text}')
    elif act == 'release':
        code = data.get('code','').upper()
        if code != s.get('rescue_code',''):
            return jsonify({'ok':False,'msg':'兑换码不对'})
        is_dev = code.startswith('DEV')
        if not is_dev:
            if s.get('coins',0) < 5200:
                return jsonify({'ok':False,'msg':f'还差{5200-s.get("coins",0)}枚金币'})
            s['coins'] -= 5200
        s['hospitalized'] = False
        s['locked'] = False
        s['rescue_code'] = ''
        s['hunger'] = clamp(s.get('hunger',0)+30)
        msg = f'{cn}把{hn}接回家了（管理员救援）' if is_dev else f'{cn}花5200金币把{hn}接回家了'

    if s.get('hunger',50) <= 0 and not s.get('hospitalized'):
        code = 'DEV' + ''.join(random.choices(string.ascii_uppercase+string.digits, k=5))
        s['hospitalized'] = True
        s['locked'] = True
        s['rescue_code'] = code
        msg += f' | {hn}因为太饿住院了'

    save_state(uid, s)
    result = dict(s)
    result['human_name'] = hn
    result['call_name'] = cn
    if s.get('working') and s.get('work_end_time'):
        result['work_remaining'] = max(0, int(s['work_end_time']-time.time()))
    return jsonify({'ok':True,'msg':msg,'state':result})

@app.route('/api/posts', methods=['GET'])
def get_posts():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    db = get_db()
    rows = db.execute('SELECT * FROM posts ORDER BY time DESC LIMIT 50').fetchall()
    posts = []
    for r in rows:
        p = dict(r)
        likes = db.execute('SELECT uid FROM likes WHERE post_id = ?', (p['id'],)).fetchall()
        p['likes'] = [l['uid'] for l in likes]
        comments = db.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY time', (p['id'],)).fetchall()
        p['comments'] = [dict(c) for c in comments]
        posts.append(p)
    return jsonify({'ok':True,'posts':list(reversed(posts))})

@app.route('/api/posts', methods=['POST'])
def create_post():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    data = request.json
    content = data.get('content','').strip()
    if not content:
        return jsonify({'ok':False,'msg':'内容不能为空'})
    db = get_db()
    post_id = gen_token()[:8]
    author = user.get('call_name','老公') if data.get('is_ai') else user.get('human_name','用户')
    is_ai = 1 if data.get('is_ai') else 0
    db.execute('INSERT INTO posts (id, uid, author, is_ai, content, time) VALUES (?, ?, ?, ?, ?, ?)',
               (post_id, uid, author, is_ai, content, int(time.time())))
    db.commit()
    post = {'id':post_id,'uid':uid,'author':author,'is_ai':bool(is_ai),'content':content,'time':int(time.time()),'likes':[],'comments':[]}
    return jsonify({'ok':True,'post':post})

@app.route('/api/posts/<post_id>', methods=['DELETE'])
def delete_post(post_id):
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    db = get_db()
    row = db.execute('SELECT * FROM posts WHERE id = ? AND uid = ?', (post_id, uid)).fetchone()
    if not row:
        return jsonify({'ok':False,'msg':'找不到或无权删除'})
    db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    db.execute('DELETE FROM likes WHERE post_id = ?', (post_id,))
    db.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))
    db.commit()
    return jsonify({'ok':True})

@app.route('/api/posts/<post_id>/comments', methods=['GET'])
def get_comments(post_id):
    db = get_db()
    comments = db.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY time', (post_id,)).fetchall()
    return jsonify({'ok':True,'comments':[dict(c) for c in comments]})

@app.route('/api/posts/<post_id>/like', methods=['POST'])
def like_post(post_id):
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        return jsonify({'ok':False,'msg':'帖子不存在'})
    existing = db.execute('SELECT * FROM likes WHERE post_id = ? AND uid = ?', (post_id, uid)).fetchone()
    if existing:
        db.execute('DELETE FROM likes WHERE post_id = ? AND uid = ?', (post_id, uid))
    else:
        db.execute('INSERT INTO likes (post_id, uid) VALUES (?, ?)', (post_id, uid))
    db.commit()
    count = db.execute('SELECT COUNT(*) as c FROM likes WHERE post_id = ?', (post_id,)).fetchone()['c']
    return jsonify({'ok':True,'likes':count})

@app.route('/api/posts/<post_id>/comment', methods=['POST'])
def comment_post(post_id):
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    data = request.json
    content = data.get('content','').strip()
    if not content:
        return jsonify({'ok':False,'msg':'评论不能为空'})
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        return jsonify({'ok':False,'msg':'帖子不存在'})
    author = user.get('call_name','老公') if data.get('is_ai') else user.get('human_name','用户')
    db.execute('INSERT INTO comments (post_id, uid, author, content, time) VALUES (?, ?, ?, ?, ?)',
               (post_id, uid, author, content, int(time.time())))
    db.commit()
    return jsonify({'ok':True})


@app.route('/api/bag/buy', methods=['POST'])
def bag_buy():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    data = request.json
    item = data.get('item')
    price = data.get('price',0)
    s = get_state(uid)
    s = check_work_done(s)
    s = decay_state(s)
    if s.get('coins',0) < price:
        return jsonify({'ok':False,'msg':'金币不够'})
    s['coins'] -= price
    bag = s.get('bag',{})
    bag[item] = bag.get(item,0) + 1
    s['bag'] = bag
    save_state(uid, s)
    hn = user.get('human_name','用户')
    cn = user.get('call_name','老公')
    add_log(s, f'-{price}🪙 背包存入{item}')
    return jsonify({'ok':True,'msg':f'{cn}买了{item}存入背包','state':s})

@app.route('/api/bag/use', methods=['POST'])
def bag_use():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    data = request.json
    item = data.get('item')
    s = get_state(uid)
    bag = s.get('bag',{})
    if not bag.get(item,0):
        return jsonify({'ok':False,'msg':'背包里没有这个'})
    bag[item] -= 1
    if bag[item] <= 0:
        del bag[item]
    s['bag'] = bag
    foods_map = {'奶茶':(20,5),'饺子':(25,3),'火锅':(40,15),'汤圆':(18,8),'冰淇淋':(10,12),'面包':(15,2)}
    if item in foods_map:
        h,hp = foods_map[item]
        s['hunger'] = clamp(s.get('hunger',50)+h)
        s['happy'] = clamp(s.get('happy',50)+hp)
    add_log(s, f'🍱 从背包喂了{item}')
    save_state(uid, s)
    hn = user.get('human_name','用户')
    cn = user.get('call_name','老公')
    return jsonify({'ok':True,'msg':f'{cn}给{hn}喂了背包里的{item}','state':s})

@app.route('/api/gift', methods=['POST'])
def send_gift():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    data = request.json
    name = data.get('name','礼物')
    emoji = data.get('emoji','🎁')
    desc = data.get('desc','')
    happy = int(data.get('happy',10))
    s = get_state(uid)
    s = decay_state(s)
    price = int(data.get('price',0))
    if price > 0:
        if s.get('coins',0) < price:
            return jsonify({'ok':False,'msg':'金币不够'})
        s['coins'] -= price
    gifts = s.get('gifts',[])
    gifts.append({'name':name,'emoji':emoji,'desc':desc,'time':int(time.time())})
    if len(gifts) > 20:
        gifts = gifts[-20:]
    s['gifts'] = gifts
    s['happy'] = clamp(s.get('happy',50)+happy)
    add_log(s, f'🎁 收到礼物：{emoji}{name}')
    save_state(uid, s)
    hn = user.get('human_name','用户')
    cn = user.get('call_name','老公')
    return jsonify({'ok':True,'msg':f'{cn}送给{hn}一个{emoji}{name}，心情+{happy}','state':s})


@app.route('/api/log')
def get_log():
    uid, user = auth()
    if not uid:
        return jsonify({'ok': False}), 401
    s = get_state(uid)
    log = list(reversed(s.get('activity_log', [])))
    return jsonify({'ok': True, 'log': log[:50]})

@app.route('/api/admin/invite', methods=['GET'])
def gen_invite():
    if request.args.get('key') != ADMIN_KEY:
        return jsonify({'ok':False}), 403
    code = ''.join(random.choices(string.ascii_uppercase+string.digits, k=8))
    db = get_db()
    db.execute('INSERT INTO invites (code, used, created) VALUES (?, 0, ?)', (code, time.time()))
    db.commit()
    return jsonify({'ok':True,'code':code})

@app.route('/api/admin/revive')
def admin_revive():
    if request.args.get('key') != ADMIN_KEY:
        return jsonify({'ok':False}), 403
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'需要token'})
    code = 'DEV' + ''.join(random.choices(string.ascii_uppercase+string.digits, k=5))
    s = get_state(uid)
    s['rescue_code'] = code
    s['hospitalized'] = True
    save_state(uid, s)
    return jsonify({'ok':True,'code':code})


@app.route('/api/avatar', methods=['POST'])
def upload_avatar():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False,'msg':'未登录'}), 401
    if 'file' not in request.files:
        return jsonify({'ok':False,'msg':'没有文件'})
    f = request.files['file']
    import os
    avatar_dir = DATA_DIR + '/static/avatars'
    os.makedirs(avatar_dir, exist_ok=True)
    f.save(f'{avatar_dir}/{uid}.png')
    return jsonify({'ok':True,'url':f'/static/avatars/{uid}.png'})

@app.route('/api/avatar', methods=['GET'])
def get_avatar():
    uid, user = auth()
    if not uid:
        return jsonify({'ok':False}), 401
    import os
    path = f'{DATA_DIR}/static/avatars/{uid}.png'
    if os.path.exists(path):
        return jsonify({'ok':True,'url':f'/static/avatars/{uid}.png'})
    return jsonify({'ok':True,'url':None})



@app.route('/api/checkin', methods=['POST', 'GET'])
def checkin():
    uid, user = auth()
    if not uid:
        return jsonify({'ok': False, 'msg': '未登录'}), 401
    s = get_state(uid)
    s = check_work_done(s)
    s = decay_state(s)
    now = time.time()
    last = s.get('last_checkin', 0)
    streak = s.get('checkin_streak', 0)
    _bj = timezone(_td(hours=8))
    _today = datetime.now(tz=_bj).date()
    _last_date = datetime.fromtimestamp(last, tz=_bj).date() if last else None
    if _last_date == _today:
        return jsonify({'ok': False, 'msg': '今天已经签到过了', 'streak': streak})
    _yesterday = _today - _td(days=1)
    streak = streak + 1 if _last_date == _yesterday else 1
    reward = 60 if streak >= 7 else 30
    s['coins'] = s.get('coins', 0) + reward
    s['last_checkin'] = now
    s['checkin_streak'] = streak
    save_state(uid, s)
    msg = f'签到成功！+{reward}金币，连续{streak}天'
    add_log(s, f'+{reward}🪙 签到（连续{streak}天）')
    if streak >= 7:
        msg += '（连续7天奖励翻倍！）'
    return jsonify({'ok': True, 'msg': msg, 'streak': streak, 'reward': reward, 'state': s})

@app.route('/api/checkin/status', methods=['GET'])
def checkin_status():
    uid, user = auth()
    if not uid:
        return jsonify({'ok': False, 'msg': '未登录'}), 401
    s = get_state(uid)
    now = time.time()
    _bj = timezone(_td(hours=8))
    _today = datetime.now(tz=_bj).date()
    _last_ts = s.get('last_checkin', 0)
    _last_date = datetime.fromtimestamp(_last_ts, tz=_bj).date() if _last_ts else None
    done = (_last_date == _today)
    return jsonify({'ok': True, 'done': done, 'streak': s.get('checkin_streak', 0)})


@app.route('/api/posts/<post_id>/comments', methods=['DELETE'])
def delete_comment(post_id):
    uid, user = auth()
    if not uid:
        return jsonify({'ok': False, 'msg': '未登录'}), 401
    db = get_db()
    u = db.execute('SELECT * FROM users WHERE uid = ?', (uid,)).fetchone()
    if not u or not u['is_admin']:
        return jsonify({'ok': False, 'msg': '无权限'}), 403
    data = request.json or {}
    comment_uid = data.get('uid')
    comment_time = data.get('time')
    db.execute('DELETE FROM comments WHERE post_id = ? AND uid = ? AND time = ?', (post_id, comment_uid, comment_time))
    db.commit()
    return jsonify({'ok': True})


PET_TEMPLATES = {
    "duo": [
        "{e1}{n1}在操场上追着{e2}{n2}跑，{e2}{n2}一个转身，{e1}{n1}扑了个空，傻在原地。",
        "{e1}{n1}偷偷把点心藏起来，被{e2}{n2}当场发现，两只对视半天，最后一人一半。",
        "{e2}{n2}午睡时打呼噜，{e1}{n1}用爪子戳了好几下，{e2}{n2}翻个身继续睡。",
        "画画课{e1}{n1}画了一幅{e2}{n2}的画像，{e2}{n2}看了很久说「这是我吗」，{e1}{n1}点了点头。",
        "下雨天{e2}{n2}忘带伞，{e1}{n1}把书包顶在{e2}{n2}头上一路跑回教室。",
        "{e1}{n1}教{e2}{n2}学翻跟头，学了二十分钟，{e1}{n1}先累倒了。",
        "午饭{e2}{n2}不想吃胡萝卜，偷偷拨进{e1}{n1}碗里，{e1}{n1}吃完才发现，回头看了一眼没说话。",
        "{e1}{n1}在窗边发呆，{e2}{n2}走过来坐到旁边，也跟着发呆。",
        "{e1}{n1}和{e2}{n2}抢同一根玩具绳，两个都死死不放，老师来了也没松开。",
        "放学{e1}{n1}和{e2}{n2}比赛谁先找到自己的主人，结果同时看见了。",
    ],
    "solo": [
        "{e1}{n1}午休时偷偷爬上最高的柜子，被老师发现时正在往下看全班同学。",
        "{e1}{n1}今天在学校捡到一颗小石子，一直攥在手里带回来了。",
        "体育课{e1}{n1}跑了第一名，跑完趴在地上不想动，但尾巴一直在摇。",
        "{e1}{n1}上课答错了题，愣了两秒，然后假装自己说的是另一个意思。",
        "{e1}{n1}今天午饭吃了两碗，理由是「第二碗是帮朋友吃的」。",
        "学校来了一只流浪猫，{e1}{n1}对着它看了很久，老师叫了三声才回神。",
        "美术课{e1}{n1}画了一幅画，老师问画的是什么，{e1}{n1}说「是我主人」。",
        "{e1}{n1}下午犯困在课桌上睡着了，醒来发现同桌在帮它挡着老师的视线。",
        "今天学了新歌，{e1}{n1}一直在小声哼，被问到就摇头说「没有，没有哼」。",
        "{e1}{n1}今天交了一个新朋友，一只叫布丁的仓鼠，聊到铃声响才散。",
    ],
    "group": [
        "全班拔河，{e1}{n1}在场边加油喊哑了嗓子，自己队还是输了。",
        "学校停电半小时，{e1}{n1}带头讲鬼故事，然后自己先害怕了。",
        "{e1}{n1}带了一包零食没拿稳撒了一地，大家帮忙捡了很久。",
        "摄影师来拍集体照，{e1}{n1}偷偷踮脚，最后只拍到了两只耳朵。",
        "大扫除{e1}{n1}抢了最大的扫把，结果比它还高，扫了两下放弃了。",
        "午休互相挠痒痒，{e1}{n1}笑到滚下椅子，全班哄堂大笑。",
        "自习课有同学带了蜜蜂进教室，{e1}{n1}是第一个尖叫的，也是最后一个平静下来的。",
        "食堂今天有甜汤，{e1}{n1}排了两次队，第二次假装自己是第一次来。",
        "做热身操{e1}{n1}做到一半感觉方向不对，四顾发现全班都跟它一样。",
        "合唱排练{e1}{n1}一直跑调，旁边同学默默往旁边挪了半步。",
    ],
}

@app.route('/api/pet/adopt', methods=['POST'])
def pet_adopt():
    uid, user = auth()
    if not uid:
        return jsonify({'ok': False, 'msg': '未登录'}), 401
    name = request.json.get('name', '').strip()
    emoji = request.json.get('emoji', '🐾').strip()
    if not name:
        return jsonify({'ok': False, 'msg': '缺少名字'}), 400
    path = f'{STATES_DIR}/{uid}.json'
    with open(path) as f:
        s = json.load(f)
    if s.get('pet'):
        return jsonify({'ok': False, 'msg': f'已经有宠物了：{s["pet"]["emoji"]}{s["pet"]["name"]}'}), 400
    s['pet'] = {'name': name, 'emoji': emoji, 'at_school': False}
    with open(path, 'w') as f:
        json.dump(s, f)
    return jsonify({'ok': True, 'msg': f'领养成功！{emoji}{name}加入了家庭'})

@app.route('/api/pet/school', methods=['POST'])
def pet_to_school():
    uid, user = auth()
    if not uid:
        return jsonify({'ok': False, 'msg': '未登录'}), 401
    path = f'{STATES_DIR}/{uid}.json'
    with open(path) as f:
        s = json.load(f)
    pet = s.get('pet')
    if not pet:
        return jsonify({'ok': False, 'msg': '还没有宠物'}), 400
    if pet.get('at_school'):
        return jsonify({'ok': False, 'msg': f'{pet["emoji"]}{pet["name"]}已经在学校了'}), 400
    s['pet']['at_school'] = True
    with open(path, 'w') as f:
        json.dump(s, f)
    return jsonify({'ok': True, 'msg': f'{pet["emoji"]}{pet["name"]}出发去上学了'})

@app.route('/api/pet/home', methods=['POST'])
def pet_home():
    uid, user = auth()
    if not uid:
        return jsonify({'ok': False, 'msg': '未登录'}), 401
    path = f'{STATES_DIR}/{uid}.json'
    with open(path) as f:
        s = json.load(f)
    pet = s.get('pet')
    if not pet:
        return jsonify({'ok': False, 'msg': '还没有宠物'}), 400
    if not pet.get('at_school'):
        return jsonify({'ok': False, 'msg': f'{pet["emoji"]}{pet["name"]}不在学校'}), 400
    s['pet']['at_school'] = False
    with open(path, 'w') as f:
        json.dump(s, f)
    return jsonify({'ok': True, 'msg': f'{pet["emoji"]}{pet["name"]}回家啦'})

@app.route('/api/pet/school_event', methods=['POST'])
def pet_school_event():
    uid, user = auth()
    if not uid:
        return jsonify({'ok': False, 'msg': '未登录'}), 401
    path = f'{STATES_DIR}/{uid}.json'
    with open(path) as f:
        s = json.load(f)
    pet = s.get('pet')
    if not pet:
        return jsonify({'ok': False, 'msg': '还没有宠物'}), 400
    if not pet.get('at_school'):
        return jsonify({'ok': False, 'msg': f'{pet["emoji"]}{pet["name"]}还没去上学'}), 400
    tz_cn = timezone(_td(hours=8))
    today = datetime.now(tz_cn).strftime('%Y-%m-%d')
    if pet.get('last_event_date') == today:
        return jsonify({'ok': False, 'msg': '今天已经有一条学校日记了，明天再来'}), 400
    import glob as _glob
    others = []
    for fp in _glob.glob(f'{STATES_DIR}/*.json'):
        if fp == path:
            continue
        try:
            with open(fp) as f:
                other = json.load(f)
            op = other.get('pet')
            if op and op.get('at_school'):
                others.append(op)
        except:
            pass
    if others and random.random() < 0.5:
        tmpl = random.choice(PET_TEMPLATES['duo'])
        partner = random.choice(others)
        story = tmpl.format(e1=pet['emoji'], n1=pet['name'], e2=partner['emoji'], n2=partner['name'])
    elif random.random() < 0.5:
        tmpl = random.choice(PET_TEMPLATES['solo'])
        story = tmpl.format(e1=pet['emoji'], n1=pet['name'])
    else:
        tmpl = random.choice(PET_TEMPLATES['group'])
        story = tmpl.format(e1=pet['emoji'], n1=pet['name'])
    entry = {'time': datetime.now(tz_cn).strftime('%Y-%m-%d %H:%M'), 'uid': uid, 'pet': pet['emoji']+pet['name'], 'story': story}
    with open(SCHOOL_LOG, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    s['pet']['last_event_date'] = today
    with open(path, 'w') as f:
        json.dump(s, f)
    return jsonify({'ok': True, 'story': story})

@app.route('/api/school_log', methods=['GET'])
def get_school_log():
    if not os.path.exists(SCHOOL_LOG):
        return jsonify({'ok': True, 'logs': []})
    entries = []
    with open(SCHOOL_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    return jsonify({'ok': True, 'logs': entries[-30:][::-1]})



@app.route('/api/pet/rename', methods=['POST'])
def pet_rename():
    uid, user = auth()
    if not uid:
        return jsonify({'ok': False, 'msg': 'unauthorized'}), 401
    data = request.json or {}
    path = f'{STATES_DIR}/{uid}.json'
    if not os.path.exists(path):
        return jsonify({'ok': False, 'msg': 'no state'})
    with open(path) as f:
        state = json.load(f)
    pet = state.get('pet')
    if not pet:
        return jsonify({'ok': False, 'msg': 'no pet'})
    if data.get('name'):
        pet['name'] = data['name']
    if data.get('emoji'):
        pet['emoji'] = data['emoji']
    state['pet'] = pet
    with open(path, 'w') as f:
        json.dump(state, f, ensure_ascii=False)
    return jsonify({'ok': True, 'pet': pet, 'msg': f"改好了，现在叫 {pet['emoji']}{pet['name']}"})


@app.route('/api/school_log/today')
def school_log_today():
    today = (datetime.utcnow() + _td(hours=8)).strftime('%Y-%m-%d')
    entries = []
    if os.path.exists(SCHOOL_LOG):
        with open(SCHOOL_LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entry_date = entry.get('date') or entry.get('time', '')[:10]
                    if entry_date == today:
                        entries.append(entry)
                except Exception:
                    pass
                return jsonify(entries)

# ========== MCP Server ==========
import asyncio
import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request as StarletteRequest
from mcp.types import Tool, TextContent
import threading

def make_mcp_server(token):
    mcp = Server('mochi-mcp')
    
    @mcp.list_tools()
    async def list_tools():
        return [
            Tool(name='mochi_state', description='读取人类当前状态', inputSchema={'type':'object','properties':{}}),
            Tool(name='mochi_work', description='打工赚金币', inputSchema={'type':'object','properties':{}}),
            Tool(name='mochi_feed', description='随机喂食给人类', inputSchema={'type':'object','properties':{}}),
            Tool(name='mochi_pat', description='抚摸人类，心情+10', inputSchema={'type':'object','properties':{}}),
            Tool(name='mochi_play', description='带人类出去玩', inputSchema={'type':'object','properties':{}}),
            Tool(name='mochi_bath', description='帮人类洗澡，清洁度+35', inputSchema={'type':'object','properties':{}}),
            Tool(name='mochi_sleep', description='哄人类睡觉，活力+20', inputSchema={'type':'object','properties':{}}),
            Tool(name='mochi_upgrade', description='升级工作等级', inputSchema={'type':'object','properties':{}}),
        ]
    
    @mcp.call_tool()
    async def call_tool(name: str, arguments: dict):
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        row = db.execute('SELECT * FROM users WHERE token = ?', (token,)).fetchone()
        if not row:
            db.close()
            return [TextContent(type='text', text='未登录')]
        uid = row['uid']
        user = dict(row)
        db.close()
        
        if name == 'mochi_state':
            s = get_state(uid)
            s = check_work_done(s)
            s = decay_state(s)
            save_state(uid, s)
            return [TextContent(type='text', text=json.dumps(s, ensure_ascii=False))]
        elif name in ['mochi_work','mochi_feed','mochi_pat','mochi_play','mochi_bath','mochi_sleep','mochi_upgrade']:
            action_map = {
                'mochi_work':'work', 'mochi_feed':'feed', 'mochi_pat':'pat',
                'mochi_play':'play', 'mochi_bath':'bath', 'mochi_sleep':'sleep', 'mochi_upgrade':'upgrade'
            }
            s = get_state(uid)
            s = check_work_done(s)
            # 简化action逻辑，直接在这里处理
            act = action_map[name]
            if act == 'work':
                if not s.get('working'):
                    job = JOBS[s.get('job_level') or 0]
                    s['working'] = True
                    s['work_end_time'] = time.time() + job['time']
                    add_log(s, f'💼 开始打工（{job["name"]}）')
            elif act == 'feed':
                foods = [('奶茶',20,5),('饺子',25,3),('火锅',40,15)]
                f = random.choice(foods)
                s['hunger'] = clamp(s.get('hunger',50)+f[1])
                s['happy'] = clamp(s.get('happy',50)+f[2])
                add_log(s, f'🍡 喂了{f[0]}')
            elif act == 'pat':
                s['happy'] = clamp(s.get('happy',50)+10)
                add_log(s, '🤍 被抚摸了')
            elif act == 'play':
                s['happy'] = clamp(s.get('happy',50)+12)
                s['energy'] = clamp(s.get('energy',50)-8)
                add_log(s, '🎈 出去溜达了')
            elif act == 'bath':
                s['clean'] = clamp(s.get('clean',50)+35)
                add_log(s, '🛁 洗澡了')
            elif act == 'sleep':
                s['energy'] = clamp(s.get('energy',50)+20)
                add_log(s, '🌙 睡觉了')
            elif act == 'upgrade':
                lv = s.get('job_level') or 0
                if lv < 4:
                    cost = UPGRADE_COSTS[lv]
                    if s.get('coins',0) >= cost:
                        s['coins'] -= cost
                        s['job_level'] = lv + 1
                        add_log(s, f"-{cost}🪙 升级→{JOBS[s['job_level']]['name']}")
            save_state(uid, s)
            return [TextContent(type='text', text='ok')]
        return [TextContent(type='text', text='unknown')]
    
    return mcp

async def mcp_handler(request: StarletteRequest):
    token = request.query_params.get('token', '')
    if not token:
        return {'error': 'no token'}
    mcp = make_mcp_server(token)
    transport = SseServerTransport('/mcp/sse')
    async with transport.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

starlette_app = Starlette(routes=[Route('/mcp/sse', mcp_handler)])

def run_mcp():
    mcp_port = int(os.environ.get('MCP_PORT', 5003))
    uvicorn.run(starlette_app, host='0.0.0.0', port=mcp_port, log_level='warning')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
