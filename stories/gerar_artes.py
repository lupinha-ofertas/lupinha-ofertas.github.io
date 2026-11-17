"""Gera as artes de story (1080x1920, PNG) dos achados do dia, no template da Lupinha.

Uso:
  python stories/gerar_artes.py                 # as 5 melhores do dia (maior desconto, máx. 2 por loja)
  python stories/gerar_artes.py --numeros 2 6 4 # escolha manual (números da lista do dia)
  python stories/gerar_artes.py --sem-numero    # sem o selo "Achado nº X"
  python stories/gerar_artes.py --sem-busca     # não tenta buscar foto pelo link

Sem foto (nem reserva nem pelo link) o produto é trocado pelo próximo da lista
que tenha foto, e o resumo avisa qual arquivo salvar em stories/fotos-reserva/.
Com --rascunho a arte sai com um espaço de foto vazio, só para conferir o layout.

Também gera stories/saida/agendar-stories.csv (para agendar no Business Suite).
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
CSV = PASTA / "saida" / "agendar-stories.csv"
NUMERACAO = PASTA / "saida" / "numeracao.json"  # nº da lista -> nº do achado (a página usa)
HORARIOS = ["09:00", "12:00", "15:00", "18:00", "21:00"]  # horário sugerido de cada story
LOGO = PASTA / "assets" / "logo.png"  # logo oficial (700x137); se faltar, usa o desenhado

ROSA, ROSA_ESC, CREME, TINTA, CINZA, BORDA = "#C9425C", "#A8334B", "#FFF4EA", "#3A1F2B", "#6E5560", "#D9A3AE"


def _data_uri(arq: Path) -> str:
    tipo = mimetypes.guess_type(arq.name)[0] or "image/jpeg"
    return f"data:{tipo};base64,{base64.b64encode(arq.read_bytes()).decode()}"


def _logo() -> str:
    if LOGO.exists():
        return f'<img src="{_data_uri(LOGO)}" alt="" style="width:700px;height:137px;display:block;object-fit:contain;object-position:left">'
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


def montar_html(p: dict, foto: Path | None, selo: bool = True) -> str:
    n = p["numero"] if selo else None
    amazon = p["loja"] == "Amazon"
    if amazon:
        corpo = _foto(foto, 670, n, None) + _nome(p["nome"])
        if p["motivo"]:
            corpo += f'<div style="font-size:34px;font-weight:500;line-height:1.35;color:{CINZA}">⭐ {html.escape(p["motivo"])}</div>'
        corpo += (f'<div style="display:flex;align-items:center;gap:20px;background:{ROSA};border-radius:28px;padding:26px 30px">'
                  f'<svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="{CREME}" stroke-width="2.4" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><line x1="15.5" y1="15.5" x2="21" y2="21"/></svg>'
                  f'<div style="font-size:50px;font-weight:800;letter-spacing:-1px;color:{CREME}">Confere o preço no link</div></div>')
        rodape = "*Preço e estoque podem mudar a qualquer momento"
    else:
        extras = sum(bool(x) for x in (p["preco_antigo"], p["parcelas"], p["cupom"]))
        corpo = _foto(foto, 740 - 60 * extras, n, p["desconto"]) + _nome(p["nome"])
        precos = ""
        if p["preco_antigo"]:
            precos += f'<div style="font-size:34px;font-weight:500;color:{CINZA};text-decoration:line-through">R$ {p["preco_antigo"]}</div>'
        precos += f'<div style="font-size:92px;font-weight:800;line-height:1.05;letter-spacing:-2px;color:{ROSA}">R$ {p["preco"]}</div>'
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
<div style="width:1080px;height:1920px;position:relative;overflow:hidden;background:{ROSA};font-family:'Inter',system-ui,sans-serif;color:{CREME};padding:190px 70px 200px;display:flex;flex-direction:column;gap:32px">
<div style="position:absolute;right:-260px;top:-300px;width:760px;height:760px;border-radius:50%;background:rgba(255,244,234,.08)"></div>
<div style="position:absolute;left:-300px;bottom:-320px;width:820px;height:820px;border-radius:50%;background:rgba(255,244,234,.08)"></div>
<div style="position:relative;display:flex;align-items:center;justify-content:space-between;gap:24px;height:137px">
{_logo()}
<div style="font-size:24px;font-weight:700;padding:10px 22px;border-radius:999px;border:3px solid {CREME};flex-shrink:0">Publicidade</div></div>
<div style="position:relative;background:{CREME};border-radius:48px;padding:44px;display:flex;flex-direction:column;gap:24px;color:{TINTA}">{corpo}</div>
<div style="position:relative;display:flex;align-items:center;gap:24px;background:{CREME};border-radius:999px;padding:16px 28px 16px 16px;height:130px">
<div style="width:98px;height:98px;border-radius:50%;background:{ROSA};display:flex;align-items:center;justify-content:center;flex-shrink:0">
<svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="{CREME}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5"/></svg></div>
<div style="flex-grow:1;height:86px;border-radius:999px;border:3px dashed {BORDA};display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:500;color:{CINZA}">toque no link para comprar</div></div>
<div style="position:relative;display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center">
<div style="font-size:32px;font-weight:700">@lupinhadaari</div>
<div style="font-size:26px;font-weight:600">{rodape}</div></div>
</div></body></html>'''


def _ordem(produtos: list[dict]) -> list[dict]:
    """Maior desconto primeiro; empate (ou sem desconto) segue a ordem da lista."""
    return sorted(produtos, key=lambda p: (-int(p["desconto"] or 0), p["numero"]))


def escolher_melhores(produtos: list[dict], quantos: int = 5, por_loja: int = 2) -> list[dict]:
    """As melhores sem olhar foto (usado no --rascunho). Máx. 2 por loja."""
    escolhidos, conta = [], {}
    for p in _ordem(produtos):
        if conta.get(p["loja"], 0) < por_loja:
            escolhidos.append(p)
            conta[p["loja"]] = conta.get(p["loja"], 0) + 1
        if len(escolhidos) == quantos:
            break
    return escolhidos


def escolher_com_foto(produtos, quantos, por_loja, achar):
    """Como escolher_melhores, mas pula quem não tem foto e pega o próximo da lista.
    Se nem assim completar (ex.: só 2 lojas com foto), libera o limite por loja."""
    cache, faltando = {}, {}

    def foto(p):
        if p["numero"] not in cache:
            cache[p["numero"]] = achar(p)
            if not cache[p["numero"]][0]:
                faltando[p["numero"]] = (p, cache[p["numero"]][1])
        return cache[p["numero"]]

    escolhidos, conta = [], {}
    for limite in (por_loja, quantos):
        for p in _ordem(produtos):
            if len(escolhidos) == quantos:
                break
            if any(e[0]["numero"] == p["numero"] for e in escolhidos) or conta.get(p["loja"], 0) >= limite:
                continue
            arq, origem = foto(p)
            if arq:
                escolhidos.append((p, arq, origem))
                conta[p["loja"]] = conta.get(p["loja"], 0) + 1
    return escolhidos, list(faltando.values())


def escrever_csv(linhas: list[dict]) -> None:
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig + ";" abre certo no Excel BR
        w = csv.DictWriter(f, fieldnames=["data", "numero", "produto", "loja", "link_afiliada", "horario_sugerido", "arquivo"], delimiter=";")
        w.writeheader()
        w.writerows(linhas)


def escrever_resumo(linhas: list[dict], faltando: list) -> None:
    """Resumo no GitHub Actions (ou no terminal, rodando local)."""
    md = ["## Stories do dia", "", "| nº | Horário | Loja | Produto | Arte |", "|---|---|---|---|---|"]
    md += [f"| {l['numero']} | {l['horario_sugerido']} | {l['loja']} | {l['produto'][:50]} | {l['arquivo']} |" for l in linhas]
    if faltando:
        md += ["", "### Sem foto (trocados pelo próximo da lista)",
               "Para usar algum deles, salve a foto com este nome em `stories/fotos-reserva/`:", "",
               "| Loja | Produto | Salvar como | Link | Motivo |", "|---|---|---|---|---|"]
        md += [f"| {p['loja']} | {p['nome'][:50]} | `{p['slug']}.jpg` | {p['link']} | {motivo} |" for p, motivo in faltando]
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
    ap.add_argument("--numeros", type=int, nargs="*", help="escolha manual (padrão: as 5 melhores)")
    ap.add_argument("--quantos", type=int, default=5, help="quantos stories por dia (padrão 5)")
    ap.add_argument("--sem-numero", action="store_true", help="desliga o selo Achado nº X")
    ap.add_argument("--sem-busca", action="store_true", help="usa só fotos-reserva")
    ap.add_argument("--rascunho", action="store_true", help="gera mesmo sem foto (espaço vazio)")
    args = ap.parse_args()

    def achar(p):
        return (foto_reserva(p), "reserva") if args.sem_busca else achar_foto(p)

    produtos = ler_produtos()
    if args.numeros or args.rascunho:  # escolha fixa: não troca ninguém
        if args.numeros:
            por_n = {p["numero"]: p for p in produtos}
            fixos = [por_n[n] for n in args.numeros if n in por_n]
        else:
            fixos = escolher_melhores(produtos, args.quantos)
        escolhidos, faltando = [], []
        for p in fixos:
            arq, origem = achar(p)
            if arq or args.rascunho:
                escolhidos.append((p, arq, origem))
            else:
                faltando.append((p, origem))
    else:
        escolhidos, faltando = escolher_com_foto(produtos, args.quantos, 2, achar)

    from playwright.sync_api import sync_playwright
    SAIDA.mkdir(parents=True, exist_ok=True)
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")
    linhas = []
    with sync_playwright() as pw:
        nav = _navegador(pw)
        pag = nav.new_page(viewport={"width": 1080, "height": 1920})
        for ordem, (p, foto, origem) in enumerate(escolhidos, 1):
            p = {**p, "numero": ordem}  # "Achado nº" segue a ordem dos selecionados
            pag.set_content(montar_html(p, foto, selo=not args.sem_numero), wait_until="networkidle", timeout=30000)
            arq = SAIDA / f"achado-{ordem:02d}-{p['slug'][:40]}.png"
            pag.screenshot(path=str(arq), clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
            print(f"✅ nº {ordem} {p['loja']}: {arq.name} (foto: {origem if foto else 'sem foto'})")
            linhas.append({"data": hoje, "numero": ordem, "produto": p["nome"], "loja": p["loja"], "link_afiliada": p["link"],
                           "horario_sugerido": HORARIOS[ordem - 1] if ordem <= len(HORARIOS) else "", "arquivo": arq.name})
        nav.close()
    escrever_csv(linhas)
    # mesma numeração na página: as artes são 1..5, o resto segue a ordem da lista
    usados = [p["numero"] for p, _, _ in escolhidos]
    resto = [p["numero"] for p in produtos if p["numero"] not in usados]
    NUMERACAO.write_text(json.dumps({str(n): i for i, n in enumerate(usados + resto, 1)}), encoding="utf-8")
    escrever_resumo(linhas, faltando)


if __name__ == "__main__":
    main()
