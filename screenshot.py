"""自动截图脚本 — 截取词页系统各页面"""
import time
import os
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
OUT_DIR = "E:/Codex/ciye/docs/screenshots"
os.makedirs(OUT_DIR, exist_ok=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        page = ctx.new_page()

        # 1. 登录页
        print("  screenshot: login page")
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=f"{OUT_DIR}/01-登录页.png")

        # 登录
        print("  logging in...")
        page.fill('input[placeholder="输入用户名"]', "test")
        page.fill('input[placeholder="输入密码"]', "123456")
        page.click('button[type="submit"]')
        page.wait_for_timeout(3000)

        # 2. 今日学习
        print("  screenshot: study")
        page.screenshot(path=f"{OUT_DIR}/02-今日学习.png")

        # 3. 翻开释义
        print("  screenshot: reveal")
        try:
            page.click('button:has-text("翻开释义")', timeout=3000)
            page.wait_for_timeout(1200)
        except:
            pass
        page.screenshot(path=f"{OUT_DIR}/03-学习卡片-翻开.png")

        # 4. 词书架
        print("  screenshot: shelf")
        page.click('a:has-text("词书架")')
        page.wait_for_timeout(2000)
        page.screenshot(path=f"{OUT_DIR}/04-词书架.png")

        # 5. 错词本
        print("  screenshot: wrong words")
        page.click('a:has-text("错词本")')
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT_DIR}/05-错词本.png")

        # 6. 收藏夹
        print("  screenshot: favorites")
        page.click('a:has-text("收藏夹")')
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT_DIR}/06-收藏夹.png")

        # 7. 拼写测试
        print("  screenshot: spelling test")
        page.click('a:has-text("拼写测试")')
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT_DIR}/07-拼写测试.png")

        # 8. 遗忘曲线
        print("  screenshot: ebbinghaus")
        page.click('a:has-text("遗忘曲线")')
        page.wait_for_timeout(2000)
        page.screenshot(path=f"{OUT_DIR}/08-遗忘曲线.png")

        # 9. 学习统计
        print("  screenshot: stats")
        page.click('a:has-text("学习统计")')
        page.wait_for_timeout(2000)
        page.screenshot(path=f"{OUT_DIR}/09-学习统计.png")

        # 10. 设置
        print("  screenshot: settings")
        page.click('a:has-text("设置")')
        page.wait_for_timeout(2000)
        page.screenshot(path=f"{OUT_DIR}/10-设置.png")

        # 11. AI 助手
        print("  screenshot: AI assistant")
        page.click('a:has-text("今日学习")')
        page.wait_for_timeout(1500)
        try:
            page.click('.ai-fab', timeout=3000)
            page.wait_for_timeout(2000)
        except:
            pass
        page.screenshot(path=f"{OUT_DIR}/11-AI助手.png")

        browser.close()
        print(f"\nDone! {len(os.listdir(OUT_DIR))} screenshots saved to {OUT_DIR}")


if __name__ == "__main__":
    run()
