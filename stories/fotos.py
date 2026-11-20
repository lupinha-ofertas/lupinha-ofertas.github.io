"""Acha a foto de cada produto.

Ordem: 1) pasta fotos-reserva (o que a Ari salvou manualmente, sempre ganha);
       2) foto que veio do robô em enviar/dados.json (Shopee, pela API de afiliados);
       3) Mercado Livre e Shein: foto da página da loja (og:image);
          no Mercado Livre só vale se o título da página bater com o nome do produto
          (o link curto às vezes abre outra página e a foto era de outro produto:
          relógio no achado 47 de 19/11, banquetas no achado 8 de 20/11);
       4) Amazon: foto pelo código do produto (ASIN);
       sem foto -> reserva ou logo.
"""
import html
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
    """A página do link é de outro produto: melhor ficar sem foto do que com foto errada."""


PALAVRAS_FRACAS = {"com", "para", "por", "sem", "the", "and", "kit", "cor", "cores", "novo", "nova",
                   "original", "promocao", "oferta", "envio", "frete", "gratis", "full", "volt", "bivolt"}


def _palavras(texto: str) -> set[str]:
    from lista import slug
    return {w for w in slug(texto, 400).split("-")
            if (len(w) >= 3 or w.isdigit()) and w not in PALAVRAS_FRACAS}


def titulo_confere(nome: str, titulo: str | None) -> bool:
    """O título da página tem a maioria das palavras do nome do produto (ao menos 2 e metade)."""
    if not titulo:
        return False
    nome_p, tit_p = _palavras(nome), _palavras(titulo)
    if not nome_p:
        return False
    iguais = len(nome_p & tit_p)
    return iguais >= min(2, len(nome_p)) and iguais / len(nome_p) >= 0.5


def url_da_foto_produto(produto: dict) -> str | None:
    """Foto do robô (Shopee, pela API) ou, no ML e na Shein, a foto da página da loja."""
    if produto.get("foto_url"):
        return produto["foto_url"]
    if produto.get("loja") == "Mercado Livre":
        foto, titulo = foto_e_titulo(produto["link"])
        if foto and not titulo_confere(produto["nome"], titulo):
            raise FotoNaoConfere(f"página é de outro produto: {(titulo or 'sem título')[:60]}")
        return foto
    if produto.get("loja") in LOJAS_PELO_LINK:
        return url_da_foto(produto["link"])
    if produto.get("loja") == "Amazon":
        return url_foto_amazon(produto["link"])
    return None


def foto_e_titulo(link: str) -> tuple[str | None, str | None]:
    """Foto (og:image) e título (og:title ou <title>) da página que o link abre."""
    pagina, _ = _baixar(link)
    texto = pagina.decode("utf-8", "ignore")
    titulo = None
    for padrao in (r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
                   r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title',
                   r"<title[^>]*>(.*?)</title>"):
        m = re.search(padrao, texto, re.S | re.I)
        if m:
            titulo = html.unescape(m.group(1)).strip()
            break
    return _og_image(texto), titulo


def url_da_foto(link: str) -> str | None:
    pagina, _ = _baixar(link)
    return _og_image(pagina.decode("utf-8", "ignore"))


def _og_image(texto: str) -> str | None:
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
    except FotoNaoConfere:
        return None, "ML: foto não confere com o produto (salve uma reserva)"
    except Exception as e:  # loja bloqueou, caiu etc.
        return None, f"falhou ({type(e).__name__})"
    return None, ("sem foto (salve uma reserva)" if produto.get("loja") == "Shopee" and not produto.get("foto_url")
                  else "falhou (loja sem foto)")
