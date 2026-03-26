"""
html_to_image.py — HTML을 이미지(PNG)로 변환

Playwright (headless Chromium)를 사용하여 HTML을 렌더링하고 스크린샷을 캡처합니다.
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


async def html_to_png_async(html_content: str, width: int = 1200) -> bytes:
    """HTML 문자열을 PNG 이미지 바이트로 변환합니다."""
    from playwright.async_api import async_playwright

    # HTML을 임시 파일로 저장
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html_content)
        html_path = f.name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": width, "height": 800})
            await page.goto(f"file://{html_path}", wait_until="networkidle")

            # .slide 요소의 실제 크기에 맞춰 스크린샷
            slide = await page.query_selector(".slide")
            if slide:
                png_bytes = await slide.screenshot(type="png")
            else:
                png_bytes = await page.screenshot(type="png", full_page=True)

            await browser.close()
    finally:
        Path(html_path).unlink(missing_ok=True)

    return png_bytes


def html_to_png(html_content: str, width: int = 1200) -> bytes:
    """동기 래퍼."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # FastAPI 등 이미 이벤트 루프가 돌고 있는 경우
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, html_to_png_async(html_content, width))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(html_to_png_async(html_content, width))
    except Exception as e:
        print(f"[html_to_image] 변환 실패: {e}")
        return b""
