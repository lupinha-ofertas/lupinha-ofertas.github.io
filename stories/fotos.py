"""Acha a foto de cada produto.

Ordem: 1) pasta fotos-reserva (o que a Ari salvou manualmente, sempre ganha);
       2) foto buscada pelo link (og:image da página da loja).
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


def url_da_foto(link: str) -> str | None:
    pagina, _ = _baixar(link)
    texto = pagina.decode("utf-8", "ignore")
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
    url = url_da_foto(produto["link"])
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
    except Exception as e:  # loja bloqueou, caiu etc.
        return None, f"falhou ({type(e).__name__})"
    return None, "falhou (sem foto na página)"
