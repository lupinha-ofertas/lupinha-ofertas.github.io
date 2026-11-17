"""Teste: a Amazon entrega a foto pelo código do produto (ASIN)? Só lê, não publica nada.

Uso:  python stories/testar_amazon.py
"""
import io
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lista import ler_produtos  # noqa: E402
from fotos import UA  # noqa: E402

ENDERECOS = {
    "widget afiliados": "https://ws-na.amazon-adsystem.com/widgets/q?_encoding=UTF8&ASIN={a}&Format=_SL500_&ID=AsinImage&MarketPlace=BR&ServiceVersion=20070822&WS=1&tag=lupinhadaari-20",
    "media P/ASIN": "https://m.media-amazon.com/images/P/{a}.01._SCLZZZZZZZ_SL500_.jpg",
    "images P/ASIN.L": "https://images-na.ssl-images-amazon.com/images/P/{a}.01.L.jpg",
}


def checar(url):
    from PIL import Image
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        dados, tipo = r.read(), r.headers.get("Content-Type", "")
    img = Image.open(io.BytesIO(dados)).convert("RGB")
    cores = len(set(img.resize((40, 40)).getdata()))
    ok = img.width >= 200 and cores > 30
    return ("✅" if ok else "❌") + f" {img.width}x{img.height}, {len(dados)//1024} KB, {cores} cores, {tipo}"


def main():
    asins = [(p["nome"], m.group(1)) for p in ler_produtos() if p["loja"] == "Amazon"
             and (m := re.search(r"/dp/([A-Z0-9]{10})", p["link"]))]
    linhas = ["| Produto | " + " | ".join(ENDERECOS) + " |", "|---" * (len(ENDERECOS) + 1) + "|"]
    for nome, a in asins:
        res = []
        for url in ENDERECOS.values():
            try:
                res.append(checar(url.format(a=a)))
            except Exception as e:
                res.append(f"❌ {type(e).__name__}: {str(e)[:50]}")
        linhas.append(f"| {nome[:35]} ({a}) | " + " | ".join(res) + " |")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
