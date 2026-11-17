"""Lê a lista do dia e devolve os produtos.

Fonte: enviar/dados.json (gravado pelo robo-ofertas). Se não existir, lê enviar/index.html.
"""
import html
import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LISTA = RAIZ / "enviar" / "index.html"
DADOS = RAIZ / "enviar" / "dados.json"

LOJAS = {"shopee": "Shopee", "mercado livre": "Mercado Livre", "amazon": "Amazon", "shein": "Shein"}


def slug(texto: str, limite: int = 60) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:limite].rstrip("-")


def _loja(tag: str) -> str:
    t = tag.lower()
    for chave, nome in LOJAS.items():
        if chave in t:
            return nome
    return "?"


def _da_mensagem(msg: str) -> dict:
    """Preço antigo, desconto, parcelas, cupom e motivo, tirados do texto da mensagem."""
    de = re.search(r"De ~R\$ ?([\d.,]+)~ por \*R\$ ?([\d.,]+)\*(?: \((\d+)% OFF\))?", msg)
    parcelas = re.search(r"(\d+)x de R\$ ?([\d.,]+)", msg)
    cupom = re.search(r"cupom:?\s*\*?([A-Z0-9_-]{3,})\*?", msg, re.I)
    motivo = next((l.strip() for l in msg.splitlines() if l.strip().startswith(("⭐", "🔥"))), "")
    return {"preco_antigo": de.group(1) if de else None,
            "desconto": de.group(3) if de and de.group(3) else None,
            "parcelas": f"{parcelas.group(1)}x de R$ {parcelas.group(2)}" if parcelas else None,
            "cupom": cupom.group(1) if cupom else None,
            "motivo": motivo.lstrip("⭐🔥 ").strip()}


def _reais(v) -> str | None:
    if v in (None, "", 0):
        return None
    return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ler_dados(caminho: Path = DADOS) -> list[dict]:
    d = json.loads(caminho.read_text(encoding="utf-8"))
    produtos = []
    for o in d["produtos"]:
        hora = (re.search(r"(\d{1,2})h", o.get("horario", "")) or [None, ""])[1]
        produtos.append({"numero": o["numero"], "loja": o["loja"], "categoria": o.get("categoria", ""),
                         "nome": o["nome"].strip(), "preco": None if o["loja"] == "Amazon" else _reais(o.get("preco")),
                         **_da_mensagem(o.get("msg", "")), "link": o["link"], "horario": o.get("horario", ""),
                         "hora": hora, "slug": slug(o["nome"]), "foto_url": o.get("foto") or None,
                         "item_id": o.get("itemId"), "data": d.get("data")})
    produtos.sort(key=lambda p: p["numero"])
    return produtos


def ler_produtos(caminho: Path = LISTA) -> list[dict]:
    if caminho == LISTA and DADOS.exists():
        return ler_dados()
    fonte = caminho.read_text(encoding="utf-8")
    produtos = []
    # cada <section> é um horário (Manhã · 9h etc.)
    for sec in re.finditer(r"<section><h3>(.*?)</h3>(.*?)</section>", fonte, re.S):
        horario = html.unescape(sec.group(1))
        hora = (re.search(r"(\d{1,2})h", horario) or [None, ""])[1]
        for card in re.finditer(r'<article class="card" data-i="(\d+)">(.*?)</article>', sec.group(2), re.S):
            n, corpo = int(card.group(1)), card.group(2)
            tag = html.unescape(re.search(r'<span class="tag">(.*?)</span>', corpo).group(1))
            preco_tag = re.search(r'<span class="preco">(.*?)</span>', corpo)
            nome = html.unescape(re.search(r"<h2>(.*?)</h2>", corpo, re.S).group(1)).strip()
            msg = html.unescape(re.search(r"<pre>(.*?)</pre>", corpo, re.S).group(1))
            link = re.search(r"https?://\S+", msg.split("👉", 1)[-1]).group(0)
            de = re.search(r"De ~R\$ ?([\d.,]+)~ por \*R\$ ?([\d.,]+)\*(?: \((\d+)% OFF\))?", msg)
            preco = (preco_tag.group(1) if preco_tag else "").replace("R$", "").strip()
            parcelas = re.search(r"(\d+)x de R\$ ?([\d.,]+)", msg)
            cupom = re.search(r"cupom:?\s*\*?([A-Z0-9_-]{3,})\*?", msg, re.I)
            motivo = next((l.strip() for l in msg.splitlines() if l.strip().startswith(("⭐", "🔥"))), "")
            loja = _loja(tag)
            produtos.append({
                "numero": n,
                "loja": loja,
                "categoria": tag.split("·", 1)[-1].strip(),
                "nome": nome,
                "preco": None if loja == "Amazon" or not re.search(r"\d", preco) else preco,
                "preco_antigo": de.group(1) if de else None,
                "desconto": de.group(3) if de and de.group(3) else None,
                "parcelas": f"{parcelas.group(1)}x de R$ {parcelas.group(2)}" if parcelas else None,
                "cupom": cupom.group(1) if cupom else None,
                "motivo": motivo.lstrip("⭐🔥 ").strip(),
                "link": link,
                "horario": horario,
                "hora": hora,
                "slug": slug(nome),
            })
    produtos.sort(key=lambda p: p["numero"])
    return produtos


if __name__ == "__main__":
    for p in ler_produtos():
        print(p["numero"], p["loja"], p["preco"], p["nome"][:50], p["link"])
