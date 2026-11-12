#!/usr/bin/env python3
"""
doubao-auto-checkin — 豆包工作「免费用豆包」每日自动签到
=========================================================
云端 Linux 无头浏览器方案：Patchright（Playwright CDP 层反检测）驱动 Chromium，
伪装 Windows 桌面指纹（NVIDIA WebGL / Win32 / 1536x864@1.25 / 上海时区 /
SamanthaDoubaoWork UA），注入网页 Cookie 后自动点击签到并直连 detail 接口复核。

Cookie 来源优先级：
  1) 环境变量 DOUBAO_COOKIE
  2) 同目录 config.json 的 "cookie" 字段

用法：
  export DOUBAO_COOKIE="sid_guard=...; sessionid=..."
  python3 scripts/checkin.py
"""
import json, time, urllib.request, sys, os, datetime, traceback, random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 用户级 site-packages（patchright 装在 ~/.local 时兜底）
sys.path.insert(0, os.path.expanduser("~/.local/lib/python3.12/site-packages"))
from patchright.sync_api import sync_playwright

CONFIG = os.path.join(BASE, "config.json")
LOG = os.path.join(BASE, "checkin.log")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/147.0.7727.149 Safari/537.36 SamanthaDoubaoWork/2.34.12")
TARGET = "https://www.doubao.com/pc/agent-explore"

# Patchright 不管的指纹：WebGL GPU / platform / 语言全量 / 屏幕可用高度
EXTRA_JS = r"""
(()=>{
  try{Object.defineProperty(navigator,'languages',{get:()=>['zh-CN','en','en-GB','en-US','zh']});}catch(e){}
  try{Object.defineProperty(navigator,'platform',{get:()=>'Win32'});}catch(e){}
  try{Object.defineProperty(screen,'availHeight',{get:()=>826});}catch(e){}
  try{
    const gp=WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter=function(p){
      if(p===37445) return 'Google Inc. (NVIDIA)';
      if(p===37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 960 (0x00001401) Direct3D11 vs_5_0 ps_5_0, D3D11)';
      return gp.call(this,p);
    };
  }catch(e){}
})();
"""

def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def load_cookie():
    ck = os.environ.get("DOUBAO_COOKIE", "").strip()
    if ck:
        return ck
    # 依次找：项目根 config.json、脚本同目录 config.json
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(BASE, "config.json"), os.path.join(here, "config.json")):
        if os.path.exists(cand):
            return json.load(open(cand))["cookie"]
    sys.exit("未找到 Cookie：请 export DOUBAO_COOKIE=... 或在项目根目录放 config.json")

def detail_check(cookie_str):
    req = urllib.request.Request(
        "https://www.doubao.com/alice/ug/campaign/v3/detail/?version_code=23206&language=zh&device_platform=web&doubao_device_platform=web&aid=497858&real_aid=497858&pkg_type=release",
        data=json.dumps({"campaign_group_code":"pc_incentive_task_mvp_v3"}).encode(), method="POST")
    req.add_header("Content-Type","application/json"); req.add_header("Cookie",cookie_str)
    req.add_header("User-Agent",UA); req.add_header("Origin","https://www.doubao.com")
    req.add_header("Referer","https://www.doubao.com/")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 必须绕系统代理
    return json.loads(opener.open(req, timeout=15).read())

def main():
    cookie_str = load_cookie()
    ck = [{"name": n.strip(), "value": v.strip(), "domain": ".doubao.com", "path": "/"}
          for n, v in (p.split("=", 1) for p in cookie_str.split(";") if "=" in p)]

    checkin = {}
    # 浏览器路径：环境变量优先；否则探测常见位置（如服务器自带 /opt/browser/chrome）
    chrome_path = os.environ.get("CHROME_PATH", "").strip()
    if not chrome_path:
        for cand in ("/opt/browser/chrome", "/usr/bin/google-chrome", "/usr/bin/chromium"):
            if os.path.exists(cand):
                chrome_path = cand
                break
    launch_kwargs = dict(headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage","--use-gl=angle",
              "--use-angle=swiftshader","--enable-unsafe-swiftshader","--lang=zh-CN"])
    if chrome_path:
        launch_kwargs["executable_path"] = chrome_path
        log(f"使用浏览器: {chrome_path}")
    with sync_playwright() as p:
        b = p.chromium.launch(**launch_kwargs)
        ctx = b.new_context(user_agent=UA, viewport={"width":1536,"height":864},
            device_scale_factor=1.25, locale="zh-CN", timezone_id="Asia/Shanghai")
        ctx.add_init_script(EXTRA_JS)
        ctx.add_cookies(ck)
        pg = ctx.new_page()

        def on_response(resp):
            u = resp.url
            if "/landing/checkin" in u or "/claim" in u or "/receive" in u:
                try: checkin[u] = resp.text()[:200]
                except Exception: checkin[u] = "<read err>"
        pg.on("response", on_response)

        try:
            pg.goto(TARGET, wait_until="networkidle", timeout=40000)
        except Exception as e:
            pg.screenshot(path=os.path.join(BASE, f"error_{datetime.datetime.now():%H%M%S}.png"))
            log(f"页面加载失败: {e}")
            raise

        # —— 真人行为模拟：不要瞬间点中，先像人一样浏览、移动鼠标、滚动 ——
        def human_pause(a=0.6, b=1.8):
            time.sleep(random.uniform(a, b))

        human_pause(2.0, 4.0)  # 打开页面后停留阅读
        try:
            # 鼠标在视窗内随机游走 2-3 次
            for _ in range(random.randint(2, 3)):
                pg.mouse.move(random.uniform(200, 1200), random.uniform(200, 700),
                              steps=random.randint(10, 25))
                human_pause()
            # 小幅滚动，模拟浏览页面
            pg.mouse.wheel(0, random.randint(150, 350))
            human_pause(1.0, 2.0)
            pg.mouse.wheel(0, -random.randint(80, 180))
        except Exception as e:
            log(f"真人行为模拟跳过: {e}")

        state = pg.evaluate(r"""
(()=>{const c=document.querySelector('[data-reward-code="daily_signin"]');
if(!c)return {found:false};
const b=c.querySelector('button');
return {found:true,rewarded:!!c.querySelector('.rewarded-nPpEuG'),btn:b?b.innerText:'NO_BTN'};})()""")
        log(f"签到卡片状态: {state}")

        if state.get("found") and not state.get("rewarded"):
            log("未签，点击签到按钮")
            try:
                btn = pg.locator('[data-reward-code="daily_signin"] button').first
                btn.hover()                       # 先悬停，再停一拍
                box = btn.bounding_box()
                if box:
                    pg.mouse.move(box["x"] + box["width"]*random.uniform(0.3,0.7),
                                  box["y"] + box["height"]*random.uniform(0.3,0.7),
                                  steps=random.randint(8, 18))
                human_pause(0.3, 0.9)             # 悬停后短暂停顿再点
                with pg.expect_response(lambda r: "landing/checkin" in r.url, timeout=20000) as ri:
                    btn.click()
                resp = ri.value
                body = resp.text()[:300]
                log(f"checkin HTTP {resp.status}: {body}")
                checkin["captured"] = body
            except Exception as e:
                log(f"等待 checkin 响应超时/异常: {e}（以 detail 复核为准）")
            human_pause(4.0, 7.0)

        # 自动点击所有「领取」按钮（里程碑/待领奖励）
        try:
            claim_btns = pg.evaluate(r"""
(()=>{const out=[];
document.querySelectorAll('[data-reward-code] button').forEach(b=>{
  const t=b.innerText.trim();
  if(t.includes('领取')){const c=b.closest('[data-reward-code]');
    out.push({code:c?c.getAttribute('data-reward-code'):'?',text:t});}});
return out;})()""")
            for cb in claim_btns:
                log(f"发现待领按钮: {cb}")
                pg.click(f'[data-reward-code="{cb["code"]}"] button')
                time.sleep(3)
        except Exception as e:
            log(f"扫描领取按钮异常: {e}")

        for u, body in checkin.items():
            log(f"接口响应 {u.split('/')[-1]}: {body}")
        b.close()

    d = detail_check(cookie_str)
    code = d.get("code")
    log(f"detail code={code}")
    if code != 0:
        log(f"登录态异常 code={code} msg={d.get('message','')}")
        return
    for t in d.get("data",{}).get("tasks",[]):
        if t.get("campaign_code")=="daily_signin":
            dc=t["daily_checkin"]
            log(f"RESULT total={d['data']['progress']['total_amount']} today={dc['checked_in_today']} continuous={dc['continuous_days']} last={dc['last_checkin_date']}")

if __name__=="__main__":
    try:
        main()
    except Exception:
        log("运行异常:\n" + traceback.format_exc())
        sys.exit(1)
