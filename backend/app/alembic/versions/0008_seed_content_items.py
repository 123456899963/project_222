"""seed_content_items：批次五 R1–R5 内容种子数据

Revision ID: 0008_seed_content_items
Revises: 0007_content_platform
Create Date: 2026-11-10

各板块 2–3 条示例条目，供后台/前台演示。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_seed_content_items"
down_revision: str | None = "0007_content_platform"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# 用三引号避免内层英文双引号导致 Python 字符串截断
TEAWARE_SEED = [
    {
        "code": "teaware",
        "title": "盖碗：茶席上最常见的泡茶器具",
        "summary": "上盖、中碗、下托三件一套，又称三才碗，明代以后流行。",
        "body": """盖碗，也称三才碗、三才杯，是一种古老的泡茶器具。碗盖、碗身、碗托三件一套，分别寓意天、人、地三才。

盖碗的优势在于不吸味、散热快、可直视汤色，适合冲泡绿茶、花茶与功夫茶。器型多为敞口浅腹，容量从 100ml 到 200ml 不等。

选盖碗时注意胎质细腻、碗口外撇防烫手、碗盖与碗身密封性适中。""",
        "cover_image": None,
        "meta": {"material": "白瓷", "volume": "150ml", "category": "盖碗"},
        "sort_order": 1,
    },
    {
        "code": "teaware",
        "title": "紫砂壶：茶器之王的秘密",
        "summary": "宜兴紫砂陶土制成，气孔结构使茶香久蕴不散，茶汤越用越润。",
        "body": """紫砂壶源于宋代，盛于明清，以江苏宜兴为核心产地。紫砂陶土含铁、硅、铝等矿物，经 1200℃ 高温烧制后形成独特的双气孔结构。

这种结构使紫砂壶透气性好、保温性适中、不吸茶香却能缓慢释放茶中物质，长期使用内壁形成的「茶山」使茶汤更加醇厚。

新壶开壶需清水煮沸 30 分钟，倒去水后用茶叶反复擦拭内壁。""",
        "cover_image": None,
        "meta": {"material": "紫砂", "volume": "200ml", "category": "茶壶"},
        "sort_order": 2,
    },
]

ORIGIN_SEED = [
    {
        "code": "origin",
        "title": "西湖：龙井茶的故乡",
        "summary": "浙江杭州西湖周边群山，茶园沿湖分布，山色湖光与茶香相映成趣。",
        "body": """西湖产茶历史可追溯至唐代，陆羽《茶经》有载。宋代以后「西湖龙井」渐成名品，明、清两度列为贡茶。

西湖核心产茶区位于狮峰、龙井村、五云山、虎跑一带。年均气温 16℃ 左右，年降水量 1500mm，土壤微酸性红壤，昼夜温差适中，造就了龙井「色翠、香郁、味甘、形美」四绝。

明前龙井特指清明节前采摘的头春茶，通常一芽一叶或一芽两叶，干茶扁平匀整。""",
        "cover_image": None,
        "meta": {"province": "浙江", "region": "杭州西湖"},
        "sort_order": 1,
    },
    {
        "code": "origin",
        "title": "武夷山：乌龙茶与红茶的发源地",
        "summary": "福建武夷山脉，丹霞地貌造就「岩骨花香」，大红袍名品即出此地。",
        "body": """武夷山位于福建省北部，海拔 400–1000m，属典型丹霞地貌——红色砂砾岩经亿万年风化形成奇峰峭壁。

茶园多分布在岩峰之间的「坑」「涧」「窠」中，土层薄而矿物质丰富，茶树因此吸收独特的岩韵。

武夷山是世界文化与自然双重遗产，也是乌龙茶（大红袍、肉桂、水仙）与正山小种红茶的发源地。""",
        "cover_image": None,
        "meta": {"province": "福建", "region": "南平武夷山"},
        "sort_order": 2,
    },
]

CULTURE_SEED = [
    {
        "code": "culture",
        "title": "陆羽与《茶经》：茶学的开山之作",
        "summary": "唐代陆羽著《茶经》三卷十章，是世界上第一部系统性茶文化专著。",
        "body": """陆羽（733–804），字鸿渐，号「茶山御史」，唐代竟陵（今湖北天门）人。他自幼被弃于茶园，后被僧人收养，一生嗜茶。

《茶经》成书于公元 780 年前后，系统论述了茶的起源、种类、采制、器具、煮茶、饮用、产地、传说等，共三卷十章。陆羽因此被尊为「茶圣」。

《茶经》不仅是技术手册，更奠定了中华茶文化的精神内核——茶需「俭」、茶具需「雅」、饮茶需「敬」。""",
        "cover_image": None,
        "meta": {"era": "唐代", "tags": ["陆羽", "茶经", "茶圣"]},
        "sort_order": 1,
    },
    {
        "code": "culture",
        "title": "宋代点茶与斗茶之风",
        "summary": "宋代茶事鼎盛，点茶法取代煮茶成为主流，文人斗茶蔚然成风。",
        "body": """宋代（960–1279）是中华茶文化的黄金时代。茶从煎茶（煮）变为点茶：先将茶饼研磨成细粉，注水后用茶筅击打至泛起细密泡沫（称为「汤花」）。

斗茶又称「茗战」，以汤花持久度和汤色白者为胜。宋徽宗赵佶著《大观茶论》，系统阐述点茶技艺，自称「斗茶十中八九」。

建盏（兔毫盏、油滴盏）因适配点茶汤花观察而风靡，成为宋代最具代表性的茶器。""",
        "cover_image": None,
        "meta": {"era": "宋代", "tags": ["点茶", "斗茶", "宋徽宗", "建盏"]},
        "sort_order": 2,
    },
]

BRAND_SEED = [
    {
        "code": "brand",
        "title": "吴裕泰：百年老字号的茉莉花茶",
        "summary": "1887 年创立于北京，以茉莉花茶闻名，百年传统工艺「双瓣茉莉花」窨制。",
        "body": """吴裕泰茶庄由徽州歙县人吴锡卿于清光绪十三年（1887）在北京崇文门外开办，至今已超 130 年。

品牌坚持「制之得其法、藏之得其宜」的古训，茉莉花茶采用春季采制的春茶坯，与伏天采摘的茉莉花反复窨制，每窨一次需花一天一夜。

2011 年，吴裕泰茉莉花茶制作技艺被列入国家级非物质文化遗产名录。""",
        "cover_image": None,
        "meta": {"founded": 1887, "brand_origin": "北京", "website": "https://www.wuyutai.com"},
        "sort_order": 1,
    },
]

KNOWLEDGE_SEED = [
    {
        "code": "knowledge",
        "title": "六大茶类分类原理：发酵度是核心",
        "summary": "绿茶、白茶、黄茶、乌龙茶、红茶、黑茶，以发酵程度为唯一分类标准。",
        "body": """中华六大茶类由安徽农业大学陈椽教授于 1979 年正式提出，分类依据为 **发酵程度**（茶叶内含物质氧化程度）：

• 绿茶（不发酵 0%）：杀青抑制酶活性，干绿汤绿，如龙井、碧螺春
• 白茶（微发酵 5–10%）：自然萎凋，不炒不揉，如白毫银针、白牡丹
• 黄茶（轻发酵 10–20%）：闷黄工艺，黄汤黄叶，如蒙顶黄芽
• 乌龙茶（半发酵 30–60%）：摇青做青，绿叶红镶边，如铁观音、大红袍
• 红茶（全发酵 80–95%）：酶促氧化彻底，红叶红汤，如祁门红茶、正山小种
• 黑茶（后发酵 100%）：微生物参与的后发酵，需陈化，如安化黑茶、六堡茶""",
        "cover_image": None,
        "meta": {"subtype": "standard", "difficulty": "beginner"},
        "sort_order": 1,
    },
    {
        "code": "knowledge",
        "title": "水温与投茶量：泡茶两要素",
        "summary": "不同茶类适用不同水温与投茶比例，掌握这两点，日常泡茶基本不会出错。",
        "body": """水温：
• 绿茶、黄茶：80–85℃（避免高温破坏鲜爽味与维生素）
• 白茶：85–95℃（视茶叶老嫩调整）
• 乌龙茶：95–100℃（沸水充分激发岩韵与香气）
• 红茶：85–95℃
• 黑茶：100℃ 沸水（后发酵茶需高温唤醒活性）

投茶量：
• 盖碗：茶量约为盖碗容量的 1/5（茶水比 1:50）
• 紫砂壶：茶量约为壶容量的 1/3（随壶型调整）
• 玻璃杯（绿茶）：茶量约为杯容量的 1/6""",
        "cover_image": None,
        "meta": {"subtype": "brewing", "difficulty": "beginner"},
        "sort_order": 2,
    },
]


ALL_SEED = TEAWARE_SEED + ORIGIN_SEED + CULTURE_SEED + BRAND_SEED + KNOWLEDGE_SEED


def upgrade() -> None:
    conn = op.get_bind()
    # 获取各板块 type_id
    type_map: dict[str, int] = {}
    rows = conn.execute(sa.text("SELECT id, code FROM content_types")).fetchall()
    for row in rows:
        type_map[row[1]] = row[0]

    # 去重：同标题已存在则跳过
    existing_titles = {
        r[0] for r in conn.execute(sa.text("SELECT title FROM content_items")).fetchall()
    }

    for item in ALL_SEED:
        if item["title"] in existing_titles:
            continue
        type_id = type_map.get(item["code"])
        if type_id is None:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO content_items (type_id, title, summary, body, cover_image, meta, sort_order, is_active) "
                "VALUES (:type_id, :title, :summary, :body, :cover_image, CAST(:meta AS JSON), :sort_order, 1)"
            ),
            {
                "type_id": type_id,
                "title": item["title"],
                "summary": item["summary"],
                "body": item["body"],
                "cover_image": item["cover_image"],
                "meta": __import__("json").dumps(item["meta"], ensure_ascii=False),
                "sort_order": item["sort_order"],
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    titles = [item["title"] for item in ALL_SEED]
    conn.execute(
        sa.text("DELETE FROM content_items WHERE title IN :titles"),
        {"titles": titles},
    )
