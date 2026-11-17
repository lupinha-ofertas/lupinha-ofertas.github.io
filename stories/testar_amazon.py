"""Teste: abrir a página do produto da Amazon com navegador (Playwright) e achar a foto. Só lê."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lista import ler_produtos  # noqa: E402
from fotos import url_foto_amazon  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

PADROES = [r'"hiRes":"(https://[^"]+)"', r'data-old-hires="(https://[^"]+)"', r'"large":"(https://[^"]+)"',
           r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', r'id="landingImage"[^>]+src="(https://[^"]+)"']


def main():
    amz = [p for p in ler_produtos() if p["loja"] == "Amazon"]
    print("| Produto | Pelo código | Página com navegador |\n|---|---|---|")
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        ctx = nav.new_context(locale="pt-BR", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36")
        for p in amz:
            pg = ctx.new_page()
            try:
                pg.goto(p["link"], wait_until="domcontentloaded", timeout=30000)
                texto = pg.content()
                achou = next((m.group(1) for pd in PADROES if (m := re.search(pd, texto))), None)
                bloqueio = "captcha" in texto.lower() or "robot" in pg.title().lower()
                res = f"✅ {achou[:60]}" if achou else ("❌ captcha" if bloqueio else f"❌ sem foto ({pg.title()[:40]})")
            except Exception as e:
                res = f"❌ {type(e).__name__}"
            pg.close()
            print(f"| {p['nome'][:35]} | {url_foto_amazon(p['link'])[-40:]} | {res} |")
        nav.close()


if __name__ == "__main__":
    main()
