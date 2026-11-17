"""Gera a página "Posts do dia" (posts/index.html): cada arte numerada com Baixar imagem,
Copiar link e Copiar texto (adesivo) nos stories, Copiar legenda no feed, e Baixar todas.

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


TEXTO_ADESIVO = "Clique para comprar"  # texto que vai no adesivo de link do story


def montar(stories: list[dict], feed: list[dict], base: str) -> str:
    e = html.escape
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m")

    def card(tipo, l, img, texto, rotulo_texto, link=None, wpp=None):
        botoes = f'<button class="baixar" data-url="{e(img)}" data-nome="{e(l["arquivo"])}">⬇️ Baixar imagem</button>'
        if link:
            botoes += f'<button class="copiar" data-txt="{e(link)}">🔗 Copiar link</button>'
        botoes += f'<button class="copiar" data-txt="{e(texto)}">📝 {rotulo_texto}</button>'
        if wpp:
            botoes += f'<button class="copiar wpp" data-txt="{e(wpp)}">💬 Copiar mensagem do WhatsApp</button>'
        prev = f'<pre>{e(texto)}</pre>' if not link else f'<p class="adesivo">Adesivo: <b>{e(texto)}</b></p>'
        return f'''    <article class="card" data-id="{tipo}-{l["numero"]}" data-url="{e(img)}" data-nome="{e(l["arquivo"])}">
      <div class="foto"><img src="{e(img)}" alt="" loading="lazy"><span class="num">{l["numero"]}</span></div>
      <div class="info">
        <div class="top"><span class="tag">{e(l["loja"])}</span><span class="hora">🕒 {e(l.get("horario_sugerido") or l.get("horario") or "")}</span></div>
        <h2>{e(l["produto"])}</h2>
        {prev}
        <div class="acoes">{botoes}</div>
        <button class="feito">✓ Marcar como postado</button>
      </div>
    </article>'''

    def cards_story(grupo, linhas):
        return "\n".join(card(grupo, l, base + "stories/" + l["arquivo"], TEXTO_ADESIVO, "Copiar texto do adesivo",
                               l["link_afiliada"], l.get("mensagem_whatsapp")) for l in linhas)
    reserva = [l for l in stories if l.get("tipo") == "reserva"]
    stories = [l for l in stories if l.get("tipo") != "reserva"]
    st, rs = cards_story("s", stories), cards_story("r", reserva)
    fd = "\n".join(card("f", l, base + "feed/" + l["arquivo"], l["legenda"], "Copiar legenda") for l in feed)
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
  main{{max-width:1180px;margin:0 auto}}
  header{{color:var(--cream);text-align:center}}
  header h1{{font-size:28px;font-weight:800}}
  header p{{font-size:15px;opacity:.92;margin-top:8px;line-height:1.5}}
  .secao{{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:30px 4px 12px}}
  .secao h3{{color:var(--cream);font-size:20px}}
  .todas{{background:var(--cream);color:var(--ink);border:0;font-weight:800;font-size:15px;padding:11px 18px;border-radius:12px;cursor:pointer;box-shadow:0 4px 0 var(--coral-dark)}}
  .grade{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px}}
  .card{{background:var(--cream);border-radius:18px;padding:12px;box-shadow:0 5px 0 var(--coral-dark);display:flex;flex-direction:column;gap:10px}}
  .card.ok{{opacity:.45}}
  .foto{{position:relative}}
  .foto img{{width:100%;border-radius:12px;display:block;background:#fff}}
  .num{{position:absolute;top:8px;left:8px;background:var(--ink);color:var(--cream);font-weight:800;font-size:22px;min-width:44px;height:44px;padding:0 10px;border-radius:99px;display:flex;align-items:center;justify-content:center}}
  .info{{display:flex;flex-direction:column;gap:8px;flex:1}}
  .top{{display:flex;justify-content:space-between;font-size:13px}}
  .tag{{background:#FCE3E7;color:var(--coral);font-weight:700;padding:2px 9px;border-radius:99px}}
  .hora{{font-weight:800}}
  h2{{font-size:15px;font-weight:600;line-height:1.3}}
  .adesivo{{font-size:13px;color:#7a5560}}
  pre{{white-space:pre-wrap;font-family:inherit;font-size:13px;background:#fff;border-radius:10px;padding:8px;max-height:120px;overflow:auto}}
  .acoes{{display:flex;flex-direction:column;gap:8px;margin-top:auto}}
  .acoes button{{border:0;border-radius:10px;padding:11px;font-weight:700;font-size:15px;cursor:pointer;background:var(--coral);color:var(--cream)}}
  .acoes .baixar{{background:var(--ink)}}
  .acoes .wpp{{background:var(--green)}}
  .feito{{border:0;border-radius:10px;padding:8px;font-weight:700;font-size:13px;cursor:pointer;background:#E6F4EA;color:var(--green)}}
</style>
</head>
<body>
<main>
  <header>
    <h1>📲 Posts de {hoje}</h1>
    <p>{len(stories)} stories, {len(feed)} posts no feed e {len(reserva)} ofertas na reserva. Os números são os mesmos da página Achados do dia.<br>
    Story: <b>Baixar imagem</b> → sobe no Business Suite → adesivo de link → <b>Copiar link</b> e <b>Copiar texto</b>.</p>
  </header>
  <div class="secao"><h3>📸 Stories (com adesivo de link)</h3><button class="todas" data-grupo="s">⬇️ Baixar todos os stories</button></div>
  <section class="grade">
{st or '<p style="color:var(--cream)">Nenhum story hoje.</p>'}
  </section>
  <div class="secao"><h3>🖼️ Feed (legenda pronta, link na bio)</h3><button class="todas" data-grupo="f">⬇️ Baixar os {len(feed)} do feed</button></div>
  <section class="grade">
{fd or '<p style="color:var(--cream)">Nenhum post de feed hoje.</p>'}
  </section>
  <div class="secao"><h3>🗂️ Reserva ({len(reserva)} ofertas Shopee extras)</h3><button class="todas" data-grupo="r">⬇️ Baixar toda a reserva</button></div>
  <section class="grade">
{rs or '<p style="color:var(--cream)">Sem reserva hoje.</p>'}
  </section>
</main>
<script>
  var DIA = {json.dumps(hoje)}, feitos = {{}};
  try {{ feitos = JSON.parse(localStorage.getItem("posts-" + DIA) || "{{}}"); }} catch (e) {{}}
  function baixar(url, nome) {{
    return fetch(url).then(function (r) {{ if (!r.ok) throw 0; return r.blob(); }}).then(function (b) {{
      var a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = nome;
      document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () {{ URL.revokeObjectURL(a.href); }}, 5000);
    }}).catch(function () {{ window.open(url, "_blank"); }});
  }}
  function aviso(b, t) {{ var o = b.textContent; b.textContent = t; setTimeout(function () {{ b.textContent = o; }}, 1500); }}
  document.querySelectorAll(".card").forEach(function (c) {{
    if (feitos[c.dataset.id]) c.classList.add("ok");
    c.querySelector(".feito").onclick = function () {{
      c.classList.toggle("ok"); feitos[c.dataset.id] = c.classList.contains("ok");
      try {{ localStorage.setItem("posts-" + DIA, JSON.stringify(feitos)); }} catch (e) {{}}
    }};
  }});
  document.querySelectorAll(".baixar").forEach(function (b) {{
    b.onclick = function () {{ aviso(b, "Baixando…"); baixar(b.dataset.url, b.dataset.nome); }};
  }});
  document.querySelectorAll(".copiar").forEach(function (b) {{
    b.onclick = function () {{
      navigator.clipboard.writeText(b.dataset.txt).then(function () {{ aviso(b, "✅ Copiado!"); }})
        .catch(function () {{ window.prompt("Copie:", b.dataset.txt); }});
    }};
  }});
  document.querySelectorAll(".todas").forEach(function (b) {{
    b.onclick = async function () {{
      var cards = document.querySelectorAll('.card[data-id^="' + b.dataset.grupo + '-"]');
      for (var i = 0; i < cards.length; i++) {{
        b.textContent = "Baixando " + (i + 1) + " de " + cards.length + "…";
        await baixar(cards[i].dataset.url, cards[i].dataset.nome);
        await new Promise(function (r) {{ setTimeout(r, 400); }});
      }}
      b.textContent = "✅ Pronto (" + cards.length + " imagens)";
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
