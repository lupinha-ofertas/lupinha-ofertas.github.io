"""Gera o pacote do dia: arte de story de cada achado com foto + os 5 posts do feed.

Uso:
  python stories/gerar_artes.py                 # pacote do dia
  python stories/gerar_artes.py --sem-numero    # sem o selo "Achado nº X"
  python stories/gerar_artes.py --sem-busca     # não busca foto pelo link (só reserva e foto do robô)

Saída em stories/saida/:
  artes/NN-story-*.png   1080x1920, com a faixa para o adesivo de link (posta na mão)
  feed/NN-feed-*.jpg     1080x1350, "Link na bio · Achados do dia · nº X"
  agendar-stories.csv    nº, produto, loja, link, tipo (lista/extra/reserva), horário sugerido (8h-22h),
                         arquivo e a mensagem pronta do WhatsApp
  agendar-feed.csv       nº, produto, loja, horário, arquivo, legenda pronta
  feed.json              o mesmo do feed, para o robô que posta sozinho
Produto sem foto (nem reserva, nem do robô, nem pelo link) fica de fora e vai para o resumo.
"""
import argparse
import base64
import csv
import html
import json
import mimetypes
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

PASTA = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA))
from lista import ler_produtos  # noqa: E402
from fotos import achar_foto, foto_reserva  # noqa: E402

SAIDA = PASTA / "saida" / "artes"
SAIDA_FEED = PASTA / "saida" / "feed"
CSV_FEED = PASTA / "saida" / "agendar-feed.csv"
FEED_JSON = PASTA / "saida" / "feed.json"  # lido pelo robô que posta o feed
POSTS_FEED = 5  # posts do feed por dia
HORARIOS_FEED = ["09:07", "12:17", "15:07", "17:57", "20:07"]  # mesmos do robo-ofertas/postar-feed.yml
MIDIA = "https://raw.githubusercontent.com/lupinha-ofertas/lupinha-ofertas.github.io/{ramo}/"
CSV = PASTA / "saida" / "agendar-stories.csv"
NUMERACAO = PASTA / "saida" / "numeracao.json"  # nº da lista -> nº do achado (a página usa)
LOGO = PASTA / "assets" / "logo.png"  # logo oficial (700x137); se faltar, usa o desenhado

ROSA, ROSA_ESC, CREME, TINTA, CINZA, BORDA = "#C9425C", "#A8334B", "#FFF4EA", "#3A1F2B", "#6E5560", "#D9A3AE"


def _data_uri(arq: Path) -> str:
    tipo = mimetypes.guess_type(arq.name)[0] or "image/jpeg"
    return f"data:{tipo};base64,{base64.b64encode(arq.read_bytes()).decode()}"


def _logo(altura: int = 137) -> str:
    if LOGO.exists():
        return (f'<img src="{_data_uri(LOGO)}" alt="" style="width:{round(altura * 700 / 137)}px;height:{altura}px;'
                f'display:block;object-fit:contain;object-position:left">')
    # mesmo símbolo do site (lupa com coração), com o nome ao lado
    return f'''<div style="display:flex;align-items:center;gap:26px;height:137px">
  <div style="width:137px;height:137px;border-radius:50%;background:{CREME};display:flex;align-items:center;justify-content:center;flex-shrink:0">
    <svg width="92" height="92" viewBox="0 0 100 100"><line x1="62" y1="62" x2="86" y2="86" stroke="{ROSA}" stroke-width="13" stroke-linecap="round"/>
    <circle cx="42" cy="42" r="34" fill="{ROSA}"/><path transform="translate(42,30) scale(.3)" d="M0 35 C0 0 -50 -10 -50 25 C-50 55 -15 75 0 90 C15 75 50 55 50 25 C50 -10 0 0 0 35Z" fill="{CREME}"/></svg>
  </div>
  <div><div style="font-size:66px;font-weight:800;letter-spacing:-1.5px;line-height:1">lupinha da Ari</div>
  <div style="font-size:24px;font-weight:600;letter-spacing:5px;text-transform:uppercase;margin-top:10px;opacity:.92">achadinhos que valem a pena</div></div>
</div>'''


def _foto(foto: Path | None, altura: int, numero: int | None, desconto: str | None) -> str:
    selo_n = (f'<div style="position:absolute;top:22px;left:22px;background:rgba(58,31,43,.72);color:{CREME};font-size:26px;'
              f'font-weight:600;padding:8px 18px;border-radius:999px">Achado nº {numero}</div>') if numero else ""
    selo_d = (f'<div style="position:absolute;top:20px;right:20px;background:{ROSA};color:{CREME};font-size:46px;'
              f'font-weight:800;padding:10px 26px;border-radius:20px">-{desconto}%</div>') if desconto else ""
    if foto:
        miolo = f'<img src="{_data_uri(foto)}" alt="" style="width:100%;height:100%;object-fit:contain;display:block">'
        estilo = "background:#FFFFFF"
    else:
        miolo = (f'<div style="font-size:30px;font-weight:600;color:{ROSA_ESC}">[FOTO DO PRODUTO]</div>')
        estilo = f"background:#FFFFFF;border:4px dashed {BORDA};display:flex;align-items:center;justify-content:center"
    return (f'<div style="position:relative;height:{altura}px;border-radius:32px;overflow:hidden;box-sizing:border-box;{estilo}">'
            f'{miolo}{selo_n}{selo_d}</div>')


def _nome(nome: str) -> str:
    return (f'<div style="font-size:40px;font-weight:500;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;'
            f'-webkit-box-orient:vertical;overflow:hidden">{html.escape(nome)}</div>')


def _faixa(p: dict, selo: bool, bio: bool) -> str:
    if bio:
        texto = "Link na bio · Achados do dia" + (f" · nº {p['numero']}" if selo else "")
        return (f'<div style="flex-grow:1;height:86px;display:flex;align-items:center;justify-content:center;'
                f'font-size:34px;font-weight:800;letter-spacing:-.5px;color:{ROSA_ESC}">{html.escape(texto)}</div>')
    return (f'<div style="flex-grow:1;height:86px;border-radius:999px;border:3px dashed {BORDA};display:flex;align-items:center;'
            f'justify-content:center;font-size:28px;font-weight:500;color:{CINZA}">toque no link para comprar</div>')


def montar_html(p: dict, foto: Path | None, selo: bool = True, bio: bool = False, feed: bool = False) -> str:
    """Story 1080x1920 (faixa para o adesivo de link) ou, com feed=True, post do feed 1080x1350
    com a faixa "Link na bio · Achados do dia · nº X" (bio=True força essa faixa no story)."""
    bio = bio or feed
    n = p["numero"] if selo else None
    amazon = p["loja"] == "Amazon"
    if amazon:
        corpo = _foto(foto, 470 if feed else 670, n, None) + _nome(p["nome"])
        if p["motivo"]:
            corpo += f'<div style="font-size:34px;font-weight:500;line-height:1.35;color:{CINZA}">⭐ {html.escape(p["motivo"])}</div>'
        corpo += (f'<div style="display:flex;align-items:center;gap:20px;background:{ROSA};border-radius:28px;padding:26px 30px">'
                  f'<svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="{CREME}" stroke-width="2.4" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><line x1="15.5" y1="15.5" x2="21" y2="21"/></svg>'
                  f'<div style="font-size:50px;font-weight:800;letter-spacing:-1px;color:{CREME}">Confere o preço no link</div></div>')
        rodape = "*Preço e estoque podem mudar a qualquer momento"
    else:
        extras = sum(bool(x) for x in (p["preco_antigo"], p["parcelas"], p["cupom"]))
        corpo = _foto(foto, (500 - 55 * extras) if feed else (740 - 60 * extras), n, p["desconto"]) + _nome(p["nome"])
        precos = ""
        grande = 80 if feed else 92
        if p["preco_antigo"]:
            precos += (f'<div style="font-size:36px;font-weight:500;color:{CINZA}">De <span style="text-decoration:line-through">'
                       f'R$ {p["preco_antigo"]}</span> por</div>')
        selo = (f'<div style="background:{ROSA};color:{CREME};font-size:{40 if feed else 44}px;font-weight:800;padding:8px 20px;'
                f'border-radius:16px;white-space:nowrap">{p["desconto"]}% OFF</div>') if p["desconto"] else ""
        precos += (f'<div style="display:flex;align-items:center;gap:22px;flex-wrap:wrap">'
                   f'<div style="font-size:{grande}px;font-weight:800;line-height:1.05;letter-spacing:-2px;color:{ROSA}">R$ {p["preco"]}</div>{selo}</div>')
        if p["parcelas"]:
            precos += f'<div style="font-size:34px;font-weight:500">ou {p["parcelas"]}</div>'
        corpo += f'<div style="display:flex;flex-direction:column;gap:4px">{precos}</div>'
        if p["cupom"]:
            corpo += (f'<div style="display:flex;align-items:center;gap:20px;background:#FBE1E3;border:4px dashed {ROSA};border-radius:28px;padding:22px 28px">'
                      f'<div style="font-size:36px;font-weight:500">Use o cupom: <span style="font-weight:800;color:{ROSA_ESC}">{html.escape(p["cupom"])}</span></div></div>')
        rodape = "*Promoção sujeita a alteração a qualquer momento"

    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">
<style>html,body{{margin:0}}*{{box-sizing:border-box}}</style></head><body>
<div style="width:1080px;height:{1350 if feed else 1920}px;position:relative;overflow:hidden;background:{ROSA};font-family:'Inter',system-ui,sans-serif;color:{CREME};padding:{"60px 60px 50px" if feed else "190px 70px 200px"};display:flex;flex-direction:column;gap:{22 if feed else 32}px">
<div style="position:absolute;right:-260px;top:-300px;width:760px;height:760px;border-radius:50%;background:rgba(255,244,234,.08)"></div>
<div style="position:absolute;left:-300px;bottom:-320px;width:820px;height:820px;border-radius:50%;background:rgba(255,244,234,.08)"></div>
<div style="position:relative;display:flex;align-items:center;justify-content:space-between;gap:24px;height:{90 if feed else 137}px">
{_logo(90 if feed else 137)}
<div style="font-size:24px;font-weight:700;padding:10px 22px;border-radius:999px;border:3px solid {CREME};flex-shrink:0">Publicidade</div></div>
<div style="position:relative;background:{CREME};border-radius:48px;padding:44px;display:flex;flex-direction:column;gap:24px;color:{TINTA}">{corpo}</div>
<div style="position:relative;display:flex;align-items:center;gap:24px;background:{CREME};border-radius:999px;padding:16px 28px 16px 16px;height:{110 if feed else 130}px;flex-shrink:0">
<div style="width:{78 if feed else 98}px;height:{78 if feed else 98}px;border-radius:50%;background:{ROSA};display:flex;align-items:center;justify-content:center;flex-shrink:0">
<svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="{CREME}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5"/></svg></div>
{_faixa(p, selo, bio)}</div>
<div style="position:relative;display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center">
<div style="font-size:32px;font-weight:700">@lupinhadaari</div>
<div style="font-size:26px;font-weight:600">{rodape}</div></div>
</div></body></html>'''


def _ordem(produtos: list[dict]) -> list[dict]:
    """Maior desconto primeiro; empate (ou sem desconto) segue a ordem da lista."""
    return sorted(produtos, key=lambda p: (-int(p["desconto"] or 0), p["numero"]))


def escolher_feed(com_foto: list[dict], quantos: int = POSTS_FEED, por_loja: int = 2) -> list[dict]:
    """Os melhores para o feed: maior desconto, máx. 2 por loja (se faltar, libera)."""
    escolhidos, conta = [], {}
    for limite in (por_loja, quantos):
        for p in _ordem(com_foto):
            if len(escolhidos) == quantos:
                break
            if p in escolhidos or conta.get(p["loja"], 0) >= limite:
                continue
            escolhidos.append(p)
            conta[p["loja"]] = conta.get(p["loja"], 0) + 1
    return sorted(escolhidos, key=lambda p: p["numero"])


def horarios_stories(n: int, inicio: int = 8 * 60, fim: int = 22 * 60) -> list[str]:
    """n horários espalhados entre 8h e 22h."""
    if n <= 1:
        return ["09:00"] * n
    passo = (fim - inicio) / (n - 1)
    return [f"{int(inicio + i * passo) // 60:02d}:{int(inicio + i * passo) % 60:02d}" for i in range(n)]


def legenda_feed(p: dict) -> str:
    if p["loja"] == "Amazon":
        preco = "💰 Confere o preço no link (muda rápido!)"
    else:
        preco = f"💰 R$ {p['preco']}"
        if p["preco_antigo"]:
            preco = f"💰 De R$ {p['preco_antigo']} por R$ {p['preco']}" + (f" ({p['desconto']}% OFF)" if p["desconto"] else "")
    loja = {"Mercado Livre": "mercadolivre"}.get(p["loja"], p["loja"].lower())
    return (f"🔍 {p['nome']}\n\n{preco}\n" + (f"🎟️ Cupom: {p['cupom']}\n" if p["cupom"] else "") +
            f"\n👉 Link na bio → Achados do dia → nº {p['numero']}\n\n"
            f"Preço e estoque podem mudar a qualquer momento.\n#publi · link de afiliado\n"
            f"#achadinhos #achadinhos{loja} #lupinhadaari")


def _csv(caminho: Path, campos: list[str], linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig + ";" abre certo no Excel BR
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        w.writerows(linhas)


def escrever_resumo(stories: list[dict], feed: list[dict], faltando: list) -> None:
    """Resumo no GitHub Actions (ou no terminal, rodando local)."""
    nr = sum(1 for l in stories if l.get("tipo") == "reserva")
    md = [f"## Posts do dia: {len(stories) - nr} stories + {nr} na reserva + {len(feed)} no feed", "",
          "| nº | Horário | Loja | Produto | Feed? |", "|---|---|---|---|---|"]
    nf = {l["numero"] for l in feed}
    md += [f"| {l['numero']} | {l['horario_sugerido']} | {l['loja']} | {l['produto'][:50]} | {'✅' if l['numero'] in nf else ''} |" for l in stories]
    if faltando:
        md += ["", "### Sem foto (ficaram de fora)",
               "Para entrar, salve a foto com este nome em `stories/fotos-reserva/` (ou preencha a coluna foto no estoque do robô):", "",
               "| nº | Loja | Produto | Salvar como | Link | Motivo |", "|---|---|---|---|---|---|"]
        md += [f"| {p['numero']} | {p['loja']} | {p['nome'][:50]} | `{p['slug']}.jpg` | {p['link']} | {motivo} |" for p, motivo in faltando]
    texto = "\n".join(md) + "\n"
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(texto)
    print(texto)


def _navegador(pw):
    try:
        return pw.chromium.launch()
    except Exception:
        return pw.chromium.launch(channel="chrome")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-numero", action="store_true", help="desliga o selo Achado nº X")
    ap.add_argument("--sem-busca", action="store_true", help="usa só fotos-reserva e a foto que veio do robô")
    ap.add_argument("--ramo-midia", default="midia", help="branch onde as imagens ficam públicas (feed.json)")
    args = ap.parse_args()

    produtos = ler_produtos()
    com_foto, faltando = [], []
    for p in produtos:
        foto, origem = (foto_reserva(p), "reserva") if args.sem_busca else achar_foto(p)
        if not foto and args.sem_busca and p.get("foto_url"):
            foto, origem = achar_foto(p)
        if foto:
            com_foto.append({**p, "_foto": foto})
        else:
            faltando.append((p, origem))
    feed = escolher_feed([p for p in com_foto if p.get("tipo") != "reserva"])

    from playwright.sync_api import sync_playwright
    SAIDA.mkdir(parents=True, exist_ok=True)
    SAIDA_FEED.mkdir(parents=True, exist_ok=True)
    hoje_dt = datetime.now(ZoneInfo("America/Sao_Paulo"))
    hoje = hoje_dt.strftime("%d/%m/%Y")
    horas = iter(horarios_stories(sum(1 for p in com_foto if p.get("tipo") != "reserva")))
    stories, feed_linhas, feed_posts = [], [], []
    with sync_playwright() as pw:
        nav = _navegador(pw)
        pag = nav.new_page(viewport={"width": 1080, "height": 1920})
        for i, p in enumerate(com_foto):
            pag.set_content(montar_html(p, p["_foto"], selo=not args.sem_numero), wait_until="networkidle", timeout=30000)
            arq = SAIDA / f"{p['numero']:02d}-story-{p['slug'][:40]}.png"
            pag.screenshot(path=str(arq), clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
            stories.append({"data": hoje, "numero": p["numero"], "produto": p["nome"], "loja": p["loja"],
                            "link_afiliada": p["link"], "tipo": p.get("tipo", "lista"),
                            "horario_sugerido": "reserva" if p.get("tipo") == "reserva" else next(horas),
                            "arquivo": arq.name, "mensagem_whatsapp": p.get("msg", "")})
        pag.set_viewport_size({"width": 1080, "height": 1350})
        for i, p in enumerate(feed):
            pag.set_content(montar_html(p, p["_foto"], selo=not args.sem_numero, feed=True), wait_until="networkidle", timeout=30000)
            arq = SAIDA_FEED / f"{p['numero']:02d}-feed-{p['slug'][:40]}.jpg"
            pag.screenshot(path=str(arq), type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
            leg = legenda_feed(p)
            feed_linhas.append({"data": hoje, "numero": p["numero"], "produto": p["nome"], "loja": p["loja"],
                                "horario": HORARIOS_FEED[i] if i < len(HORARIOS_FEED) else "", "arquivo": arq.name, "legenda": leg})
            feed_posts.append({"numero": p["numero"], "imagem": MIDIA.format(ramo=args.ramo_midia) + f"feed/{arq.name}",
                               "legenda": leg, "horario": feed_linhas[-1]["horario"]})
        nav.close()
    _csv(CSV, ["data", "numero", "produto", "loja", "link_afiliada", "tipo", "horario_sugerido", "arquivo", "mensagem_whatsapp"], stories)
    _csv(CSV_FEED, ["data", "numero", "produto", "loja", "horario", "arquivo", "legenda"], feed_linhas)
    FEED_JSON.write_text(json.dumps({"data": hoje_dt.date().isoformat(), "posts": feed_posts}, ensure_ascii=False, indent=1), encoding="utf-8")
    # mesma numeração em tudo: o nº é o da lista do dia
    NUMERACAO.write_text(json.dumps({str(p["numero"]): p["numero"] for p in produtos}), encoding="utf-8")
    escrever_resumo(stories, feed_linhas, faltando)


if __name__ == "__main__":
    main()
