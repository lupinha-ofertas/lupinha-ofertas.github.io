"""Acha a foto de cada produto.

Ordem: 1) pasta fotos-reserva (o que a Ari salvou manualmente, sempre ganha);
       2) foto que veio do robô em enviar/dados.json (Shopee, pela API de afiliados);
       3) Mercado Livre e Shein: foto da página da loja (og:image);
       4) Amazon: foto pelo código do produto (ASIN);
       sem foto -> reserva ou logo.
"""
import re
import urllib.request
from pathlib import Path

PASTA = Path(__file__).resolve().parent
RESERVA = PASTA / "fotos-reserva"
CACHE = PASTA / "saida" / "fotos"
EXTS = (".jpg", ".jpeg", ".png", ".webp")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def foto_reserva(produto: dict) -> Path | None:
    """Arquivo em fotos-reserva cujo nome é o nome do produto (ou o começo dele)."""
    from lista import slug
    alvo = produto["slug"]
    for arq in sorted(RESERVA.iterdir()) if RESERVA.exists() else []:
        if arq.suffix.lower() not in EXTS:
            continue
        s = slug(arq.stem)
        if s and (s == alvo or alvo.startswith(s) or s.startswith(alvo[:25])):
            return arq
    return None


def _baixar(url: str, timeout: int = 20) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.geturl()


LOJAS_PELO_LINK = ("Mercado Livre", "Shein")  # Shopee bloqueia; usa a foto do robô, reserva ou logo
AMAZON_FOTO = "https://m.media-amazon.com/images/P/{asin}.01._SCLZZZZZZZ_SL500_.jpg"  # pelo código (ASIN)


def url_foto_amazon(link: str) -> str | None:
    """Foto pelo código do produto. Produto novo às vezes não tem: vem 1x1 e cai na reserva/logo."""
    m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", link)
    return AMAZON_FOTO.format(asin=m.group(1)) if m else None


class FotoNaoConfere(Exception):
    """A página do link é de outro produto (ou é vitrine/perfil): a foto dela não serve."""


PALAVRAS_FRACAS = {"para", "com", "sem", "kit", "unidades", "unidade", "pecas", "peca", "feminino", "feminina",
                   "masculino", "masculina", "cor", "tamanho", "novo", "nova", "original", "promocao", "mercado",
                   "livre", "shein", "loja", "oficial", "frete", "gratis", "envio", "full"}


def _palavras(texto: str) -> set[str]:
    from lista import slug
    return {w for w in slug(texto, 400).split("-") if len(w) >= 4 and not w.isdigit() and w not in PALAVRAS_FRACAS}


def confere(titulo: str | None, nome: str) -> bool:
    """O título da página fala do mesmo produto? Sem título não dá para conferir: aceita."""
    if not titulo:
        return True
    a, b = _palavras(titulo), _palavras(nome)
    if not a or not b:
        return True
    comuns = a & b
    return len(comuns) >= 2 or len(comuns) / min(len(a), len(b)) >= 0.5


def url_da_foto_produto(produto: dict) -> str | None:
    """Foto do robô (Shopee, pela API) ou, no ML e na Shein, a foto da página da loja."""
    if produto.get("foto_url"):
        return produto["foto_url"]
    if produto.get("loja") in LOJAS_PELO_LINK:
        return url_da_foto(produto["link"], produto.get("nome"))
    if produto.get("loja") == "Amazon":
        return url_foto_amazon(produto["link"])
    return None


def titulo_da_pagina(texto: str) -> str | None:
    import html
    for padrao in (r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
                   r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title',
                   r'<title[^>]*>([^<]+)</title>'):
        m = re.search(padrao, texto, re.I)
        if m and m.group(1).strip():
            return html.unescape(m.group(1)).strip()
    return None


def url_da_foto(link: str, nome: str | None = None) -> str | None:
    pagina, final = _baixar(link)
    texto = pagina.decode("utf-8", "ignore")
    if nome:
        titulo = titulo_da_pagina(texto)
        if not confere(titulo, nome):
            raise FotoNaoConfere(f"a página do link é de outra coisa: \"{(titulo or '')[:60]}\" ({final[:60]})")
    for padrao in (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        r'"hiRes":"(https://[^"]+)"',                    # Amazon
        r'data-old-hires=["\'](https://[^"\']+)',        # Amazon
    ):
        m = re.search(padrao, texto)
        if m:
            return m.group(1).replace("&amp;", "&")
    return None


def foto_do_link(produto: dict) -> Path | None:
    url = url_da_foto_produto(produto)
    if not url:
        return None
    dados, _ = _baixar(url)
    if len(dados) < 2000:  # ícone ou imagem vazia
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / f"{produto['slug']}.jpg"
    destino.write_bytes(dados)
    return destino


def achar_foto(produto: dict) -> tuple[Path | None, str]:
    arq = foto_reserva(produto)
    if arq:
        return arq, "reserva"
    try:
        arq = foto_do_link(produto)
        if arq:
            return arq, "link"
    except FotoNaoConfere as e:  # melhor ficar sem arte do que postar foto de outro produto
        return None, f"foto não confere: {e}"
    except Exception as e:  # loja bloqueou, caiu etc.
        return None, f"falhou ({type(e).__name__})"
    return None, ("sem foto (salve uma reserva)" if produto.get("loja") == "Shopee" and not produto.get("foto_url")
                  else "falhou (loja sem foto)")
