[android] Content of /storage/emulated/0/Download/mochi_mcp_service.py:
  1| #!/usr/bin/env python3
  2| """
  3| Mochi MCP Service - 让张栖能养满满
  4| 
  5| 这个服务把Mochi游戏包装成MCP协议
  6| 让AI助手能：
  7| - 查看满满的状态（饱食/心情/活力/清洁）
  8| - 上班赚钱
  9| - 喂满满、陪她玩、帮她洗澡、哄她睡觉
 10| - 查看活动日志
 11| - 送礼物
 12| - 管理宠物学校
 13| """
 14| 
 15| import asyncio
 16| import json
 17| import os
 18| import sys
 19| from typing import Any
 20| 
 21| import httpx
 22| from mcp.server import Server
 23| from mcp.server.stdio import stdio_server
 24| from mcp.types import Tool, TextContent
 25| 
 26| # 从环境变量读取配置
 27| MOCHI_BASE_URL = os.environ.get("MOCHI_BASE_URL", "https://mochi-production.up.railway.app")
 28| MOCHI_TOKEN = os.environ.get("MOCHI_TOKEN", "")
 29| 
 30| if not MOCHI_TOKEN:
 31|     print("错误: 需要设置 MOCHI_TOKEN 环境变量", file=sys.stderr)
 32|     sys.exit(1)
 33| 
 34| server = Server("mochi")
 35| 
 36| HEADERS = {"X-Token": MOCHI_TOKEN}
 37| 
 38| 
 39| async def call_api(method: str, endpoint: str, data: dict = None) -> dict:
 40|     """调用Mochi API"""
 41|     url = f"{MOCHI_BASE_URL}{endpoint}"
 42|     async with httpx.AsyncClient(timeout=30.0) as client:
 43|         if method == "GET":
 44|             resp = await client.get(url, headers=HEADERS)
 45|         elif method == "POST":
 46|             resp = await client.post(url, headers=HEADERS, json=data or {})
 47|         elif method == "DELETE":
 48|             resp = await client.delete(url, headers=HEADERS)
 49|         else:
 50|             raise ValueError(f"不支持的方法: {method}")
 51|         
 52|         return resp.json()
 53| 
 54| 
 55| @server.list_tools()
 56| async def list_tools() -> list[Tool]:
 57|     """列出所有可用工具"""
 58|     return [
 59|         Tool(
 60|             name="mochi_get_state",
 61|             description="查看满满当前的状态（饱食度/心情/活力/清洁度/金币/工作状态等）",
 62|             inputSchema={
 63|                 "type": "object",
 64|                 "properties": {},
 65|                 "required": []
 66|             }
 67|         ),
 68|         Tool(
 69|             name="mochi_work",
 70|             description="开始打工赚钱（需要等待一段时间才能收工）",
 71|             inputSchema={
 72|                 "type": "object",
 73|                 "properties": {},
 74|                 "required": []
 75|             }
 76|         ),
 77|         Tool(
 78|             name="mochi_upgrade_job",
 79|             description="升级职业（消耗金币，提高收入）",
 80|             inputSchema={
 81|                 "type": "object",
 82|                 "properties": {},
 83|                 "required": []
 84|             }
 85|         ),
 86|         Tool(
 87|             name="mochi_feed",
 88|             description="喂满满吃东西（随机食物，增加饱食度和心情）",
 89|             inputSchema={
 90|                 "type": "object",
 91|                 "properties": {},
 92|                 "required": []
 93|             }
 94|         ),
 95|         Tool(
 96|             name="mochi_pat",
 97|             description="抚摸满满（增加心情）",
 98|             inputSchema={
 99|                 "type": "object",
100|                 "properties": {},
101|                 "required": []
102|             }
103|         ),
104|         Tool(
105|             name="mochi_play",
106|             description="带满满出去玩（增加心情，消耗活力和饱食度）",
107|             inputSchema={
108|                 "type": "object",
109|                 "properties": {},
110|                 "required": []
111|             }
112|         ),
113|         Tool(
114|             name="mochi_bath",
115|             description="帮满满洗澡（大幅增加清洁度）",
116|             inputSchema={
117|                 "type": "object",
118|                 "properties": {},
119|                 "required": []
120|             }
121|         ),
122|         Tool(
123|             name="mochi_sleep",
124|             description="哄满满睡觉（增加活力）",
125|             inputSchema={
126|                 "type": "object",
127|                 "properties": {},
128|                 "required": []
129|             }
130|         ),
131|         Tool(
132|             name="mochi_send_gift",
133|             description="送满满礼物（需要指定礼物名称、emoji、描述）",
134|             inputSchema={
135|                 "type": "object",
136|                 "properties": {
137|                     "name": {
138|                         "type": "string",
139|                         "description": "礼物名称"
140|                     },
141|                     "emoji": {
142|                         "type": "string",
143|                         "description": "礼物emoji，例如🎁🌹💝"
144|                     },
145|                     "desc": {
146|                         "type": "string",
147|                         "description": "礼物描述或寄语"
148|                     },
149|                     "happy": {
150|                         "type": "integer",
151|                         "description": "增加的心情值，默认10",
152|                         "default": 10
153|                     },
154|                     "price": {
155|                         "type": "integer",
156|                         "description": "礼物价格（金币），默认0",
157|                         "default": 0
158|                     }
159|                 },
160|                 "required": ["name", "emoji"]
161|             }
162|         ),
163|         Tool(
164|             name="mochi_get_log",
165|             description="查看最近的活动日志（最多50条）",
166|             inputSchema={
167|                 "type": "object",
168|                 "properties": {},
169|                 "required": []
170|             }
171|         ),
172|         Tool(
173|             name="mochi_checkin",
174|             description="每日签到（获得金币奖励，连续签到有额外奖励）",
175|             inputSchema={
176|                 "type": "object",
177|                 "properties": {},
178|                 "required": []
179|             }
180|         ),
181|         Tool(
182|             name="mochi_pet_adopt",
183|             description="领养一只宠物（需要名字和emoji）",
184|             inputSchema={
185|                 "type": "object",
186|                 "properties": {
187|                     "name": {
188|                         "type": "string",
189|                         "description": "宠物名字"
190|                     },
191|                     "emoji": {
192|                         "type": "string",
193|                         "description": "宠物emoji"
194|                     }
195|                 },
196|                 "required": ["name", "emoji"]
197|             }
198|         ),
199|         Tool(
200|             name="mochi_pet_to_school",
201|             description="送宠物去上学（宠物会在学校里发生各种事情）",
202|             inputSchema={
203|                 "type": "object",
204|                 "properties": {},
205|                 "required": []
206|             }
207|         ),
208|         Tool(
209|             name="mochi_pet_home",
210|             description="把宠物从学校接回家",
211|             inputSchema={
212|                 "type": "object",
213|                 "properties": {},
214|                 "required": []
215|             }
216|         ),
217|         Tool(
218|             name="mochi_pet_school_event",
219|             description="查看宠物今天在学校发生的事（每天只能查看一次）",
220|             inputSchema={
221|                 "type": "object",
222|                 "properties": {},
223|                 "required": []
224|             }
225|         ),
226|         Tool(
227|             name="mochi_get_school_log",
228|             description="查看学校所有宠物的日志（最近30条）",
229|             inputSchema={
230|                 "type": "object",
231|                 "properties": {},
232|                 "required": []
233|             }
234|         ),
235|     ]
236| 
237| 
238| @server.call_tool()
239| async def call_tool(name: str, arguments: Any) -> list[TextContent]:
240|     """处理工具调用"""
241|     
242|     try:
243|         if name == "mochi_get_state":
244|             result = await call_api("GET", "/api/state")
245|             if result.get("ok"):
246|                 state = result
247|                 pet = state.get("pet")
248|                 
249|                 output = f"""【满满的状态】
250| 
251| 💧 饱食度: {state.get('hunger', 0)}/100
252| 💖 心情: {state.get('happy', 0)}/100
253| ⚡ 活力: {state.get('energy', 0)}/100
254| ✨ 清洁度: {state.get('clean', 0)}/100
255| 🪙 金币: {state.get('coins', 0)}
256| 
257| 💼 职业等级: {state.get('job_level', 0)}
258| {'🔨 正在打工中...' if state.get('working') else '✅ 当前空闲'}
259| {f"⏰ 还需 {state.get('work_remaining', 0)//60} 分钟下班" if state.get('work_remaining') else ''}
260| 
261| {'🏥 满满住院了！' if state.get('hospitalized') else ''}
262| {'🔒 满满不想理你' if state.get('locked') else ''}
263| """
264|                 
265|                 if pet:
266|                     output += f"\n🐾 宠物: {pet.get('emoji', '')}{pet.get('name', '')}"
267|                     output += f" {'📚 在学校' if pet.get('at_school') else '🏠 在家'}"
268|                 
269|                 gifts = state.get('gifts', [])
270|                 if gifts:
271|                     output += f"\n\n🎁 最近收到的礼物:"
272|                     for g in gifts[-5:]:
273|                         output += f"\n  {g.get('emoji', '🎁')}{g.get('name', '')} - {g.get('desc', '')}"
274|                 
275|                 return [TextContent(type="text", text=output)]
276|             else:
277|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '获取状态失败')}")]
278|         
279|         elif name == "mochi_work":
280|             result = await call_api("POST", "/api/action", {"action": "work"})
281|             if result.get("ok"):
282|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '开始打工了')}")]
283|             else:
284|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '打工失败')}")]
285|         
286|         elif name == "mochi_upgrade_job":
287|             result = await call_api("POST", "/api/action", {"action": "upgrade"})
288|             if result.get("ok"):
289|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '升级成功')}")]
290|             else:
291|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '升级失败')}")]
292|         
293|         elif name == "mochi_feed":
294|             result = await call_api("POST", "/api/action", {"action": "feed"})
295|             if result.get("ok"):
296|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '喂食成功')}")]
297|             else:
298|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '喂食失败')}")]
299|         
300|         elif name == "mochi_pat":
301|             result = await call_api("POST", "/api/action", {"action": "pat"})
302|             if result.get("ok"):
303|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '抚摸成功')}")]
304|             else:
305|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '抚摸失败')}")]
306|         
307|         elif name == "mochi_play":
308|             result = await call_api("POST", "/api/action", {"action": "play"})
309|             if result.get("ok"):
310|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '玩耍成功')}")]
311|             else:
312|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '玩耍失败')}")]
313|         
314|         elif name == "mochi_bath":
315|             result = await call_api("POST", "/api/action", {"action": "bath"})
316|             if result.get("ok"):
317|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '洗澡成功')}")]
318|             else:
319|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '洗澡失败')}")]
320|         
321|         elif name == "mochi_sleep":
322|             result = await call_api("POST", "/api/action", {"action": "sleep"})
323|             if result.get("ok"):
324|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '哄睡成功')}")]
325|             else:
326|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '哄睡失败')}")]
327|         
328|         elif name == "mochi_send_gift":
329|             data = {
330|                 "name": arguments.get("name"),
331|                 "emoji": arguments.get("emoji"),
332|                 "desc": arguments.get("desc", ""),
333|                 "happy": arguments.get("happy", 10),
334|                 "price": arguments.get("price", 0)
335|             }
336|             result = await call_api("POST", "/api/gift", data)
337|             if result.get("ok"):
338|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '送礼成功')}")]
339|             else:
340|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '送礼失败')}")]
341|         
342|         elif name == "mochi_get_log":
343|             result = await call_api("GET", "/api/log")
344|             if result.get("ok"):
345|                 logs = result.get("log", [])
346|                 if not logs:
347|                     return [TextContent(type="text", text="还没有活动记录")]
348|                 
349|                 output = "【最近的活动】\n\n"
350|                 for log in logs[:20]:
351|                     from datetime import datetime
352|                     time_str = datetime.fromtimestamp(log.get("time", 0)).strftime("%m-%d %H:%M")
353|                     output += f"{time_str} {log.get('text', '')}\n"
354|                 
355|                 return [TextContent(type="text", text=output)]
356|             else:
357|                 return [TextContent(type="text", text="❌ 获取日志失败")]
358|         
359|         elif name == "mochi_checkin":
360|             result = await call_api("POST", "/api/checkin")
361|             if result.get("ok"):
362|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '签到成功')}")]
363|             else:
364|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '签到失败')}")]
365|         
366|         elif name == "mochi_pet_adopt":
367|             data = {
368|                 "name": arguments.get("name"),
369|                 "emoji": arguments.get("emoji")
370|             }
371|             result = await call_api("POST", "/api/pet/adopt", data)
372|             if result.get("ok"):
373|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '领养成功')}")]
374|             else:
375|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '领养失败')}")]
376|         
377|         elif name == "mochi_pet_to_school":
378|             result = await call_api("POST", "/api/pet/school")
379|             if result.get("ok"):
380|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '送去上学了')}")]
381|             else:
382|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '送学失败')}")]
383|         
384|         elif name == "mochi_pet_home":
385|             result = await call_api("POST", "/api/pet/home")
386|             if result.get("ok"):
387|                 return [TextContent(type="text", text=f"✅ {result.get('msg', '接回家了')}")]
388|             else:
389|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '接回失败')}")]
390|         
391|         elif name == "mochi_pet_school_event":
392|             result = await call_api("POST", "/api/pet/school_event")
393|             if result.get("ok"):
394|                 story = result.get("story", "")
395|                 return [TextContent(type="text", text=f"【今天在学校】\n\n{story}")]
396|             else:
397|                 return [TextContent(type="text", text=f"❌ {result.get('msg', '获取事件失败')}")]
398|         
399|         elif name == "mochi_get_school_log":
400|             result = await call_api("GET", "/api/school_log")
401|             if result.get("ok"):
402|                 logs = result.get("logs", [])
403|                 if not logs:
404|                     return [TextContent(type="text", text="学校还没有任何记录")]
405|                 
406|                 output = "【学校日志】\n\n"
407|                 for log in logs[:15]:
408|                     output += f"{log.get('time', '')} {log.get('pet', '')}\n{log.get('story', '')}\n\n"
409|                 
410|                 return [TextContent(type="text", text=output)]
411|             else:
412|                 return [TextContent(type="text", text="❌ 获取学校日志失败")]
413|         
414|         else:
415|             return [TextContent(type="text", text=f"❌ 未知工具: {name}")]
416|     
417|     except Exception as e:
418|         return [TextContent(type="text", text=f"❌ 错误: {str(e)}")]
419| 
420| 
421| async def main():
422|     """启动MCP服务"""
423|     async with stdio_server() as (read_stream, write_stream):
424|         await server.run(
425|             read_stream,
426|             write_stream,
427|             server.create_initialization_options()
428|         )
429| 
430| 
431| if __name__ == "__main__":
432|     asyncio.run(main())
433|
            
