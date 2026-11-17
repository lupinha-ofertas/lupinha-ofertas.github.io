"""Gera a página "Achados do dia" (achados/index.html) com os 15 produtos da lista.

Foto: fotos-reserva > foto da página da loja (og:image) > logo da Lupinha.
Uso:  python stories/gerar_pagina.py [--sem-busca]
"""
import argparse
import base64
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

PASTA = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA))
from lista import ler_produtos  # noqa: E402
from fotos import foto_reserva, url_da_foto_produto  # noqa: E402

RAIZ = PASTA.parent
DESTINO = RAIZ / "achados" / "index.html"
LOGO = PASTA / "assets" / "logo.png"  # vai embutido na página (não depende de outro arquivo)
NUMERACAO = PASTA / "saida" / "numeracao.json"  # gravado pelo gerar_artes.py


def numeracao(produtos: list[dict]) -> dict[int, int]:
    """nº da lista -> nº do achado (o mesmo das artes). Sem o arquivo, segue a lista."""
    if NUMERACAO.exists():
        mapa = {int(k): v for k, v in json.loads(NUMERACAO.read_text(encoding="utf-8")).items()}
        if all(p["numero"] in mapa for p in produtos):
            return mapa
    return {p["numero"]: p["numero"] for p in produtos}


def foto_src(p: dict, buscar: bool) -> str | None:
    arq = foto_reserva(p)
    if arq:
        return "../" + quote(arq.relative_to(RAIZ).as_posix())
    if buscar:
        try:
            return url_da_foto_produto(p)
        except Exception:
            return None
    return None


def card(p: dict, n: int, src: str | None) -> str:
    e = html.escape
    if src:
        foto, cls = f'<img src="{e(src)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="semFoto(this)">', "foto"
    else:
        foto, cls = "", "foto sem"
    preco = "" if p["loja"] == "Amazon" or not p["preco"] else f'<span class="preco">R$ {e(p["preco"])}</span>'
    return f'''    <article class="item{" semfoto" if not src else ""}" data-n="{n}">
      <div class="{cls}">{foto}<span class="num">nº {n}</span></div>
      <div class="info">
        <div class="meta"><span class="loja">{e(p["loja"])}</span>{preco}</div>
        <h2>{e(p["nome"])}</h2>
        <a class="btn" href="{e(p["link"])}" target="_blank" rel="sponsored noopener">Ver oferta <span>›</span></a>
      </div>
    </article>'''


def montar(produtos: list[dict], buscar: bool) -> str:
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")
    nums = numeracao(produtos)
    itens = sorted(((nums[p["numero"]], p, foto_src(p, buscar)) for p in produtos),
                   key=lambda t: (t[2] is None, t[0]))  # sem foto vão para o fim; nº não muda
    cards = "\n".join(card(p, n, src) for n, p, src in itens)
    logo = base64.b64encode(LOGO.read_bytes()).decode()
    return f'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Achados do dia · Lupinha da Ari</title>
<meta name="description" content="Os achadinhos do dia da Lupinha da Ari, com link direto para a oferta.">
<meta property="og:title" content="Achados do dia · Lupinha da Ari">
<meta name="theme-color" content="#C8435A">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='50' fill='%23C8435A'/%3E%3Ccircle cx='45' cy='44' r='22' fill='%23FDF3EA'/%3E%3Cline x1='60' y1='59' x2='74' y2='73' stroke='%23FDF3EA' stroke-width='9' stroke-linecap='round'/%3E%3C/svg%3E">
<style>
  :root{{--coral:#C8435A;--coral-dark:#A9354A;--cream:#FDF3EA;--ink:#4A1F2A}}
  *{{box-sizing:border-box;margin:0}}
  html,body{{min-height:100%}}
  body{{background:var(--coral);color:var(--cream);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
       background-image:radial-gradient(circle at 100% 0,rgba(255,255,255,.08) 0 220px,transparent 221px),radial-gradient(circle at 0 100%,rgba(255,255,255,.07) 0 260px,transparent 261px);
       background-attachment:fixed;display:flex;justify-content:center;padding:40px 16px 32px}}
  main{{width:100%;max-width:440px;display:flex;flex-direction:column;align-items:center;text-align:center}}
  .logo{{width:96px;height:96px;border-radius:50%;background:var(--cream);display:flex;align-items:center;justify-content:center;box-shadow:0 14px 34px rgba(70,10,25,.25)}}
  h1{{font-size:30px;font-weight:800;letter-spacing:-.02em;margin-top:16px;line-height:1}}
  .tag{{font-size:13px;letter-spacing:.22em;text-transform:uppercase;font-weight:600;opacity:.9;margin-top:8px}}
  .aviso{{font-size:13px;opacity:.85;margin-top:10px}}
  .lista{{width:100%;display:flex;flex-direction:column;gap:16px;margin-top:24px}}
  .item{{display:flex;gap:14px;background:var(--cream);color:var(--ink);border-radius:18px;padding:12px;box-shadow:0 6px 0 var(--coral-dark);text-align:left}}
  .foto{{position:relative;flex:none;width:112px;height:112px;border-radius:12px;overflow:hidden;background:#fff}}
  .foto img{{width:100%;height:100%;object-fit:contain;display:block}}
  .foto.sem{{background:var(--coral) url(data:image/png;base64,{logo}) center/86% auto no-repeat}}
  .foto.sem img{{display:none}}
  .num{{position:absolute;top:6px;left:6px;background:rgba(74,31,42,.75);color:var(--cream);font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px}}
  .info{{flex:1;min-width:0;display:flex;flex-direction:column;gap:6px}}
  .meta{{display:flex;justify-content:space-between;align-items:center;font-size:12px}}
  .loja{{background:#FCE3E7;color:var(--coral);font-weight:700;padding:2px 9px;border-radius:99px}}
  .preco{{font-weight:800;font-size:15px}}
  h2{{font-size:14px;font-weight:600;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
  a.btn{{margin-top:auto;display:flex;justify-content:center;align-items:center;gap:6px;padding:9px 12px;border-radius:12px;background:var(--coral);color:var(--cream);
        font-weight:700;font-size:15px;text-decoration:none;box-shadow:0 4px 0 var(--coral-dark);transition:transform .12s ease,box-shadow .12s ease}}
  a.btn:active{{transform:translateY(3px);box-shadow:0 1px 0 var(--coral-dark)}}
  footer{{font-size:12px;opacity:.85;margin-top:26px;line-height:1.5}}
  footer a{{color:var(--cream)}}
</style>
<script>
  // foto que não carregou: mostra o logo e manda o card para o fim da lista (o nº não muda)
  function semFoto(img){{var c=img.closest(".item"),l=c.parentNode;img.parentNode.classList.add("sem");c.classList.add("semfoto");
    Array.from(l.querySelectorAll(".semfoto")).sort(function(a,b){{return a.dataset.n-b.dataset.n}}).forEach(function(x){{l.appendChild(x)}})}}
</script>
</head>
<body>
<main>
  <div class="logo" aria-hidden="true">
    <svg width="64" height="64" viewBox="0 0 100 100">
      <line x1="62" y1="62" x2="86" y2="86" stroke="#C8435A" stroke-width="13" stroke-linecap="round"/>
      <circle cx="42" cy="42" r="34" fill="#C8435A"/>
      <path transform="translate(42,30) scale(.3)" d="M0 35 C0 0 -50 -10 -50 25 C-50 55 -15 75 0 90 C15 75 50 55 50 25 C50 -10 0 0 0 35Z" fill="#FDF3EA"/>
    </svg>
  </div>
  <h1>Achados do dia</h1>
  <div class="tag">{hoje}</div>
  <p class="aviso">Links de afiliada · preços e estoque podem mudar a qualquer momento</p>

  <section class="lista">
{cards}
  </section>

  <footer><a href="../">← todos os canais da lupinha</a><br>@lupinhadaari</footer>
</main>
</body>
</html>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-busca", action="store_true", help="não busca foto pelo link (só reserva/logo)")
    args = ap.parse_args()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(montar(ler_produtos(), not args.sem_busca), encoding="utf-8")
    print(f"Página gerada: {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
