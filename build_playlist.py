#!/usr/bin/env python3
"""Build a curated global IPTV playlist from iptv-org and keep only reachable streams."""
import re, sys, time, collections, concurrent.futures as cf, urllib.request, ssl

BASE = "https://iptv-org.github.io/iptv/"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def get(url, timeout=40, retries=3):
    last = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        except Exception as e:
            last = e; time.sleep(2)
    raise last

def parse(txt):
    L = txt.splitlines(); out = []
    for i, l in enumerate(L):
        if not l.startswith("#EXTINF"): continue
        name = l.rsplit(",", 1)[-1].strip()
        g = lambda k: (re.search(k + r'="([^"]*)"', l) or [None, ""])[1]
        url = next((L[j].strip() for j in range(i + 1, min(i + 4, len(L))) if L[j].startswith("http")), "")
        r = re.search(r"\((\d{3,4})[pi]\)", name); res = int(r.group(1)) if r else 0
        bad = bool(re.search(r"Geo-blocked|Not 24/7", name))
        if url: out.append(dict(name=name, tid=g("tvg-id"), logo=g("tvg-logo"), url=url, res=res, bad=bad))
    return out

def probe(it):
    try:
        with get(it["url"], timeout=6, retries=1) as r:
            return it, r.status == 200 and r.read(4096).lstrip()[:7] == b"#EXTM3U"
    except Exception:
        return it, False

def clean(name):
    return re.sub(r"\s*\((\d{3,4})[pi]\)", "", name).strip()

# (group, display name, regex on channel name)
W = [
("新闻 News","BBC News",r"^BBC News( \(|$)|^BBC News (HD|Global)"),
("新闻 News","CNN International",r"^CNN International|^CNN( \(|$)"),
("新闻 News","Al Jazeera English",r"^Al Jazeera English"),
("新闻 News","DW English",r"^DW (English|News)|^DW \("),
("新闻 News","France 24 English",r"^France 24 English"),
("新闻 News","NHK World Japan",r"^NHK World"),
("新闻 News","Bloomberg TV",r"^Bloomberg( TV| Originals|$| \()"),
("新闻 News","Euronews English",r"^Euronews English"),
("新闻 News","Sky News",r"^Sky News( \(|$|\s*HD)"),
("新闻 News","CNA 亚洲新闻台",r"^CNA( |$)|^Channel NewsAsia"),
("新闻 News","CGTN English",r"^CGTN( \(|$| English)"),
("新闻 News","TRT World",r"^TRT World"),
("新闻 News","WION",r"^WION"),
("新闻 News","Arirang",r"^Arirang TV( \(|$)"),
("新闻 News","ABC News Live",r"^ABC News Live( \(|$)"),
("新闻 News","CBS News 24/7",r"^CBS News 24/7"),
("新闻 News","NBC News NOW",r"^NBC News NOW"),
("新闻 News","Newsmax",r"^Newsmax( |$)"),
("新闻 News","i24NEWS English",r"^i24NEWS English"),
("新闻 News","LiveNOW from FOX",r"^LiveNOW"),
("纪录片 Documentary","NASA TV",r"^NASA (TV|\+)|^NASA TV"),
("纪录片 Documentary","Love Nature",r"^Love Nature( \(|$| HD| 4K)"),
("纪录片 Documentary","Curiosity Channel",r"^Curiosity Channel"),
("纪录片 Documentary","Documentary+",r"^Documentary\+"),
("纪录片 Documentary","History Hit",r"^History Hit"),
("纪录片 Documentary","Smithsonian Channel",r"^Smithsonian"),
("纪录片 Documentary","Nat Geo Wild",r"^Nat(ional)? Geo(graphic)? Wild"),
("纪录片 Documentary","National Geographic",r"^National Geographic( \(|$| HD)|^Nat Geo( \(|$| HD)"),
("纪录片 Documentary","Wild Earth",r"^Wild Earth"),
("纪录片 Documentary","Real Wild",r"^Real Wild"),
("纪录片 Documentary","Cosmos",r"^Cosmos"),
("纪录片 Documentary","CGTN Documentary",r"^CGTN Documentary"),
("纪录片 Documentary","Docurama",r"^Docurama"),
("纪录片 Documentary","Pluto TV Documentaries",r"^Pluto TV (Documentar|Discovery)"),
("体育 Sports","Red Bull TV",r"^Red Bull TV"),
("体育 Sports","CBS Sports HQ",r"^CBS Sports HQ"),
("体育 Sports","Fight Network",r"^Fight Network|^Fight Sports"),
("体育 Sports","Eurosport 1",r"^Eurosport 1"),
("体育 Sports","Eurosport 2",r"^Eurosport 2"),
("体育 Sports","Sport TV",r"^Sport ?TV 1"),
("体育 Sports","beIN SPORTS XTRA",r"^beIN SPORTS XTRA( \(|$)"),
("体育 Sports","Stadium",r"^Stadium( |$)"),
("体育 Sports","Pluto TV Sports",r"^Pluto TV Sports|^Sports Pluto"),
("体育 Sports","Golf Channel",r"^(The )?Golf Channel|^Golf( TV|$)"),
("体育 Sports","Fox Sports",r"^Fox Sports( |$)"),
("体育 Sports","Tennis Channel",r"^Tennis Channel"),
("体育 Sports","CCTV-5",r"^CCTV-?5( |$)"),
("电影 Movies","Pluto TV Movies",r"^Pluto TV Movies|^Pluto TV Cine"),
("电影 Movies","Pluto TV Action",r"^Pluto TV Action"),
("电影 Movies","Pluto TV Sci-Fi",r"^Pluto TV Sci-?Fi"),
("电影 Movies","Pluto TV Horror",r"^Pluto TV (Horror|Terror)"),
("电影 Movies","Pluto TV Comedy",r"^Pluto TV Comedy"),
("电影 Movies","Pluto TV Classic Movies",r"^Pluto TV Classic"),
("电影 Movies","Cine Action by Pluto TV",r"^Cine Action by Pluto"),
("电影 Movies","Rakuten Movies",r"^Rakuten TV (Action|Movies|Comedy|Drama|Romance|Thriller)"),
("电影 Movies","Tubi Movies",r"^Tubi"),
("电影 Movies","Filmrise Movies",r"^FilmRise"),
("电影 Movies","Classic Movies",r"^Classic Movies|^All Time Movies"),
("电影 Movies","Western",r"^Western"),
("电影 Movies","Crime Network",r"^(Crime|True Crime)( Network| Channel|$)"),
("动画少儿 Kids","Cartoon Network",r"^Cartoon Network( \(|$| HD)"),
("动画少儿 Kids","Cartoonito",r"^Cartoonito( \(|$| HD)"),
("动画少儿 Kids","Nickelodeon",r"^Nickelodeon( \(|$| HD)"),
("动画少儿 Kids","Nick Jr.",r"^Nick Jr"),
("动画少儿 Kids","Disney Channel",r"^Disney Channel( \(|$| HD)"),
("动画少儿 Kids","Disney Junior",r"^Disney Junior"),
("动画少儿 Kids","Baby Shark TV",r"^Baby Shark"),
("动画少儿 Kids","Moonbug Kids",r"^Moonbug"),
("动画少儿 Kids","Pluto TV Kids",r"^Pluto TV Kids|^Pluto Kids"),
("动画少儿 Kids","Anime x HIDIVE",r"^Anime x HIDIVE"),
("动画少儿 Kids","Pluto TV Anime",r"^Pluto TV Anime"),
("动画少儿 Kids","Ryan and Friends",r"^Ryan"),
("动画少儿 Kids","Peppa Pig",r"^Peppa"),
("动画少儿 Kids","Paw Patrol",r"^Paw Patrol"),
("动画少儿 Kids","CCTV-14 少儿",r"^CCTV-?14"),
("音乐 Music","MTV",r"^MTV( \(|$| HD| Hits| 00s| 80s| 90s| Live)"),
("音乐 Music","Vevo Pop",r"^Vevo Pop"),
("音乐 Music","Vevo Hip Hop",r"^Vevo Hip"),
("音乐 Music","Vevo Latino",r"^Vevo Latino"),
("音乐 Music","Vevo 2000s",r"^Vevo 2000"),
("音乐 Music","Stingray Classica",r"^Stingray Classica"),
("音乐 Music","Stingray Djazz",r"^Stingray Djazz"),
("音乐 Music","Mezzo",r"^Mezzo( |$)"),
("音乐 Music","Trace Urban",r"^Trace Urban"),
("音乐 Music","Trace Latina",r"^Trace Latina"),
("音乐 Music","CMC Country",r"^CMC"),
("音乐 Music","Deluxe Music",r"^Deluxe Music"),
("音乐 Music","Concert Channel",r"^Concert Channel"),
("音乐 Music","Classic Music",r"^Classic Music"),
("音乐 Music","The Rock",r"^Rock( TV|$)|^Classic Rock"),
("音乐 Music","Jazz",r"^Jazz( TV|$)|^Jazz"),
("音乐 Music","Lofi",r"^Lo-?fi"),
("音乐 Music","K-pop",r"^K-?pop|^KPop"),
]

COUNTRIES = [("jp","日本 Japan"),("kr","韩国 Korea"),("hk","香港 Hong Kong"),("tw","台湾 Taiwan"),
             (("us",),"美国 USA"),(("gb","uk"),"英国 UK"),("de","德国 Germany"),("fr","法国 France"),
             ("sg","新加坡 Singapore"),("au","澳洲 Australia"),("ca","加拿大 Canada")]
JUNK = re.compile(r"shop|shopping|radio|\bFM\b|\bAM\b|home &|mall|casino|bet\b|adult|xxx|church|evangel|BTL TV|faith|bakthi|\b\d+(GB|AW|PR)\b|^\d{1,2}[A-Z]{2,3}$|^(ABC|CBS|NBC|FOX|PBS) [A-Z]{3,5}", re.I)
PER_COUNTRY = 8

def main(out_path):
    all_items = parse(get(BASE + "index.m3u", timeout=90).read().decode("utf-8", "ignore"))
    out = ["#EXTM3U"]; stats = collections.OrderedDict(); used = set()

    cands = []
    for grp, disp, pat in W:
        m = [it for it in all_items if re.search(pat, it["name"], re.I) and not it["bad"]]
        m.sort(key=lambda x: -x["res"])
        cands.append((grp, disp, m[:6]))
    flat = [it for _, _, m in cands for it in m]
    with cf.ThreadPoolExecutor(64) as ex: ok = {id(it): v for it, v in ex.map(probe, flat)}
    for grp, disp, m in cands:
        pick = next((it for it in m if ok[id(it)] and it["url"] not in used), None)
        stats.setdefault(grp, [0, 0]); stats[grp][1] += 1
        if pick:
            used.add(pick["url"]); stats[grp][0] += 1
            out += ['#EXTINF:-1 tvg-id="%s" tvg-logo="%s" group-title="%s",%s' % (pick["tid"], pick["logo"], grp, disp), pick["url"]]

    for code, label in COUNTRIES:
        codes = code if isinstance(code, tuple) else (code,)
        items = None
        for c in codes:
            try: items = parse(get(BASE + "countries/%s.m3u" % c).read().decode("utf-8", "ignore")); break
            except Exception as e: print("skip", c, e, file=sys.stderr)
        if not items: stats[label] = [0, 0]; continue
        seen = set(); cand = []
        for it in sorted(items, key=lambda x: (-x["res"], x["name"])):
            if it["bad"] or JUNK.search(it["name"]) or it["url"] in used: continue
            k = re.sub(r"[^a-z0-9]", "", re.sub(r"\(.*?\)|\[.*?\]", "", it["name"]).lower())
            if k in seen: continue
            seen.add(k); cand.append(it)
        cand = cand[:50]
        with cf.ThreadPoolExecutor(48) as ex: res = list(ex.map(probe, cand))
        good = [it for it, v in res if v][:PER_COUNTRY]
        stats[label] = [len(good), len(cand)]
        for it in good:
            used.add(it["url"])
            out += ['#EXTINF:-1 tvg-id="%s" tvg-logo="%s" group-title="%s",%s' % (it["tid"], it["logo"], label, clean(it["name"])), it["url"]]

    n = (len(out) - 1) // 2
    if n < 30:
        print("too few channels (%d), refusing to overwrite" % n, file=sys.stderr); sys.exit(1)
    open(out_path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("channels:", n)
    for k, v in stats.items(): print(k, v[0], "/", v[1])

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "playlist.m3u")
