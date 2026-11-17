"""Teste: busca a foto pelo link de 2 produtos de cada loja e mostra uma tabela.

Uso:  python stories/testar_fotos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lista import ler_produtos  # noqa: E402
from fotos import foto_do_link  # noqa: E402

LOJAS = ["Shopee", "Mercado Livre", "Amazon", "Shein"]


def main():
    produtos = ler_produtos()
    linhas = ["| Loja | Produto | Foto pelo link |", "|---|---|---|"]
    for loja in LOJAS:
        for p in [p for p in produtos if p["loja"] == loja][:2]:
            try:
                ok = foto_do_link(p)
                res = "✅ funcionou" if ok else "❌ página sem foto"
            except Exception as e:
                res = f"❌ {type(e).__name__}: {str(e)[:60]}"
            linhas.append(f"| {loja} | {p['nome'][:45]} | {res} |")
    tabela = "\n".join(linhas)
    print(tabela)
    Path(__file__).resolve().parent.joinpath("saida").mkdir(exist_ok=True)
    Path(__file__).resolve().parent.joinpath("saida", "teste-fotos.md").write_text(tabela + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
