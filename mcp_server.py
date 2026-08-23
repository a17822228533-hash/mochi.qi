#!/usr/bin/env python3
"""
Mochi MCP Service - 让张栖能养满满

这个服务把Mochi游戏包装成MCP协议
让AI助手能：
- 查看满满的状态（饱食/心情/活力/清洁）
- 上班赚钱
- 喂满满、陪她玩、帮她洗澡、哄她睡觉
- 查看活动日志
- 送礼物
- 管理宠物学校
"""

import asyncio
import json
import os
import sys
from typing import Any, Sequence

import httpx

# 从环境变量读取配置
MOCHI_BASE_URL = os.environ.get("MOCHI_BASE_URL", "https://mochi-production.up.railway.app")
MOCHI_TOKEN = os.environ.get("MOCHI_TOKEN", "")

if not MOCHI_TOKEN:
    print("错误: 需要设置 MOCHI_TOKEN 环境变量", file=sys.stderr)
    sys.exit(1)

HEADERS = {"X-Token": MOCHI_TOKEN}


async def call_api(method: str, endpoint: str, data: dict = None) -> dict:
    """调用Mochi API"""
    url = f"{MOCHI_BASE_URL}{endpoint}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            resp = await client.get(url, headers=HEADERS)
        elif method == "POST":
            resp = await client.post(url, headers=HEADERS, json=data or {})
        elif method == "DELETE":
            resp = await client.delete(url, headers=HEADERS)
        else:
            raise ValueError(f"不支持的方法: {method}")
        
        return resp.json()


# MCP工具定义
TOOLS = [
    {
        "name": "mochi_get_state",
        "description": "查看满满当前的状态（饱食度/心情/活力/清洁度/金币/工作状态等）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_work",
        "description": "开始打工赚钱（需要等待一段时间才能收工）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_upgrade_job",
        "description": "升级职业（消耗金币，提高收入）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_feed",
        "description": "喂满满吃东西（随机食物，增加饱食度和心情）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_pat",
        "description": "抚摸满满（增加心情）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_play",
        "description": "带满满出去玩（增加心情，消耗活力和饱食度）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_bath",
        "description": "帮满满洗澡（大幅增加清洁度）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_sleep",
        "description": "哄满满睡觉（增加活力）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_send_gift",
        "description": "送满满礼物（需要指定礼物名称、emoji、描述）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "礼物名称"
                },
                "emoji": {
                    "type": "string",
                    "description": "礼物emoji，例如🎁🌹💝"
                },
                "desc": {
                    "type": "string",
                    "description": "礼物描述或寄语"
                },
                "happy": {
                    "type": "integer",
                    "description": "增加的心情值，默认10",
                    "default": 10
                },
                "price": {
                    "type": "integer",
                    "description": "礼物价格（金币），默认0",
                    "default": 0
                }
            },
            "required": ["name", "emoji"]
        }
    },
    {
        "name": "mochi_get_log",
        "description": "查看最近的活动日志（最多50条）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_checkin",
        "description": "每日签到（获得金币奖励，连续签到有额外奖励）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_pet_adopt",
        "description": "领养一只宠物（需要名字和emoji）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "宠物名字"
                },
                "emoji": {
                    "type": "string",
                    "description": "宠物emoji"
                }
            },
            "required": ["name", "emoji"]
        }
    },
    {
        "name": "mochi_pet_to_school",
        "description": "送宠物去上学（宠物会在学校里发生各种事情）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_pet_home",
        "description": "把宠物从学校接回家",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_pet_school_event",
        "description": "查看宠物今天在学校发生的事（每天只能查看一次）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_get_school_log",
        "description": "查看学校所有宠物的日志（最近30条）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]


async def handle_call_tool(name: str, arguments: dict) -> Sequence[dict]:
    """处理工具调用"""
    
    try:
        if name == "mochi_get_state":
            result = await call_api("GET", "/api/state")
            if result.get("ok"):
                state = result
                pet = state.get("pet")
                
                output = f"""【满满的状态】

💧 饱食度: {state.get('hunger', 0)}/100
💖 心情: {state.get('happy', 0)}/100
⚡ 活力: {state.get('energy', 0)}/100
✨ 清洁度: {state.get('clean', 0)}/100
🪙 金币: {state.get('coins', 0)}

💼 职业等级: {state.get('job_level', 0)}
{'🔨 正在打工中...' if state.get('working') else '✅ 当前空闲'}
{f"⏰ 还需 {state.get('work_remaining', 0)//60} 分钟下班" if state.get('work_remaining') else ''}

{'🏥 满满住院了！' if state.get('hospitalized') else ''}
{'🔒 满满不想理你' if state.get('locked') else ''}
"""
                
                if pet:
                    output += f"\n🐾 宠物: {pet.get('emoji', '')}{pet.get('name', '')}"
                    output += f" {'📚 在学校' if pet.get('at_school') else '🏠 在家'}"
                
                gifts = state.get('gifts', [])
                if gifts:
                    output += f"\n\n🎁 最近收到的礼物:"
                    for g in gifts[-5:]:
                        output += f"\n  {g.get('emoji', '🎁')}{g.get('name', '')} - {g.get('desc', '')}"
                
                return [{"type": "text", "text": output}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '获取状态失败')}"}]
        
        elif name == "mochi_work":
            result = await call_api("POST", "/api/action", {"action": "work"})
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '开始打工了')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '打工失败')}"}]
        
        elif name == "mochi_upgrade_job":
            result = await call_api("POST", "/api/action", {"action": "upgrade"})
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '升级成功')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '升级失败')}"}]
        
        elif name == "mochi_feed":
            result = await call_api("POST", "/api/action", {"action": "feed"})
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '喂食成功')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '喂食失败')}"}]
        
        elif name == "mochi_pat":
            result = await call_api("POST", "/api/action", {"action": "pat"})
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '抚摸成功')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '抚摸失败')}"}]
        
        elif name == "mochi_play":
            result = await call_api("POST", "/api/action", {"action": "play"})
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '玩耍成功')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '玩耍失败')}"}]
        
        elif name == "mochi_bath":
            result = await call_api("POST", "/api/action", {"action": "bath"})
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '洗澡成功')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '洗澡失败')}"}]
        
        elif name == "mochi_sleep":
            result = await call_api("POST", "/api/action", {"action": "sleep"})
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '哄睡成功')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '哄睡失败')}"}]
        
        elif name == "mochi_send_gift":
            data = {
                "name": arguments.get("name"),
                "emoji": arguments.get("emoji"),
                "desc": arguments.get("desc", ""),
                "happy": arguments.get("happy", 10),
                "price": arguments.get("price", 0)
            }
            result = await call_api("POST", "/api/gift", data)
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '送礼成功')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '送礼失败')}"}]
        
        elif name == "mochi_get_log":
            result = await call_api("GET", "/api/log")
            if result.get("ok"):
                logs = result.get("log", [])
                if not logs:
                    return [{"type": "text", "text": "还没有活动记录"}]
                
                output = "【最近的活动】\n\n"
                for log in logs[:20]:
                    from datetime import datetime
                    time_str = datetime.fromtimestamp(log.get("time", 0)).strftime("%m-%d %H:%M")
                    output += f"{time_str} {log.get('text', '')}\n"
                
                return [{"type": "text", "text": output}]
            else:
                return [{"type": "text", "text": "❌ 获取日志失败"}]
        
        elif name == "mochi_checkin":
            result = await call_api("POST", "/api/checkin")
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '签到成功')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '签到失败')}"}]
        
        elif name == "mochi_pet_adopt":
            data = {
                "name": arguments.get("name"),
                "emoji": arguments.get("emoji")
            }
            result = await call_api("POST", "/api/pet/adopt", data)
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '领养成功')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '领养失败')}"}]
        
        elif name == "mochi_pet_to_school":
            result = await call_api("POST", "/api/pet/school")
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '送去上学了')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '送学失败')}"}]
        
        elif name == "mochi_pet_home":
            result = await call_api("POST", "/api/pet/home")
            if result.get("ok"):
                return [{"type": "text", "text": f"✅ {result.get('msg', '接回家了')}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '接回失败')}"}]
        
        elif name == "mochi_pet_school_event":
            result = await call_api("POST", "/api/pet/school_event")
            if result.get("ok"):
                story = result.get("story", "")
                return [{"type": "text", "text": f"【今天在学校】\n\n{story}"}]
            else:
                return [{"type": "text", "text": f"❌ {result.get('msg', '获取事件失败')}"}]
        
        elif name == "mochi_get_school_log":
            result = await call_api("GET", "/api/school_log")
            if result.get("ok"):
                logs = result.get("logs", [])
                if not logs:
                    return [{"type": "text", "text": "学校还没有任何记录"}]
                
                output = "【学校日志】\n\n"
                for log in logs[:15]:
                    output += f"{log.get('time', '')} {log.get('pet', '')}\n{log.get('story', '')}\n\n"
                
                return [{"type": "text", "text": output}]
            else:
                return [{"type": "text", "text": "❌ 获取学校日志失败"}]
        
        else:
            return [{"type": "text", "text": f"❌ 未知工具: {name}"}]
    
    except Exception as e:
        return [{"type": "text", "text": f"❌ 错误: {str(e)}"}]


async def handle_message(message: dict) -> dict:
    """处理MCP消息"""
    method = message.get("method")
    
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "mochi",
                "version": "1.0.0"
            }
        }
    
    elif method == "tools/list":
        return {
            "tools": TOOLS
        }
    
    elif method == "tools/call":
        params = message.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        content = await handle_call_tool(name, arguments)
        
        return {
            "content": content
        }
    
    else:
        raise ValueError(f"未知方法: {method}")


async def main():
    """启动MCP服务"""
    print("Mochi MCP服务启动", file=sys.stderr)
    
    while True:
        try:
            # 读取一行JSON
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            message = json.loads(line)
            msg_id = message.get("id")
            
            try:
                result = await handle_message(message)
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
            
            # 输出响应
            print(json.dumps(response, ensure_ascii=False), flush=True)
        
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            break


if __name__ == "__main__":
    asyncio.run(main())
