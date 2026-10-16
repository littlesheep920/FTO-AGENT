"""Mock 演示源：返回控弯导管领域的示例 CN 专利（明确标记 source=mock）。

用途：无真实数据源/无网络时，端到端演示完整流水线（含权利要求）。
生产环境请勿把 mock 放进 PATENT_SOURCES。
"""
from services.base import BaseSource, PatentDoc

_SAMPLES = [
    {
        "patent_no": "CN115000001A",
        "title": "一种可控弯曲的导引导管",
        "abstract": "本发明公开一种可控弯曲的导引导管，包括管体、位于管体远端的可弯曲段，以及贯穿管体的拉线机构；"
                    "通过牵拉拉线使可弯曲段向预设方向弯曲，实现对导管远端的精确控弯。",
        "applicant": "上海某医疗器械有限公司",
        "inventor": "张三",
        "application_date": "2023-03-15",
        "publication_date": "2023-08-01",
        "grant_date": None,
        "ipc_codes": ["A61M25/092", "A61M25/01"],
        "legal_status": "审中",
        "family": [{"patent_no": "CN115000002A", "relation": "分案"}],
        "claims": (
            "1. 一种可控弯曲的导引导管，其特征在于，包括：管体，具有近端和远端；"
            "可弯曲段，设置于所述管体的远端；拉线，贯穿所述管体并与所述可弯曲段连接，用于控制所述可弯曲段弯曲。\n"
            "2. 根据权利要求1所述的可控弯曲的导引导管，其特征在于，所述拉线为两根，对称设置于所述管体两侧。"
        ),
    },
    {
        "patent_no": "CN114000002B",
        "title": "拉线驱动的可调弯导管",
        "abstract": "一种拉线驱动的可调弯导管，管体远端设置弯曲段，弯曲段内嵌有两根对称布置的拉线，"
                    "拉线近端连接手柄的旋钮，旋转旋钮即可控制弯曲段的偏转角度。",
        "applicant": "北京某医疗科技公司",
        "inventor": "李四",
        "application_date": "2022-06-20",
        "publication_date": "2022-11-10",
        "grant_date": "2024-02-15",
        "ipc_codes": ["A61M25/092"],
        "legal_status": "有效",
        "family": [],
        "claims": (
            "1. 一种拉线驱动的可调弯导管，其特征在于，包括：管体；弯曲段，位于所述管体远端；"
            "两根拉线，对称设置于所述弯曲段内；手柄，设置于所述管体近端，所述手柄上的旋钮与所述拉线连接，"
            "用于控制所述弯曲段的偏转角度。"
        ),
    },
    {
        "patent_no": "CN113000003A",
        "title": "形状记忆合金控弯导管",
        "abstract": "本发明涉及一种形状记忆合金控弯导管，弯曲段由镍钛形状记忆合金制成，"
                    "通过温度变化驱动弯曲段变形，实现导管远端的主动控弯。",
        "applicant": "深圳某介入器械有限公司",
        "inventor": "王五",
        "application_date": "2021-09-05",
        "publication_date": "2021-12-20",
        "grant_date": None,
        "ipc_codes": ["A61M25/092", "A61M25/01"],
        "legal_status": "审中",
        "family": [],
        "claims": (
            "1. 一种形状记忆合金控弯导管，其特征在于，所述导管的弯曲段由镍钛形状记忆合金制成，"
            "通过温度变化驱动所述弯曲段变形。"
        ),
    },
    {
        "patent_no": "CN112000004B",
        "title": "球囊导管弯曲控制机构",
        "abstract": "一种球囊导管的弯曲控制机构，通过改变球囊内压力实现导管弯曲角度的调节。",
        "applicant": "广州某医疗器械公司",
        "inventor": "赵六",
        "application_date": "2020-04-10",
        "publication_date": "2020-08-01",
        "grant_date": "2021-06-01",
        "ipc_codes": ["A61M25/10"],
        "legal_status": "失效",
        "family": [],
        "claims": (
            "1. 一种球囊导管弯曲控制机构，其特征在于，通过改变球囊内压力实现导管弯曲角度的调节。"
        ),
    },
    {
        "patent_no": "CN111000005A",
        "title": "双拉线偏转导管",
        "abstract": "本发明公开一种双拉线偏转导管，采用两根拉线分别控制导管远端的两个方向偏转，"
                    "提高控弯精度与灵活性。",
        "applicant": "杭州某微创器械有限公司",
        "inventor": "钱七",
        "application_date": "2019-12-01",
        "publication_date": "2020-04-15",
        "grant_date": None,
        "ipc_codes": ["A61M25/092"],
        "legal_status": "有效",
        "family": [{"patent_no": "CN111000006A", "relation": "同族"}],
        "claims": (
            "1. 一种双拉线偏转导管，其特征在于，包括：管体；两根拉线，分别控制所述导管远端的两个方向的偏转。"
        ),
    },
]


class MockSource(BaseSource):
    name = "mock"

    async def search(self, expression, jurisdiction="CN", limit=20):
        docs = []
        for s in _SAMPLES[:limit]:
            docs.append(PatentDoc(
                patent_no=s["patent_no"], title=s["title"], abstract=s["abstract"],
                applicant=s["applicant"], inventor=s["inventor"],
                application_date=s["application_date"], publication_date=s["publication_date"],
                grant_date=s["grant_date"], ipc_codes=s["ipc_codes"],
                legal_status=s["legal_status"], family=s["family"],
                source=self.name,
                source_url=f"https://patents.google.com/patent/{s['patent_no']}/zh",
                raw=s,   # 含 claims，供 Claim Parser 读取
            ))
        return docs
