#!/usr/bin/env python3
"""
Mochi MCP Service - SSE版本
让张栖能通过Operit养满满
"""

import asyncio
import json
import os
import sys
from typing import Any

import httpx
from starlette.applications import Starlette
from starlette.responses import StreamingResponse
from starlette.routing import Route
import uvicorn

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
                "name": {"type": "string", "description": "礼物名称"},
                "emoji": {"type": "string", "description": "礼物emoji"},
                "desc": {"type": "string", "description": "礼物描述或寄语"},
                "happy": {"type": "integer", "description": "增加的心情值", "default": 10},
                "price": {"type": "integer", "description": "礼物价格（金币）", "default": 0}
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
        "description": "每日签到（获得金币奖励）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_pet_adopt",
        "description": "领养宠物",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "emoji": {"type": "string"}
            },
            "required": ["name", "emoji"]
        }
    },
    {
        "name": "mochi_pet_to_school",
        "description": "送宠物去上学",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_pet_home",
        "description": "接宠物回家",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mochi_pet_school_event",
        "description": "触发今日幼儿园剧情",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


async def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """处理工具调用"""
    
    if tool_name == "mochi_get_state":
        result = await call_api("GET", "/api/state")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
    
    elif tool_name == "mochi_work":
        result = await call_api("POST", "/api/work")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_upgrade_job":
        result = await call_api("POST", "/api/upgrade")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_feed":
        result = await call_api("POST", "/api/feed")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_pat":
        result = await call_api("POST", "/api/pat")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_play":
        result = await call_api("POST", "/api/play")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_bath":
        result = await call_api("POST", "/api/bath")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_sleep":
        result = await call_api("POST", "/api/sleep")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_send_gift":
        result = await call_api("POST", "/api/gift", arguments)
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_get_log":
        result = await call_api("GET", "/api/log")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
    
    elif tool_name == "mochi_checkin":
        result = await call_api("POST", "/api/checkin")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_pet_adopt":
        result = await call_api("POST", "/api/pet/adopt", arguments)
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_pet_to_school":
        result = await call_api("POST", "/api/pet/school")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_pet_home":
        result = await call_api("POST", "/api/pet/home")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    elif tool_name == "mochi_pet_school_event":
        result = await call_api("POST", "/api/pet/event")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    
    else:
        return {"content": [{"type": "text", "text": f"未知工具: {tool_name}"}], "isError": True}


async def sse_stream(request):
    """SSE端点 - 处理MCP协议"""
    
    async def event_generator():
        """生成SSE事件流"""
        
        # 发送初始化消息
        init_msg = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "mochi-mcp",
                    "version": "1.0.0"
                }
            }
        }
        yield f"data: {json.dumps(init_msg)}\n\n"
        
        # 发送工具列表
        tools_msg = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "result": {
                "tools": TOOLS
            }
        }
        yield f"data: {json.dumps(tools_msg)}\n\n"
        
        # 保持连接并等待客户端请求
        # 注: 实际的请求处理需要通过另一个endpoint接收
        while True:
            await asyncio.sleep(30)
            # 发送心跳
            yield f": heartbeat\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


async def handle_request(request):
    """处理客户端的工具调用请求"""
    body = await request.json()
    
    if body.get("method") == "tools/call":
        tool_name = body["params"]["name"]
        arguments = body["params"].get("arguments", {})
        
        result = await handle_tool_call(tool_name, arguments)
        
        response = {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": result
        }
        
        return json.dumps(response)
    
    return json.dumps({"error": "Unknown method"})


# 创建Starlette应用
app = Starlette(
    routes=[
        Route("/sse", sse_stream),
        Route("/call", handle_request, methods=["POST"]),
    ]
)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8766))
    uvicorn.run(app, host="0.0.0.0", port=port)
