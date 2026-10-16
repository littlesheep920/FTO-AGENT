"""Claim 解析与特征比对的共享工具（规则引擎，无 LLM 也可用）。"""
import re

CLAIM_SPLIT_RE = re.compile(r"(\d+)[\.、．]\s*")

# 控弯导管领域关键词（用于要素分类 + 规则比对兜底）
DOMAIN_KEYWORDS = [
    "导管", "管体", "弯曲", "可弯曲", "可调弯", "控弯", "拉线", "牵引丝", "牵引线",
    "聚氨酯", "形状记忆", "镍钛", "球囊", "远端", "近端", "偏转", "手柄", "旋钮",
    "温度", "外径", "直径", "驱动", "弯曲段", "偏转角度",
]

CATEGORY_KEYWORDS = {
    "材料": ["材料", "合金", "聚氨酯", "硅胶", "金属", "塑料", "镍钛", "形状记忆"],
    "连接": ["连接", "固定", "贯穿", "设置于", "安装", "焊接", "粘接", "套设", "连接于"],
    "运动": ["弯曲", "偏转", "变形", "移动", "旋转", "转向", "伸缩"],
    "参数": ["直径", "长度", "角度", "厚度", "宽度", "外径", "内径", "尺寸"],
    "功能": ["用于", "控制", "调节", "实现", "驱动"],
}


def split_claims(full_text: str) -> list:
    """把整段权利要求文本拆成 [{claim_no, claim_type, claim_text}]。

    claim_type: 1=独立（不含"根据权利要求"），2=从属。
    """
    if not full_text:
        return []
    parts = CLAIM_SPLIT_RE.split(full_text)
    claims = []
    for i in range(1, len(parts), 2):
        no = int(parts[i])
        text = (parts[i + 1] if i + 1 < len(parts) else "").strip()
        if not text:
            continue
        is_dep = ("根据权利要求" in text or "如权利要求" in text)
        claims.append({"claim_no": no, "claim_type": 2 if is_dep else 1, "claim_text": text})
    return claims


def split_elements(claim_text: str) -> list:
    """把一条权利要求切分为技术要素。

    去掉前序（"一种...，"标题 + "其特征在于" + "包括："），
    再按 ；； 切分（单个时按逗号切）。
    """
    text = claim_text
    text = re.sub(r"其特征在于[，,:：]?", "", text)
    text = re.sub(r"^\d+[\.、．]\s*", "", text)
    # 去标题前序 "一种XX，"
    text = re.sub(r"^一种[^，,]*[，,]\s*", "", text)
    # 去 "包括："
    text = re.sub(r"^包括[：:，,]?\s*", "", text)
    parts = [p.strip() for p in re.split(r"[；;]", text) if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in re.split(r"，", text) if p.strip()]
    # 去掉纯标点/纯数字
    return [p for p in parts if p and not re.fullmatch(r"[\d\W]+", p)]


def categorize(text: str) -> str:
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                return cat
    return "结构"


def element_keywords(text: str) -> list:
    """提取要素中的领域关键词。"""
    return [kw for kw in DOMAIN_KEYWORDS if kw in text]


def rule_match(product_text: str, element_text: str) -> tuple:
    """规则比对：返回 (ratio, matched_keywords)。

    ratio = 要素关键词在产品描述中的命中比例，0~1。
    """
    kws = element_keywords(element_text)
    if not kws:
        return 0.5, []
    hits = [kw for kw in kws if kw in product_text]
    return round(len(hits) / len(kws), 3), hits


def ratio_to_status(ratio: float) -> str:
    if ratio >= 0.6:
        return "命中"
    if ratio >= 0.3:
        return "部分"
    return "缺失"
