"""Teste: busca a foto pelo link e mostra uma tabela.

1) Os casos que já saíram com foto errada no Mercado Livre (têm que ficar SEM foto ou com a foto certa).
2) Todos os produtos do Mercado Livre da lista do dia: título da página, se confere e a foto.
3) 2 produtos de cada uma das outras lojas.

Uso:  python stories/testar_fotos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lista import ler_produtos, slug  # noqa: E402
from fotos import foto_do_link, foto_e_titulo, titulo_confere  # noqa: E402

CASOS_ML = [  # já saíram com foto errada
    {"numero": "47 (19/11)", "nome": "Kit 60 Bolas Natal Lisas/foscas/glitter C/ Ponteira Enfeite",
     "link": "https://meli.la/1jTc4Vu"},
    {"numero": "8 (20/11)", "nome": "3x3m Cortina 300 Led Pisca Pisca Decoração Natal Duplo Volt",
     "link": "https://meli.la/1RJdfzi"},
]


def linha_ml(p: dict) -> str:
    try:
        foto, titulo = foto_e_titulo(p["link"])
        ok = titulo_confere(p["nome"], titulo)
        res = "✅ usa a foto" if ok and foto else ("⚪ sem foto na página" if not foto else "🚫 não confere: fica sem foto")
        return f"| {p['numero']} | {p['nome'][:40]} | {(titulo or '—')[:50]} | {res} | {foto or '—'} |"
    except Exception as e:
        return f"| {p['numero']} | {p['nome'][:40]} | — | ❌ {type(e).__name__}: {str(e)[:40]} | — |"


def main():
    produtos = ler_produtos()
    md = ["### Mercado Livre: casos que já deram foto errada", "",
          "| nº | Produto | Título da página | Resultado | Foto |", "|---|---|---|---|---|"]
    md += [linha_ml({**c, "slug": slug(c["nome"])}) for c in CASOS_ML]
    md += ["", "### Mercado Livre: lista do dia", "",
           "| nº | Produto | Título da página | Resultado | Foto |", "|---|---|---|---|---|"]
    md += [linha_ml(p) for p in produtos if p["loja"] == "Mercado Livre"]
    md += ["", "### Outras lojas (2 de cada)", "", "| Loja | Produto | Foto pelo link |", "|---|---|---|"]
    for loja in ["Shopee", "Amazon", "Shein"]:
        for p in [p for p in produtos if p["loja"] == loja][:2]:
            try:
                ok = foto_do_link(p)
                res = ("✅ funcionou" + (" (foto do robô)" if p.get("foto_url") else "")) if ok else "❌ sem foto"
            except Exception as e:
                res = f"❌ {type(e).__name__}: {str(e)[:60]}"
            md.append(f"| {loja} | {p['nome'][:45]} | {res} |")
    tabela = "\n".join(md)
    print(tabela)
    Path(__file__).resolve().parent.joinpath("saida").mkdir(exist_ok=True)
    Path(__file__).resolve().parent.joinpath("saida", "teste-fotos.md").write_text(tabela + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
