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
            "type": "obje
