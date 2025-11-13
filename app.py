from fastapi import FastAPI
import feedparser
from bs4 import BeautifulSoup
import requests
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, desc
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="News Scraper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# =========================================================
engine = create_engine("sqlite:///news.db", echo=False)
Base = declarative_base()

class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), unique=True)
    link = Column(String(500), unique=True)
    summary = Column(Text)
    image = Column(String(500))
    published = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()

# =========================================================
# FUNÇÃO AUXILIAR PARA PEGAR A PRIMEIRA IMAGEM
# =========================================================
def get_first_image(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        img_tag = soup.find("img")
        if img_tag and img_tag.get("src"):
            src = img_tag["src"]
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                domain = url.split("/")[2]
                src = f"https://{domain}{src}"
            return src
    except Exception:
        pass
    return None

# =========================================================
# FUNÇÃO PARA BUSCAR E SALVAR NOTÍCIAS
# =========================================================
def fetch_news():
    feeds = [
        "https://admin.cnnbrasil.com.br/feed/",
        "https://g1.globo.com/rss/g1/saude/",
        "https://feeds.bbci.co.uk/portuguese/topics/c404v09lmw9t/rss.xml",
        "https://rss.dw.com/rdf/rss-pt-saude",
    ]

    keywords = [
        "saúde", "hospital", "doença", "médico", "tratamento", "covid", "vacina",
        "IRB PRIME CARE", "IRB", "IRB SÂO PAULO", "irb prime care"
    ]
    count_new = 0

    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                summary = entry.get("summary", "")
                clean_summary = BeautifulSoup(summary, "html.parser").get_text()

                text_to_search = f"{title} {clean_summary}".lower()
                if not any(word in text_to_search for word in keywords):
                    continue

                exists = session.query(News).filter(
                    (News.link == link) | (News.title == title)
                ).first()
                if exists:
                    continue

                image_url = get_first_image(link)
                try:
                    news_item = News(
                        title=title,
                        link=link,
                        summary=clean_summary,
                        image=image_url,
                        published=datetime.utcnow()
                    )
                    session.add(news_item)
                    session.commit()
                    count_new += 1
                except Exception:
                    session.rollback()
        except Exception:
            continue

    return count_new

# =========================================================
# ROTAS
# =========================================================
@app.get("/atualizar")
def atualizar_noticias():
    novas = fetch_news()
    return {
        "message": f"✅ {novas} novas notícias de saúde adicionadas." if novas > 0
        else "🟢 As notícias já estão atualizadas."
    }

@app.get("/noticias")
def listar_noticias():
    # 🔥 Retorna apenas os 30 mais recentes para não travar o front
    noticias = session.query(News).order_by(desc(News.published)).limit(30).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "link": n.link,
            "summary": n.summary,
            "image": n.image,
            "published": n.published.strftime("%Y-%m-%d")
        }
        for n in noticias
    ]

@app.get("/noticias/{id}")
def obter_noticia(id: int):
    noticia = session.query(News).filter_by(id=id).first()
    if not noticia:
        return {"error": "Notícia não encontrada"}

    return {
        "id": noticia.id,
        "title": noticia.title,
        "link": noticia.link,
        "summary": noticia.summary,
        "published": noticia.published.strftime("%Y-%m-%d"),
        "image": getattr(noticia, "image", None)
    }
