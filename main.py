import json
import re
from pathlib import Path
from nonebot import on_message
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.params import EventMessage

# ========== 请修改下方的目标 QQ 号 ==========
TARGET_QQ = 3889738531  # 替换为 @KardsAmiya 的 QQ 号
# =========================================

# 加载卡牌数据（必须将 cards.json 放在本插件文件夹内）
DATA_PATH = Path(__file__).parent / "cards.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    CARDS = json.load(f)

# 监听状态：记录当前处于“接收侦查数据”状态的群号
listening_groups = set()

# ---------- 中文 -> 游戏内字段 映射表 ----------
TYPE_MAP = {
    "步兵": "infantry",
    "坦克": "tank",
    "战斗机": "fighter",
    "轰炸机": "bomber",
    "火炮": "artillery",
    "指令": "order",
    "反制": "countermeasure",
}
FACTION_MAP = {
    "英国": "Britain",
    "美国": "USA",
    "德国": "Germany",
    "日本": "Japan",
    "苏联": "Soviet",
    "法国": "France",
    "意大利": "Italy",
    "波兰": "Poland",
    "芬兰": "Finland",
    "澳新": "Anzac",
    "中立": "Neutral",
}
RARITY_MAP = {
    "标准": "Standard",
    "特殊": "Special",
    "受限": "Limited",
    "精英": "Elite",
}

def match_cards(text: str):
    """从一条消息中提取线索，匹配卡牌"""
    conditions = {}

    # 1. 费用（支持“费用2”或“2费”）
    cost_match = re.search(r'(?:费用|费)\s*(\d+)', text)
    if cost_match:
        conditions['kredits'] = int(cost_match.group(1))

    # 2. 类型
    for cn, en in TYPE_MAP.items():
        if cn in text:
            conditions['type'] = en
            break

    # 3. 国籍
    for cn, en in FACTION_MAP.items():
        if cn in text:
            conditions['faction'] = en
            break

    # 4. 稀有度
    for cn, en in RARITY_MAP.items():
        if cn in text:
            conditions['rarity'] = en
            break

    # 遍历所有卡牌，满足所有条件即匹配
    result = []
    for card in CARDS:
        ok = True
        for key, value in conditions.items():
            if card.get(key) != value:
                ok = False
                break
        if ok:
            result.append(card['name'])
    return result

# 消息事件处理器
matcher = on_message(rule=Rule())

@matcher.handle()
async def handle_group_message(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = event.user_id
    msg = str(event.get_message()).strip()

    # ---------- 开启侦查模式 ----------
    if msg == "/接收侦查数据":
        listening_groups.add(group_id)
        await matcher.send(f"侦查数据接收中，请等待 @{TARGET_QQ} 提供线索。")
        return

    # ---------- 若当前群处于侦查模式 ----------
    if group_id in listening_groups:
        # 只处理目标用户的消息
        if user_id == TARGET_QQ:
            matches = match_cards(msg)
            if not matches:
                await matcher.send("未找到符合线索的卡牌，请检查线索格式。")
            else:
                if len(matches) > 20:
                    await matcher.send(f"符合条件的卡牌过多（共 {len(matches)} 张），请增加线索再试。")
                else:
                    reply = "符合条件的卡牌：\n" + "\n".join(matches)
                    await matcher.send(reply)
            # 完成一次猜测后自动关闭侦查模式（如需再次猜测，重新发送 /接收侦查数据）
            listening_groups.discard(group_id)
        else:
            # 非目标用户的消息忽略（不回复）
            pass
