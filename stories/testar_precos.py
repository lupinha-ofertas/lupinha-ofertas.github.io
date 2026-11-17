"""Teste: dá para ler preço antigo e desconto na página do ML e da Shein? Só lê."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fotos import _baixar  # noqa: E402

LINKS = {"ML": ["https://meli.la/1quiJkp", "https://meli.la/31WdiyL", "https://meli.la/1fobtdq"],
         "Shein": ["https://onelink.shein.com/60/686vjv2ygd4e?ismg_ol=DGGKjTgPFFD_01_KOC-C",
                   "https://onelink.shein.com/60/686vheakrxvp?ismg_ol=9OVwhkQyDvZ_01_KOC-C"]}
PADROES = [r'"original_price":\s*[\d.]+', r'"price":\s*[\d.]+', r'andes-money-amount--previous[^>]*aria-label="[^"]+"',
           r'aria-label="Antes:[^"]+"', r'"discount_label":"[^"]+"', r'\d+% OFF', r'"retailPrice":\{[^}]{0,120}',
           r'"salePrice":\{[^}]{0,120}', r'"unit_discount":"?\d+', r'"discountPrice"[^,]{0,80}', r'itemprop="price"[^>]*']
for loja, links in LINKS.items():
    for l in links:
        try:
            pag, final = _baixar(l)
            t = pag.decode("utf-8", "ignore")
            print(f"\n== {loja} {final[:90]} ({len(t)} bytes)")
            for p in PADROES:
                ms = re.findall(p, t)[:2]
                if ms:
                    print("  ", p[:25], "->", [m[:110] for m in ms])
        except Exception as e:
            print(loja, l, "ERRO", e)
