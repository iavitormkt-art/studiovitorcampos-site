"""Gera o blog do site a partir dos artigos em posts/.

Cada artigo é um arquivo posts/AAAA-MM-DD-slug.md com um cabeçalho simples:

    ---
    titulo: Título do artigo
    descricao: Resumo de uma ou duas frases (aparece no Google)
    ---
    Texto em Markdown: ## subtítulo, **negrito**, *itálico*, [link](url),
    listas com "- " ou "1. " e citações com "> ".

Artigos com data no futuro ficam guardados e só entram no ar no dia
(o robô .github/workflows/blog.yml roda todo dia às 9h de Brasília).

Uso: python blog.py
Gera blog/index.html, blog/<slug>/index.html, sitemap.xml, feed.xml e robots.txt.
"""

import datetime as dt
import html
import json
import re
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SITE = "https://studiovitorcampos.com.br"
WHATS = "https://wa.me/5561992163078?text=Ol%C3%A1!%20Vim%20pelo%20blog%20e%20quero%20saber%20mais%20sobre%20o%20Marketing%20Essencial."
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def hoje():
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).date()


def data_extenso(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


# ---------------------------------------------------------------- Markdown simples

def inline(texto):
    t = html.escape(texto, quote=False)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{html.escape(m[2])}">{m[1]}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t


def markdown(texto):
    saida, bloco, tipo = [], [], None

    def fechar():
        nonlocal bloco, tipo
        if not bloco:
            return
        if tipo == "p":
            saida.append(f"<p>{inline(' '.join(bloco))}</p>")
        elif tipo in ("ul", "ol"):
            itens = "".join(f"<li>{inline(i)}</li>" for i in bloco)
            saida.append(f"<{tipo}>{itens}</{tipo}>")
        elif tipo == "quote":
            saida.append(f"<blockquote><p>{inline(' '.join(bloco))}</p></blockquote>")
        bloco, tipo = [], None

    for linha in texto.splitlines():
        s = linha.strip()
        if not s:
            fechar()
            continue
        m = re.match(r"(#{2,3})\s+(.*)", s)
        if m:
            fechar()
            n = len(m[1])
            saida.append(f"<h{n}>{inline(m[2])}</h{n}>")
            continue
        for padrao, novo in ((r"[-*]\s+(.*)", "ul"), (r"\d+\.\s+(.*)", "ol"), (r">\s?(.*)", "quote")):
            m = re.match(padrao, s)
            if m:
                if tipo != novo:
                    fechar()
                    tipo = novo
                bloco.append(m[1])
                break
        else:
            if tipo != "p":
                fechar()
                tipo = "p"
            bloco.append(s)
    fechar()
    return "\n".join(saida)


# ---------------------------------------------------------------- artigos

def ler_post(arquivo):
    bruto = arquivo.read_text(encoding="utf-8")
    m = re.match(r"---\s*\n(.*?)\n---\s*\n(.*)", bruto, re.S)
    if not m:
        raise SystemExit(f"{arquivo.name}: falta o cabeçalho entre --- e ---")
    meta = dict(l.split(":", 1) for l in m[1].splitlines() if ":" in l)
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    nome = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", arquivo.stem)
    if not nome:
        raise SystemExit(f"{arquivo.name}: o nome precisa ser AAAA-MM-DD-slug.md")
    corpo = m[2]
    palavras = len(re.findall(r"\w+", corpo))
    return {
        "titulo": meta["titulo"],
        "descricao": meta["descricao"],
        "data": dt.date.fromisoformat(nome[1]),
        "slug": nome[2],
        "html": markdown(corpo),
        "minutos": max(1, round(palavras / 200)),
    }


# ---------------------------------------------------------------- páginas

TOPO = """<header class="topo">
  <div class="container">
    <a class="marca" href="/">
      <svg class="logo" viewBox="0 0 100 100" style="color:var(--ciano)"><g fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><circle cx="50" cy="51" r="44"/><path d="M7 29 L30 93 L74 8"/><path d="M90 26 A31 31 0 1 0 82 85"/></g></svg>
      <span><small>STUDIO</small><strong>VITOR CAMPOS</strong></span>
    </a>
    <nav class="menu">
      <a href="/#inclui">O que inclui</a>
      <a href="/#planos">Planos</a>
      <a href="/blog/">Blog</a>
      <a class="botao botao-ciano" href="/#diagnostico">Diagnóstico grátis</a>
    </nav>
  </div>
</header>"""

RODAPE = f"""<footer>
  <div class="container">
    <span><strong>Studio Vitor Campos</strong> · O básico bem feito funciona.</span>
    <nav>
      <a href="/">Site</a>
      <a href="/blog/">Blog</a>
      <a href="https://www.instagram.com/vitorcamposmkt/" target="_blank" rel="noopener">Instagram</a>
      <a href="{WHATS}" target="_blank" rel="noopener">WhatsApp</a>
    </nav>
  </div>
</footer>"""

CHAMADA = """<aside class="chamada">
  <h2>Quer saber como está o seu perfil?</h2>
  <p>Peça um diagnóstico gratuito. Eu analiso o seu Instagram, o seu Facebook e o seu site e mostro onde você está perdendo clientes.</p>
  <a class="botao botao-coral" href="/#diagnostico">Quero o diagnóstico gratuito</a>
</aside>"""


def pagina(titulo, descricao, url, corpo, extra_head=""):
    t, d = html.escape(titulo), html.escape(descricao)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta name="theme-color" content="#003346">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="Blog do Studio Vitor Campos" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/blog.css">
{extra_head}</head>
<body>
{TOPO}
{corpo}
{RODAPE}
</body>
</html>
"""


def pagina_post(p):
    url = f"{SITE}/blog/{p['slug']}/"
    ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": p["titulo"], "description": p["descricao"],
        "datePublished": p["data"].isoformat(), "url": url, "inLanguage": "pt-BR",
        "author": {"@type": "Person", "name": "Vitor Campos"},
        "publisher": {"@type": "Organization", "name": "Studio Vitor Campos", "url": SITE},
    }
    corpo = f"""<main class="artigo">
  <div class="container estreito">
    <a class="voltar" href="/blog/">← Todos os artigos</a>
    <p class="meta">{data_extenso(p['data'])} · {p['minutos']} min de leitura</p>
    <h1>{html.escape(p['titulo'])}</h1>
    <p class="linha-fina">{html.escape(p['descricao'])}</p>
    <div class="texto">
{p['html']}
    </div>
    <p class="assinatura">Vitor Campos · filmmaker, formado em marketing e gestor do Marketing Essencial</p>
    {CHAMADA}
  </div>
</main>"""
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
    return pagina(f"{p['titulo']} · Blog Studio Vitor Campos", p["descricao"], url, corpo, extra)


def pagina_lista(posts):
    cartoes = "\n".join(f"""    <a class="cartao-post" href="/blog/{p['slug']}/">
      <p class="meta">{data_extenso(p['data'])} · {p['minutos']} min</p>
      <h2>{html.escape(p['titulo'])}</h2>
      <p>{html.escape(p['descricao'])}</p>
      <span class="ler">Ler artigo →</span>
    </a>""" for p in posts) or '    <p class="vazio">Os primeiros artigos chegam em breve.</p>'
    corpo = f"""<section class="capa-blog">
  <div class="container">
    <span class="selo">Blog</span>
    <h1>Marketing para quem tem um negócio de verdade</h1>
    <p>Um artigo por semana sobre Instagram, Facebook e atendimento para o comércio local. Sem fórmula mágica: o básico bem feito funciona.</p>
  </div>
</section>
<main class="lista">
  <div class="container">
{cartoes}
  </div>
</main>"""
    return pagina("Blog · Studio Vitor Campos",
                  "Dicas práticas de Instagram, Facebook e atendimento para pequenos e médios negócios. Um artigo novo por semana.",
                  f"{SITE}/blog/", corpo)


def feed(posts):
    itens = "".join(f"""
  <item>
    <title>{html.escape(p['titulo'])}</title>
    <link>{SITE}/blog/{p['slug']}/</link>
    <guid>{SITE}/blog/{p['slug']}/</guid>
    <pubDate>{dt.datetime.combine(p['data'], dt.time(9)).strftime('%a, %d %b %Y %H:%M:%S')} -0300</pubDate>
    <description>{html.escape(p['descricao'])}</description>
  </item>""" for p in posts)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Blog do Studio Vitor Campos</title>
  <link>{SITE}/blog/</link>
  <description>Marketing para quem tem um negócio de verdade.</description>
  <language>pt-BR</language>{itens}
</channel>
</rss>
"""


def sitemap(posts):
    urls = [(f"{SITE}/", None), (f"{SITE}/blog/", posts[0]["data"] if posts else None)]
    urls += [(f"{SITE}/blog/{p['slug']}/", p["data"]) for p in posts]
    linhas = "".join(
        f"\n  <url><loc>{u}</loc>{f'<lastmod>{d.isoformat()}</lastmod>' if d else ''}</url>" for u, d in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{linhas}\n</urlset>\n'


def main():
    todos = [ler_post(a) for a in sorted((RAIZ / "posts").glob("*.md"))]
    no_ar = sorted((p for p in todos if p["data"] <= hoje()), key=lambda p: p["data"], reverse=True)

    pasta = RAIZ / "blog"
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir()
    (pasta / "index.html").write_text(pagina_lista(no_ar), encoding="utf-8")
    for p in no_ar:
        (pasta / p["slug"]).mkdir()
        (pasta / p["slug"] / "index.html").write_text(pagina_post(p), encoding="utf-8")

    (RAIZ / "feed.xml").write_text(feed(no_ar), encoding="utf-8")
    (RAIZ / "sitemap.xml").write_text(sitemap(no_ar), encoding="utf-8")
    (RAIZ / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    agendados = [p for p in todos if p["data"] > hoje()]
    print(f"{len(no_ar)} no ar" + (f", {len(agendados)} agendado(s): " + ", ".join(
        f"{p['slug']} ({p['data']:%d/%m})" for p in agendados) if agendados else ""))


if __name__ == "__main__":
    main()
