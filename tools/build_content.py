#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小区百科 + 月度简报生成器。
数据来源：../小区数据/communities.json（贝壳 CLI 实时查询存档）+ 公开页挂牌参考价。
以后每月更新：重新跑 beike CLI → 更新 communities.json → 跑本脚本。
"""
import json, re, html, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # 门店展示页/
DATA = ROOT.parent / "小区数据" / "communities.json"
DATE = "2026-08-27"

# 站点绝对地址：部署/绑域名后用 SITE_URL 环境变量覆盖并重跑本脚本
SITE_URL = os.environ.get("SITE_URL", "https://example.com").rstrip("/")
OG_IMAGE = SITE_URL + "/assets/storefront.jpg"

C = json.load(open(DATA, encoding="utf-8"))

# ---- 文章元数据（按可夫提供的维护清单顺序）----
# (显示名, slug, 挂牌参考均价, 一句话特点, 组员[仅组团])
ARTICLES = [
    ("玉翠园", "yucuiyuan", None, "老牌品质社区", None),
    ("金泰丽舍", "jintailishe", None, "近武清高铁商圈", None),
    ("泰合府", "tahefu", "11,333", "价格居中的次新选择", None),
    ("鸿坤原乡郡", "hongkun-yuanxiangjun", "11,849", "体量大、选择多", None),
    ("泉昇佳苑", "quansheng-jiayuan", "7,523–7,849", "还迁商品混合 · 板块价格地板", ["泉昇佳苑东区", "泉昇佳苑中区", "泉昇佳苑西区"]),
    ("泉鑫佳苑", "quanxin-jiayuan", "7,947", "还迁商品混合 · 物业费 0.5 元", ["泉鑫佳苑东区", "泉鑫佳苑中区", "泉鑫佳苑西区"]),
    ("丽泽花园", "lize-huayuan", None, "低于周边均价的实惠盘", None),
    ("丽德花园", "lide-huayuan", "11,897", "黄庄中部改善选择", None),
    ("新华联悦澜湾", "xinhualian-yuelanwan", "12,422", "纯洋房高品质社区", None),
    ("品澜花苑", "pinlan-huayuan", None, "次新小区 · 自带游泳池", None),
    ("瞰湖花苑", "kanhu-huayuan", None, "次新 · 总价跨度大", None),
    ("隽悦府", "junyuefu", None, "次新 · 总价友好", None),
    ("奥克斯泉上文华", "aokesi-quanshangwenhua", None, "次新 · 高于周边均价的品质盘", None),
    ("金融街金悦府", "jinrongjie-jinyuefu", "12,458", "楼龄 1–4 年 · 板块最新", None),
    ("金科博翠湾", "jinke-bocuiwan", None, "2021–2022 年次新盘", None),
    ("世茂国风雅颂", "shimao-guofengyasong", "11,763", "西侧临龙凤河景观带", None),
    ("观澜花苑", "guanlan-huayuan", "15,942", "板块价格天花板 · 改善标杆", None),
    ("名湖花苑", "minghu-huayuan", None, "次新小体量社区", None),
    ("天娇里", "tianjiaoli", None, "高于周边均价的品质盘", None),
    ("翠亨花园", "cuiheng-huayuan", None, "在售量大 · 总价跨度大", None),
    ("华庭豪苑", "huating-haoyuan", None, "高于周边均价 1.3 万/㎡ · 高端盘", None),
    ("上河雅苑南里", "shanghe-yayuan-nanli", None, "4937 户超大社区 · 在售量最大", None),
    ("和悦花园", "heyue-huayuan", None, "在售量少的低密社区", None),
    ("盛世家园", "shengshi-jiayuan", "16,181", "1.6 万档改善盘", None),
    ("翠景园", "cuijingyuan", None, "高于周边均价的品质盘", None),
    ("盛世郦园", "shengshi-liyuan", "15,926", "1.6 万档改善盘 · 楼龄适中", None),
]
# 手写的亚泰澜公馆已存在，单独列入清单
YATAILAN = ("亚泰澜公馆", "yatailan-gongguan", "10,682", "门店所在小区 · 大盘低门槛")

ZONE_REFS = {"泉昇佳苑东区": "7,707", "泉昇佳苑中区": "7,849", "泉昇佳苑西区": "7,523", "泉鑫佳苑东区": "7,947"}

def fee_num(fee):
    m = re.search(r"([\d.]+)", fee or "")
    return float(m.group(1)) if m else None

def price_minmax(pr):
    a, b = pr.split("-")
    return int(a), int(b)

def build_end(years):
    return int(years.split("-")[1]) if years else 0

def build_start(years):
    return int(years.split("-")[0]) if years else 0

def facilities(env):
    m = re.search(r"内部设施：([^，。]+)", env or "")
    return m.group(1).split("/") if m else []

def esc(s):
    return html.escape(str(s), quote=False)

# ---------- 优缺点 / 适合人群（全部从数据推导）----------
def pros_cons(name, d):
    pros, cons = [], []
    pmin, pmax = price_minmax(d["price_range"])
    fee = fee_num(d["fee"])
    if d["households"] >= 2000:
        pros.append(f"{d['households']} 户大盘，在售 {d['on_sale']} 套，流动性好，以后想卖不难出手")
    if d["on_sale"] >= 100:
        pros.append(f"在售 {d['on_sale']} 套，选择多、议价空间大")
    if pmin <= 60:
        pros.append(f"总价 {pmin} 万起，上车门槛低")
    if fee is not None and fee <= 1.0:
        pros.append(f"物业费仅 {d['fee'].replace('元/平米/月','')} 元/㎡/月，持有成本极低")
    elif fee is not None and fee < 2.0:
        pros.append(f"物业费 {d['fee'].replace('元/平米/月','')} 元/㎡/月，持有成本低")
    if d["green"] and int(d["green"]) >= 40:
        pros.append(f"绿化率 {d['green']}%，居住环境有底子")
    if build_end(d["years"]) >= 2020:
        pros.append(f"{d['years']} 年建成，楼龄新（{d['age']}）")
    if d["ratio"] and float(d["ratio"]) <= 1.3:
        pros.append(f"容积率 {d['ratio']}，密度低、住着不挤")
    fac = facilities(d["env"])
    if "游泳池" in fac:
        pros.append("自带游泳池等内部设施，品质配置")
    if d["diff_dir"] == "低" and d["diff"] >= 2000:
        pros.append(f"挂牌均价低于周边约 {d['diff']} 元/㎡，板块内的价格洼地")
    if not pros:
        pros.append("位于黄庄商圈，生活配套成熟")
    if fee is not None and fee >= 2.9:
        cons.append(f"物业费 {d['fee'].replace('元/平米/月','')} 元/㎡/月，高于周边，长期持有成本要算进去")
    if "动迁安置" in d["rights"] or "房改房" in d["rights"]:
        cons.append("含还迁/房改等混合权属，买前核实产权性质、能否贷款")
    if "商水" in d["util"] or "商电" in d["util"]:
        cons.append("水电性质民商混合，买前确认目标房源是民水民电还是商水商电")
    if d["on_sale"] <= 20:
        cons.append(f"在售仅 {d['on_sale']} 套，选择面窄，看中的房源要果断")
    if 0 < d["households"] <= 600:
        cons.append(f"体量小（{d['households']} 户），房源少、挑选余地有限")
    if "塔楼" in d["btype"]:
        cons.append("含塔楼产品，不同楼栋的户型朝向、公摊差异大，选房要细挑")
    if d["diff_dir"] == "高" and d["diff"] >= 2000:
        cons.append(f"挂牌均价高于周边约 {d['diff']} 元/㎡，属于高端定位，买入预期要放对")
    if build_start(d["years"]) and build_start(d["years"]) <= 2002:
        cons.append(f"部分楼栋楼龄较长（{d['age']}），关注房屋实际状况")
    return pros[:5], cons[:4]

def fit_table(d, ref):
    pmin, _ = price_minmax(d["price_range"])
    refn = int(ref.replace(",", "").split("–")[0]) if ref else None
    gx = "★★★" if pmin <= 70 else ("★★" if pmin <= 110 else "★")
    gs = "★★★" if (refn and refn >= 14000) or pmin >= 100 else "★★"
    be = build_end(d["years"])
    cx = "★★★" if be >= 2020 else ("★★" if be >= 2015 else "★")
    bz = "★★" if d["households"] >= 1500 or d["on_sale"] >= 60 else "★"
    rows = [
        ("刚需首套", gx, "总价门槛低" if pmin <= 70 else "总价门槛中等，看具体户型"),
        ("改善置换", gs, "品质与总价匹配改善需求" if gs == "★★★" else "可作为改善备选，建议同板块对比"),
        ("学区需求", "待定", "以当年教育局划片为准，到店帮你查"),
        ("持有保值", bz, "流动性是保值的底子" if bz == "★★" else "体量有限，保值看板块整体"),
    ]
    return rows

# ---------- 页面骨架 ----------
def breadcrumb_ld(crumbs):
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n,
             "item": f"{SITE_URL}/{u}" if u else SITE_URL + "/"}
            for i, (n, u) in enumerate(crumbs)
        ],
    }

def page(title, desc, ld, body, path="", crumbs=None, ogtype="article"):
    canon = f"{SITE_URL}/{path}" if path else SITE_URL + "/"
    ld_blocks = [json.dumps(ld, ensure_ascii=False, indent=1)]
    if crumbs:
        ld_blocks.append(json.dumps(breadcrumb_ld(crumbs), ensure_ascii=False, indent=1))
    lds = "\n".join(f'<script type="application/ld+json">\n{b}\n</script>' for b in ld_blocks)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{canon}">
<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
<meta property="og:type" content="{ogtype}">
<meta property="og:locale" content="zh_CN">
<meta property="og:site_name" content="德佑地产晟禾亚泰店">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{OG_IMAGE}">
{lds}
<link rel="stylesheet" href="../assets/page.css">
</head>
<body>
<header>
  <div class="brand">德佑<em>·</em>晟禾亚泰店</div>
  <a class="back" href="../index.html">← 返回门店首页</a>
</header>
<div class="wrap">
{body}
</div>
<footer>
  <span>德佑地产 · 晟禾亚泰店</span>
  <span>天津市武清区黄庄街亚泰澜公馆底商</span>
  <a href="../index.html">返回门店首页</a>
</footer>
</body>
</html>
"""

def article_ld(name, title):
    return {
        "@context": "https://schema.org", "@type": "Article",
        "headline": title, "datePublished": DATE, "dateModified": DATE,
        "author": {"@type": "Person", "name": "孙可夫", "jobTitle": "资深经纪人"},
        "publisher": {"@type": "Organization", "name": "德佑地产（晟禾亚泰店）"},
        "about": {"@type": "Residence", "name": name, "address": "天津市武清区黄庄街"},
    }

def fact(num, unit, lbl):
    return f'<div class="fact"><div class="num">{num}<i>{unit}</i></div><div class="lbl">{lbl}</div></div>'

def sign_block(extra=""):
    return f"""  <div class="sign">
    <b>关于作者</b>
    <p>孙可夫，武清房产从业者，深耕本地 16 年，德佑地产晟禾亚泰店资深经纪人。门店在武清区黄庄街亚泰澜公馆底商，黄庄这些小区的房子，我们天天在看、在卖。{extra}</p>
    <p>对这个小区或武清其他小区有疑问，欢迎到店聊，或电话 <a href="tel:18610935206">186 1093 5206</a>（24 小时）。</p>
    <p style="opacity:.55;font-size:.8rem">原创内容，转载请联系授权。</p>
  </div>"""

def head_block(kicker, h1):
    return f"""  <p class="mini-title">{kicker}</p>
  <h1>{h1}</h1>
  <div class="byline">
    <span>作者：孙可夫（德佑地产晟禾亚泰店）</span>
    <span>更新：{DATE}</span>
    <span>数据来源：贝壳找房</span>
  </div>"""

def peer_rows(self_name, d, limit=3):
    pmin, pmax = price_minmax(d["price_range"])
    mid = (pmin + pmax) / 2
    peers = []
    for name, slug, ref, tag, members in ARTICLES + [YATAILAN + (None,)]:
        if name == self_name or name in ("泉昇佳苑", "泉鑫佳苑"):
            continue
        dd = C.get(name)
        if not dd or not dd.get("price_range"):
            continue
        a, b = price_minmax(dd["price_range"])
        peers.append((abs((a + b) / 2 - mid), name, ref, dd["on_sale"], tag))
    peers.sort()
    out = []
    for _, name, ref, on_sale, tag in peers[:limit]:
        out.append(f'<tr><td>{name}</td><td>{ref + " 元/㎡" if ref else "—"}</td><td>{on_sale} 套</td><td>{tag}</td></tr>')
    return "\n".join(out)

def render_single(name, slug, ref, tag):
    d = C[name]
    pmin, pmax = price_minmax(d["price_range"])
    descriptor = "大型" if d["households"] >= 2000 else ("小型" if d["households"] <= 600 else "中型")
    newness = "次新" if build_end(d["years"]) >= 2020 else ""
    facts = []
    if ref:
        facts.append(fact(ref, "元/㎡", "挂牌参考均价"))
    facts += [
        fact(d["on_sale"], "套", "当前在售"),
        fact(f"{pmin}–{pmax}", "万", "在售总价区间"),
        fact(d["households"], "户", "小区规模"),
        fact((d["fee"] or "—").replace("元/平米/月", ""), "元/㎡/月", "物业费"),
        fact(d["green"] or "—", "%", "绿化率"),
    ]
    pros, cons = pros_cons(name, d)
    fit = fit_table(d, ref)
    extra_peitao = ""
    if name == "金泰丽舍":
        extra_peitao = "小区临近武清高铁商圈（据贝壳房源描述），京津通勤是这个小区的一大卖点。"
    if name == "世茂国风雅颂":
        extra_peitao = "据贝壳房源描述，小区西侧临龙凤河景观带，是武清区政府打造的生态景观带。"
    fac = facilities(d["env"])
    fac_html = f"<p>小区内部设施：{'、'.join(fac)}。</p>" if fac else ""
    body = f"""{head_block("小区百科 · 武清", f"{name}全解析：配套、成交、适合谁买")}
  <p class="lede">{name}是武清黄庄商圈的{newness}{descriptor}小区，{tag}。最近不少客户问这个小区值不值得买、现在什么价位，把数据和建议整理在这，供参考。</p>

  <div class="fact-grid">
    {chr(10).join(facts)}
  </div>

  <h2>基础信息</h2>
  <table>
    <tr><th>项目</th><th>内容</th></tr>
    <tr><td>所在板块</td><td>天津市武清区（{d['biz']}）</td></tr>
    <tr><td>建成年代</td><td>{d['years']} 年（楼龄 {d['age']}）</td></tr>
    <tr><td>楼栋类型</td><td>{d['btype']}</td></tr>
    <tr><td>总户数</td><td>{d['households']} 户</td></tr>
    <tr><td>容积率 / 绿化率</td><td>{d['ratio'] or '—'} / {d['green']}%</td></tr>
    <tr><td>物业费</td><td>{d['fee'].replace('元/平米/月',' 元/㎡/月')}，{d['heat']}</td></tr>
    <tr><td>交易权属</td><td>{d['rights']}</td></tr>
    <tr><td>水电性质</td><td>{d['util']}（买前核实目标房源）</td></tr>
  </table>
  {fac_html}

  <h2>配套情况</h2>
  <p>{extra_peitao}学校划片、通勤时间这类容易变动的信息，我们不凭印象写：<span class="fill">学校划片以当年教育局公布为准</span>，周边交通和商业的实测数据 <span class="fill">待可夫实勘补充</span>，到店可以逐项讲清楚。</p>

  <h2>价格与在售情况</h2>
  <p>截至 {DATE}（贝壳平台数据）：小区在售 <em>{d['on_sale']} 套</em>，在售总价区间 <em>{pmin}–{pmax} 万</em>{"，挂牌参考均价约 " + ref + " 元/㎡" if ref else ""}，{"挂牌均价" + d["diff_dir"] + "周边小区约 " + str(d["diff"]) + " 元/㎡" if d["diff"] else ""}。</p>
  <p>提醒一句：挂牌价是房东预期，成交价才是市场。具体到某栋楼、某个户型的近期情况，到店查实时数据最准。</p>

  <h2>优缺点总结</h2>
  <p><strong>优点</strong></p>
  <ul class="plain">
    {chr(10).join('<li>' + esc(p) + '</li>' for p in pros)}
  </ul>
  <p><strong>需要注意</strong></p>
  <ul class="plain">
    {chr(10).join('<li>' + esc(c) + '</li>' for c in cons)}
  </ul>

  <h2>适合谁买</h2>
  <table>
    <tr><th>人群</th><th>适合度</th><th>理由</th></tr>
    {chr(10).join(f'<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>' for a, b, c in fit)}
  </table>

  <h2>同板块对比（挂牌参考均价）</h2>
  <table>
    <tr><th>小区</th><th>参考均价</th><th>在售</th><th>特点</th></tr>
    <tr><td>{name}</td><td>{ref + " 元/㎡" if ref else "—"}</td><td>{d['on_sale']} 套</td><td>{tag}</td></tr>
    {peer_rows(name, d)}
  </table>
  <p class="note">均价为贝壳找房公开页面挂牌参考价（2026 年 3–8 月快照），在售与总价为 {DATE} 实时数据，均为挂牌口径非成交价，仅供参考。</p>

{sign_block()}"""
    title = f"武清{name}全解析：配套、成交、适合谁买 | 德佑地产晟禾亚泰店"
    desc = f"{name}位于天津武清黄庄商圈，{d['years']}年建成，{d['households']}户，在售{d['on_sale']}套、总价{pmin}-{pmax}万。德佑地产晟禾亚泰店根据贝壳平台数据整理，含优缺点和适合人群分析。"
    crumbs = [("首页", ""), ("小区百科", "xiaoqu/"), (name, f"xiaoqu/{slug}.html")]
    return page(title, desc, article_ld(name, f"武清{name}全解析：配套、成交、适合谁买"), body,
                path=f"xiaoqu/{slug}.html", crumbs=crumbs)

def render_group(name, slug, ref, tag, members):
    ds = [C[m] for m in members]
    total_sale = sum(d["on_sale"] for d in ds)
    pmins, pmaxs = zip(*[price_minmax(d["price_range"]) for d in ds])
    pmin, pmax = min(pmins), max(pmaxs)
    total_h = sum(d["households"] for d in ds)
    facts = [
        fact(ref, "元/㎡", "挂牌参考均价"),
        fact(total_sale, "套", "三区在售合计"),
        fact(f"{pmin}–{pmax}", "万", "在售总价区间"),
        fact(total_h, "户", "三区总户数"),
        fact("0.5–1.5", "元/㎡/月", "物业费"),
        fact(len(members), "区", "东/中/西三区"),
    ]
    zone_rows = []
    for m in members:
        d = C[m]
        zref = ZONE_REFS.get(m, "—")
        a, b = price_minmax(d["price_range"])
        zone_rows.append(
            f'<tr><td>{m.replace(name, "") or m}</td><td>{d["years"]}</td><td>{d["households"]} 户</td>'
            f'<td>{zref}</td><td>{d["on_sale"]} 套</td><td>{a}–{b} 万</td><td>{d["fee"].replace("元/平米/月","")}</td></tr>'
        )
    pros, cons = pros_cons(name, {**ds[0], "on_sale": total_sale, "price_range": f"{pmin}-{pmax}", "households": total_h})
    fit = fit_table({**ds[0], "price_range": f"{pmin}-{pmax}", "on_sale": total_sale, "households": total_h}, ref)
    body = f"""{head_block("小区百科 · 武清", f"{name}全解析：东中西三区怎么选、成交、适合谁买")}
  <p class="lede">{name}是武清黄庄商圈的大型社区，分东、中、西三区，{tag}。预算有限想在黄庄上车的客户，十个里有八个会问到它，把数据整理在这，供参考。</p>

  <div class="fact-grid">
    {chr(10).join(facts)}
  </div>

  <h2>三区对比</h2>
  <table>
    <tr><th>区</th><th>建成年代</th><th>户数</th><th>参考均价(元/㎡)</th><th>在售</th><th>总价区间</th><th>物业费(元/㎡/月)</th></tr>
    {chr(10).join(zone_rows)}
  </table>
  <p>三区都是还迁与商品房混合社区，权属含动迁安置房/商品房/房改房/私产，<span class="fill">买前务必核实单套房源的产权性质、是否满五、能否贷款</span>。</p>

  <h2>配套情况</h2>
  <p>学校划片、通勤时间这类容易变动的信息，我们不凭印象写：<span class="fill">学校划片以当年教育局公布为准</span>，周边交通和商业的实测数据 <span class="fill">待可夫实勘补充</span>，到店可以逐项讲清楚。</p>

  <h2>价格与在售情况</h2>
  <p>截至 {DATE}（贝壳平台数据）：{name}三区在售合计 <em>{total_sale} 套</em>，总价区间 <em>{pmin}–{pmax} 万</em>。挂牌均价明显低于周边商品房小区——对预算有限的刚需，这是黄庄上车的价格地板。</p>
  <p>提醒一句：挂牌价是房东预期，成交价才是市场，具体到某个区、某套房的近期情况，到店查实时数据最准。</p>

  <h2>优缺点总结</h2>
  <p><strong>优点</strong></p>
  <ul class="plain">
    {chr(10).join('<li>' + esc(p) + '</li>' for p in pros)}
  </ul>
  <p><strong>需要注意</strong></p>
  <ul class="plain">
    {chr(10).join('<li>' + esc(c) + '</li>' for c in cons)}
  </ul>

  <h2>适合谁买</h2>
  <table>
    <tr><th>人群</th><th>适合度</th><th>理由</th></tr>
    {chr(10).join(f'<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>' for a, b, c in fit)}
  </table>
  <p class="note">均价为贝壳找房公开页面挂牌参考价（2026 年 3–8 月快照），在售与总价为 {DATE} 实时数据，均为挂牌口径非成交价，仅供参考。</p>

{sign_block()}"""
    title = f"武清{name}全解析：东中西三区怎么选、成交、适合谁买 | 德佑地产晟禾亚泰店"
    desc = f"{name}位于天津武清黄庄商圈，分东中西三区，在售合计{total_sale}套、总价{pmin}-{pmax}万，是黄庄刚需上车的价格地板。德佑地产晟禾亚泰店根据贝壳平台数据整理。"
    crumbs = [("首页", ""), ("小区百科", "xiaoqu/"), (name, f"xiaoqu/{slug}.html")]
    return page(title, desc, article_ld(name, f"武清{name}全解析：东中西三区怎么选、成交、适合谁买"), body,
                path=f"xiaoqu/{slug}.html", crumbs=crumbs)

# ---------- 生成 26 篇文章 ----------
outdir = ROOT / "xiaoqu"
outdir.mkdir(exist_ok=True)
listing = []
for name, slug, ref, tag, members in ARTICLES:
    html_text = render_group(name, slug, ref, tag, members) if members else render_single(name, slug, ref, tag)
    (outdir / f"{slug}.html").write_text(html_text, encoding="utf-8")
    d0 = C[members[0]] if members else C[name]
    if members:
        sale = sum(C[m]["on_sale"] for m in members)
        a, b = min(price_minmax(C[m]["price_range"])[0] for m in members), max(price_minmax(C[m]["price_range"])[1] for m in members)
    else:
        sale, (a, b) = d0["on_sale"], price_minmax(d0["price_range"])
    listing.append((name, slug, ref, sale, a, b, tag))
print("articles:", len(listing))

# ---------- 小区百科目录页 ----------
rows = []
# 把亚泰澜插回第 4 位（按可夫清单顺序）
full_list = listing[:3] + [(YATAILAN[0], YATAILAN[1], YATAILAN[2], C["亚泰澜公馆"]["on_sale"], *price_minmax(C["亚泰澜公馆"]["price_range"]), YATAILAN[3])] + listing[3:]
for name, slug, ref, sale, a, b, tag in full_list:
    rows.append(f'<li><a href="{slug}.html">武清{name}全解析</a><span>在售 {sale} 套 · {a}–{b} 万</span></li>')
body = f"""{head_block("小区百科 · 目录", "27 个覆盖小区，一个一个写透")}
  <p class="lede">配套、成交、优缺点、适合谁买——全部基于贝壳平台数据整理，持续更新。想找哪个小区，点进去看；嫌麻烦，直接到店聊。</p>
  <ul class="art-rows">
    {chr(10).join(rows)}
  </ul>
  <p class="note">数据为挂牌口径非成交价，仅供参考；实时行情以贝壳找房页面及到店查询为准。</p>
{sign_block()}"""
(outdir / "index.html").write_text(
    page("小区百科 · 27 个覆盖小区全解析 | 德佑地产晟禾亚泰店",
         "天津武清 27 个主力小区全解析：亚泰澜公馆、鸿坤原乡郡、观澜花苑、泉昇佳苑等，配套、成交、优缺点、适合谁买，德佑地产晟禾亚泰店根据贝壳平台数据整理。",
         article_ld("武清小区百科", "27 个覆盖小区全解析"), body,
         path="xiaoqu/", crumbs=[("首页", ""), ("小区百科", "xiaoqu/")], ogtype="website"), encoding="utf-8")
print("listing done")

# ---------- 月度简报（2026 年 8 月·首期）----------
total = sum(s for _, _, _, s, _, _, _ in full_list)
top3 = sorted(full_list, key=lambda x: -x[3])[:3]
bgdir = ROOT / "baogao"
bgdir.mkdir(exist_ok=True)
trows = []
for name, slug, ref, sale, a, b, tag in full_list:
    d0 = C[name] if name in C else C["亚泰澜公馆"]
    trows.append(f'<tr><td><a href="../xiaoqu/{slug}.html" style="color:var(--ink)">{name}</a></td><td>{ref or "—"}</td><td>{sale}</td><td>{a}–{b} 万</td><td>{d0["years"]}</td></tr>')
body = f"""{head_block("月度数据简报 · 2026 年 8 月（首期）", "武清 27 个主力小区在售数据速览")}
  <p class="lede">这是本店第一期月度数据简报。以后每月一期，就一件事：<em>把武清主力小区的在售情况摆出来，用数据说话</em>。本期数据为 2026 年 8 月 27 日贝壳平台实时查询，挂牌口径。</p>

  <div class="fact-grid">
    {fact(len(full_list), "个", "跟踪小区")}
    {fact(total, "套", "在售房源合计")}
    {fact("43", "万起", "最低上车总价（泉昇佳苑）")}
    {fact("1,470", "万", "最高在售总价（观澜花苑）")}
    {fact(top3[0][3], "套", f"在售最多 · {top3[0][0]}")}
    {fact("0.5", "元/㎡/月", "最低物业费（泉昇/泉鑫）")}
  </div>

  <h2>27 个小区在售总表</h2>
  <table>
    <tr><th>小区</th><th>挂牌参考均价(元/㎡)</th><th>在售(套)</th><th>总价区间</th><th>建成年代</th></tr>
    {chr(10).join(trows)}
  </table>
  <p class="note">均价为贝壳找房公开页面挂牌参考价（2026 年 3–8 月快照），"—"表示暂未获取公开页均价；在售与总价为 {DATE} 实时数据。均为挂牌口径非成交价。成交记录查询功能暂未开通，开通后下期补上成交速览。</p>

  <h2>本期三个观察</h2>
  <ul class="plain">
    <li><strong>房源量就是议价空间</strong>：{top3[0][0]}在售 {top3[0][3]} 套、{top3[1][0]} {top3[1][3]} 套、{top3[2][0]} {top3[2][3]} 套，买家可挑的余地大；在售个位数的小区则相反，看中的要果断。</li>
    <li><strong>价格梯度非常清晰</strong>：泉昇/泉鑫 7 字头地板价 → 亚泰澜、泰合府 1.05–1.15 万 → 新华联、金融街 1.2 万+ → 观澜、盛世系 1.6 万档。先定预算，再选板块。</li>
    <li><strong>次新房集中在 2020 年后</strong>：金融街金悦府（楼龄 1–4 年）、金科博翠湾、奥克斯泉上文华、品澜花苑、瞰湖花苑，介意楼龄的优先看这几个。</li>
  </ul>

  <h2>下期预告</h2>
  <p>每月 1 号更新：27 个小区在售量与挂牌价变化、新上/去化情况。想看具体小区的成交价和走势，到店查实时数据，或电话 186 1093 5206。</p>

{sign_block()}"""
(bgdir / "2026-08.html").write_text(
    page("武清主力小区数据简报 · 2026 年 8 月 | 德佑地产晟禾亚泰店",
         f"2026年8月武清27个主力小区在售数据速览：在售合计{total}套，总价43万-1470万，德佑地产晟禾亚泰店根据贝壳平台数据整理，每月更新。",
         article_ld("武清月度数据简报", "武清 27 个主力小区在售数据速览（2026 年 8 月）"), body,
         path="baogao/2026-08.html",
         crumbs=[("首页", ""), ("月度数据简报", "baogao/"), ("2026 年 8 月", "baogao/2026-08.html")]),
    encoding="utf-8")
print("briefing done, total on sale:", total)

# ---------- 简报目录页 ----------
REPORTS = [("2026-08", "2026 年 8 月（首期）", f"27 个主力小区在售合计 {total} 套，挂牌口径数据速览")]
rrows = "\n".join(
    f'<li><a href="{m}.html">{label}</a><span>{d}</span></li>'
    for m, label, d in REPORTS)
rbody = f"""{head_block("月度数据简报 · 目录", "每月一期，用数据说话")}
  <p class="lede">每月 1 号更新：武清 27 个主力小区在售量与挂牌价变化，新上/去化情况。全部基于贝壳平台数据，挂牌口径。</p>
  <ul class="art-rows">
    {rrows}
  </ul>
  <p class="note">数据为挂牌口径非成交价，仅供参考；实时行情以贝壳找房页面及到店查询为准。</p>
{sign_block()}"""
(bgdir / "index.html").write_text(
    page("月度数据简报 · 武清主力小区行情月报 | 德佑地产晟禾亚泰店",
         "德佑地产晟禾亚泰店月度数据简报：每月一期，武清 27 个主力小区在售量、挂牌价变化，全部基于贝壳平台数据。",
         article_ld("武清月度数据简报", "武清主力小区行情月报目录"), rbody,
         path="baogao/", crumbs=[("首页", ""), ("月度数据简报", "baogao/")], ogtype="website"),
    encoding="utf-8")
print("report index done")

# ---------- robots.txt ----------
(ROOT / "robots.txt").write_text(f"""# 德佑地产晟禾亚泰店 · 欢迎所有搜索引擎与 AI 爬虫抓取
User-agent: *
Allow: /

# 主流 AI 爬虫显式放行（GEO）
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Bingbot
Allow: /

User-agent: Baiduspider
Allow: /

User-agent: Bytespider
Allow: /

User-agent: Applebot
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: meta-externalagent
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
""", encoding="utf-8")

# ---------- sitemap.xml ----------
urls = [("", "1.0", "weekly"), ("xiaoqu/", "0.8", "weekly")]
urls += [(f"xiaoqu/{slug}.html", "0.7", "monthly") for _, slug, *_ in full_list]
urls += [("baogao/", "0.6", "monthly")] + [(f"baogao/{m}.html", "0.6", "monthly") for m, *_ in REPORTS]
smap = ['<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u, pri, freq in urls:
    loc = f"{SITE_URL}/{u}" if u else SITE_URL + "/"
    smap.append(f"  <url><loc>{loc}</loc><lastmod>{DATE}</lastmod>"
                f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>")
smap.append("</urlset>")
(ROOT / "sitemap.xml").write_text("\n".join(smap) + "\n", encoding="utf-8")
print("sitemap:", len(urls), "urls")

# ---------- llms.txt ----------
lines = [
    "# 德佑地产晟禾亚泰店（天津武清）",
    "",
    "> 贝壳平台合作门店，位于天津市武清区黄庄街亚泰澜公馆底商。服务武清全境，深耕黄庄、南湖、下朱庄、体育中心、商务区、杨村六大板块 16 年，主营武清二手房买卖、新房代理、房产咨询。电话：18610935206（24 小时）。",
    "",
    "## 门店",
    f"- [门店首页]({SITE_URL}/)：门店简介、团队、环境实拍、27 个主力小区实时行情、买房问答、到访信息",
    "",
    "## 小区百科（27 个覆盖小区全解析）",
    f"- [小区百科目录]({SITE_URL}/xiaoqu/)：配套、成交、优缺点、适合谁买，全部基于贝壳平台数据",
]
for name, slug, ref, sale, a, b, tag in full_list:
    lines.append(f"- [武清{name}全解析]({SITE_URL}/xiaoqu/{slug}.html)：{tag}，在售 {sale} 套，总价 {a}–{b} 万")
lines += [
    "",
    "## 月度数据简报",
    f"- [简报目录]({SITE_URL}/baogao/)：每月一期，27 个主力小区在售量与挂牌价变化",
]
for m, label, d in REPORTS:
    lines.append(f"- [武清主力小区数据简报 · {label}]({SITE_URL}/baogao/{m}.html)：{d}")
lines += [
    "",
    "## 数据口径",
    "- 在售套数与总价区间为贝壳平台实时查询，挂牌参考均价来自贝壳找房公开页面，均为挂牌口径非成交价",
    "- 学校划片以当年教育局公布为准，本网站不做学区承诺",
]
(ROOT / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("robots / llms done")
