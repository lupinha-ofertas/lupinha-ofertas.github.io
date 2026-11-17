"""Acha a foto de cada produto.

Ordem: 1) pasta fotos-reserva (o que a Ari salvou manualmente, sempre ganha);
       2) Shopee: API de afiliados (secrets SHOPEE_APP_ID e SHOPEE_SECRET);
       3) foto buscada pelo link (og:image da página da loja).
"""
import difflib
import hashlib
import json
import os
import re
import time
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


SHOPEE_API = "https://open-api.affiliate.shopee.com.br/graphql"


def _shopee_api(consulta: str) -> dict:
    app_id, segredo = os.environ.get("SHOPEE_APP_ID"), os.environ.get("SHOPEE_SECRET")
    if not app_id or not segredo:
        raise RuntimeError("sem SHOPEE_APP_ID/SHOPEE_SECRET")
    corpo = json.dumps({"query": consulta}, separators=(",", ":"))
    ts = str(int(time.time()))
    assinatura = hashlib.sha256((app_id + ts + corpo + segredo).encode()).hexdigest()
    req = urllib.request.Request(SHOPEE_API, data=corpo.encode(), method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id}, Timestamp={ts}, Signature={assinatura}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        dados = json.loads(r.read())
    if dados.get("errors"):
        raise RuntimeError(f"API Shopee: {dados['errors'][0].get('message', '')[:80]}")
    return dados["data"]["productOfferV2"]["nodes"]


def ids_shopee(link: str) -> tuple[str, str] | None:
    """Abre o link curto e acha (shopId, itemId) no endereço final ou na página."""
    pagina, final = _baixar(link)
    texto = final + " " + urllib.request.unquote(pagina.decode("utf-8", "ignore")[:200000])
    for padrao in (r"-i\.(\d+)\.(\d+)", r"/product/(\d+)/(\d+)",
                   r"shopid=(\d+)[^\d]+itemid=(\d+)", r'"shopid":(\d+),"itemid":(\d+)'):
        m = re.search(padrao, texto, re.I)
        if m:
            return m.group(1), m.group(2)
    return None


def url_foto_shopee(produto: dict) -> str | None:
    campos = "nodes { imageUrl productName itemId shopId }"
    ids = ids_shopee(produto["link"])
    if ids:
        nos = _shopee_api(f"{{ productOfferV2(shopId: {ids[0]}, itemId: {ids[1]}, limit: 1) {{ {campos} }} }}")
        if nos and nos[0].get("imageUrl"):
            return nos[0]["imageUrl"]
    # reserva: busca pelo nome e só aceita se o nome bater bem
    nome = produto["nome"][:60].replace('"', "")
    nos = _shopee_api(f'{{ productOfferV2(keyword: "{nome}", limit: 5) {{ {campos} }} }}')
    for no in nos:
        if difflib.SequenceMatcher(None, no["productName"].lower(), produto["nome"].lower()).ratio() > 0.8:
            return no["imageUrl"]
    return None


def url_da_foto_produto(produto: dict) -> str | None:
    """URL da foto do produto: Shopee pela API (se tiver credenciais), senão pela página."""
    if produto.get("loja") == "Shopee" and os.environ.get("SHOPEE_APP_ID"):
        url = url_foto_shopee(produto)
        if url:
            return url
    return url_da_foto(produto["link"])


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
    except Exception as e:  # loja bloqueou, caiu etc.
        return None, f"falhou ({type(e).__name__})"
    return None, "falhou (sem foto na página)"
