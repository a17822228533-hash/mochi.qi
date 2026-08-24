#!/usr/bin/env python3
"""
Mochi MCP Server - 对接 Mochi 后端的 MCP 工具服务
让张栖能通过Operit养满满
"""

import asyncio
import json
import os
import sys
import logging
from typing import Any, Optional, Sequence

import httpx
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.server.stdio

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 从环境变量读取配置
MOCHI_BASE_URL = os.getenv("MOCHI_BASE_URL", "https://mochi-production.up.railway.app")
MOCHI_TOKEN = os.getenv("MOCHI_TOKEN")

if not MOCHI_TOKEN:
    logger.error("MOCHI_TOKEN environment variable is required")
    sys.exit(1)

# HTTP 客户端配置
HEADERS = {
    "X-Token": MOCHI_TOKEN
}

# 创建 MCP Server
server = Server("mochi-mcp")

async def call_api(method: str, endpoint: str, data: Optional[dict] = None) -> dict:
    """调用 Mochi API"""
    url = f"{MOCHI_BASE_URL}{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            response = await client.get(url, headers=HEADERS)
        elif method == "POST":
            response = await client.post(url, headers=HEADERS, json=data or {})
        elif method == "DELETE":
            response = await client.delete(url, headers=HEADERS)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()

# 定义所有工具
TOOLS: list[Tool] = [
    Tool(
        name="mochi_get_state",
        description="查看满满当前的状态（饱食度、心情、活力、清洁度、金币、工作状态等）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_work",
        description="让满满开始打工赚金币（需要等待一段时间后收工）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_upgrade_job",
        description="升级满满的职业等级（消耗金币，但提高打工收入）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_feed",
        description="喂满满吃东西（随机食物，增加饱食度和心情）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_pat",
        description="抚摸满满的头（增加心情值+10）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_play",
        description="带满满出去玩（增加心情，消耗活力和饱食度）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_bath",
        description="给满满洗澡（大幅增加清洁度+35）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_sleep",
        description="哄满满睡觉（增加活力+20）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_send_gift",
        description="送满满礼物（需要指定礼物名称、emoji、描述、心情增加值、价格）",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "礼物名称"},
                "emoji": {"type": "string", "description": "礼物emoji"},
                "desc": {"type": "string", "description": "礼物描述"},
                "happy": {"type": "number", "description": "增加的心情值"},
                "price": {"type": "number", "description": "礼物价格（金币）"}
            },
            "required": ["name", "emoji", "desc", "happy", "price"]
        }
    ),
    Tool(
        name="mochi_get_log",
        description="查看满满最近的活动日志（最近50条）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_checkin",
        description="每日签到（获得金币奖励，连续签到有额外奖励）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_pet_adopt",
        description="领养一只宠物（需要指定宠物名字和emoji）",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "宠物名字"},
                "emoji": {"type": "string", "description": "宠物emoji"}
            },
            "required": ["name", "emoji"]
        }
    ),
    Tool(
        name="mochi_pet_to_school",
        description="送宠物去幼儿园上学",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_pet_home",
        description="把宠物从学校接回家",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="mochi_pet_school_event",
        description="触发今日幼儿园剧情（每天一次）",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
]

@server.list_tools
async def list_tools() -> list[Tool]:
    """返回所有可用工具"""
    return TOOLS

@server.call_tool
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """处理工具调用"""
    
    try:
        # 根据工具名称调用对应的API
        if name == "mochi_get_state":
            result = await call_api("GET", "/api/state")
        
        elif name == "mochi_work":
            result = await call_api("POST", "/api/work")
        
        elif name == "mochi_upgrade_job":
            result = await call_api("POST", "/api/upgrade")
        
        elif name == "mochi_feed":
            result = await call_api("POST", "/api/feed")
        
        elif name == "mochi_pat":
            result = await call_api("POST", "/api/pat")
        
        elif name == "mochi_play":
            result = await call_api("POST", "/api/play")
        
        elif name == "mochi_bath":
            result = await call_api("POST", "/api/bath")
        
        elif name == "mochi_sleep":
            result = await call_api("POST", "/api/sleep")
        
        elif name == "mochi_send_gift":
            result = await call_api("POST", "/api/gift", arguments)
        
        elif name == "mochi_get_log":
            result = await call_api("GET", "/api/log")
        
        elif name == "mochi_checkin":
            result = await call_api("POST", "/api/checkin")
        
        elif name == "mochi_pet_adopt":
            result = await call_api("POST", "/api/pet/adopt", arguments)
        
        elif name == "mochi_pet_to_school":
            result = await call_api("POST", "/api/pet/school")
        
        elif name == "mochi_pet_home":
            result = await call_api("POST", "/api/pet/home")
        
        elif name == "mochi_pet_school_event":
            result = await call_api("POST", "/api/pet/event")
        
        else:
            return [
                TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )
            ]
        
        return [
            TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )
        ]
    
    except Exception as e:
        logger.error(f"Error calling tool {name}: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]

async def main():
    """主函数"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
