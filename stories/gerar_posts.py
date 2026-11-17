"""Gera a página "Posts do dia" (posts/index.html): cada story com a arte e o link para copiar,
os posts do feed com a legenda para copiar, e o botão para baixar tudo (.zip).

As imagens ficam públicas no branch "midia" (o workflow publica lá todo dia).
Uso:  python stories/gerar_posts.py [--ramo-midia midia]
"""
import argparse
import csv
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PASTA = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA))
from gerar_artes import CSV, CSV_FEED, MIDIA  # noqa: E402

DESTINO = PASTA.parent / "posts" / "index.html"


def ler(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def montar(stories: list[dict], feed: list[dict], base: str) -> str:
    e = html.escape
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m")

    def card(tipo, l, img, copiar, rotulo, extra=""):
        return f'''    <article class="card" data-id="{tipo}-{l["numero"]}">
      <a href="{e(img)}" target="_blank" rel="noopener"><img src="{e(img)}" alt="" loading="lazy"></a>
      <div class="info">
        <div class="top"><span class="tag">nº {l["numero"]} · {e(l["loja"])}</span><span class="hora">{e(l.get("horario_sugerido") or l.get("horario") or "")}</span></div>
        <h2>{e(l["produto"])}</h2>{extra}
        <div class="acoes">
          <button class="copiar" data-txt="{e(copiar)}">{rotulo}</button>
          <a class="abrir" href="{e(img)}" target="_blank" rel="noopener">Abrir arte</a>
          <button class="feito" title="Marcar como postado">✓</button>
        </div>
      </div>
    </article>'''

    st = "\n".join(card("s", l, base + "stories/" + l["arquivo"], l["link_afiliada"], "Copiar link") for l in stories)
    fd = "\n".join(card("f", l, base + "feed/" + l["arquivo"], l["legenda"], "Copiar legenda",
                        f'<details><summary>Ver legenda</summary><pre>{e(l["legenda"])}</pre></details>') for l in feed)
    return f'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Posts do dia · Lupinha</title>
<style>
  :root{{--coral:#C8435A;--coral-dark:#A9354A;--cream:#FDF3EA;--ink:#4A1F2A;--green:#1F9D4E}}
  *{{box-sizing:border-box;margin:0}}
  body{{background:var(--coral);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;padding:24px 16px 48px}}
  main{{max-width:760px;margin:0 auto}}
  header{{color:var(--cream);text-align:center}}
  header h1{{font-size:26px;font-weight:800}}
  header p{{font-size:14px;opacity:.9;margin-top:6px;line-height:1.45}}
  .zip{{display:inline-block;margin-top:14px;background:var(--cream);color:var(--ink);font-weight:800;padding:12px 20px;border-radius:14px;text-decoration:none;box-shadow:0 5px 0 var(--coral-dark)}}
  h3{{color:var(--cream);font-size:19px;margin:26px 4px 10px}}
  .card{{display:flex;gap:14px;background:var(--cream);border-radius:18px;padding:12px;margin-bottom:12px;box-shadow:0 5px 0 var(--coral-dark)}}
  .card.ok{{opacity:.45}}
  .card img{{width:96px;border-radius:10px;display:block;background:#fff}}
  .info{{flex:1;min-width:0;display:flex;flex-direction:column;gap:6px}}
  .top{{display:flex;justify-content:space-between;font-size:13px}}
  .tag{{background:#FCE3E7;color:var(--coral);font-weight:700;padding:2px 9px;border-radius:99px}}
  .hora{{font-weight:800}}
  h2{{font-size:14px;font-weight:600;line-height:1.3}}
  details{{font-size:13px}} summary{{cursor:pointer;color:var(--coral);font-weight:600}}
  pre{{white-space:pre-wrap;font-family:inherit;background:#fff;border-radius:10px;padding:8px;margin-top:6px}}
  .acoes{{display:flex;gap:8px;margin-top:auto}}
  .acoes button,.acoes a{{border:0;border-radius:10px;padding:9px 12px;font-weight:700;font-size:14px;cursor:pointer;text-decoration:none;text-align:center}}
  .copiar{{flex:1;background:var(--coral);color:var(--cream)}}
  .abrir{{background:#FCE3E7;color:var(--coral)}}
  .feito{{background:#E6F4EA;color:var(--green)}}
</style>
</head>
<body>
<main>
  <header>
    <h1>📲 Posts de {hoje}</h1>
    <p>{len(stories)} stories (com adesivo de link) e {len(feed)} posts no feed.<br>
    Baixe tudo, suba a arte, toque em <b>Copiar link</b> e cole no adesivo. Marque ✓ quando postar.</p>
    <a class="zip" href="{e(base)}posts-do-dia.zip">⬇️ Baixar tudo (.zip)</a>
  </header>
  <h3>📸 Stories · cole o link no adesivo</h3>
{st or '<p style="color:var(--cream)">Nenhum story hoje.</p>'}
  <h3>🖼️ Feed · legenda pronta (link na bio)</h3>
{fd or '<p style="color:var(--cream)">Nenhum post de feed hoje.</p>'}
</main>
<script>
  var DIA = {json.dumps(hoje)}, feitos = {{}};
  try {{ feitos = JSON.parse(localStorage.getItem("posts-" + DIA) || "{{}}"); }} catch (e) {{}}
  document.querySelectorAll(".card").forEach(function (c) {{
    if (feitos[c.dataset.id]) c.classList.add("ok");
    c.querySelector(".feito").onclick = function () {{
      c.classList.toggle("ok"); feitos[c.dataset.id] = c.classList.contains("ok");
      try {{ localStorage.setItem("posts-" + DIA, JSON.stringify(feitos)); }} catch (e) {{}}
    }};
    var b = c.querySelector(".copiar");
    b.onclick = function () {{
      var t = b.textContent;
      navigator.clipboard.writeText(b.dataset.txt).then(function () {{ b.textContent = "Copiado!"; setTimeout(function () {{ b.textContent = t; }}, 1500); }})
        .catch(function () {{ prompt("Copie:", b.dataset.txt); }});
    }};
  }});
</script>
</body>
</html>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ramo-midia", default="midia")
    args = ap.parse_args()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(montar(ler(CSV), ler(CSV_FEED), MIDIA.format(ramo=args.ramo_midia)), encoding="utf-8")
    print(f"Página gerada: {DESTINO.relative_to(PASTA.parent)}")


if __name__ == "__main__":
    main()
