# app.py
from fastapi import FastAPI
import feedparser
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, desc
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

# =========================================================
# INICIALIZAÇÃO DO FASTAPI
# =========================================================
app = FastAPI(title="News Scraper API")

# ✅ CORS deve vir logo após a criação do app
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
    published = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()

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

    keywords = ["saúde", "hospital", "doença", "médico", "tratamento", "covid", "vacina", "IRB PRIME CARE","IRB","IRB SÂO PAULO","irb prime care"]
    count_new = 0

    for url in feeds:
        print(f"🔍 Coletando do feed: {url}")
        try:
            feed = feedparser.parse(url)
            print(f"📥 {len(feed.entries)} notícias encontradas.")
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                summary = entry.get("summary", "")
                clean_summary = BeautifulSoup(summary, "html.parser").get_text()
                text_to_search = f"{title} {clean_summary}".lower()
                if not any(word in text_to_search for word in keywords):
                    continue
                exists = session.query(News).filter_by(link=link).first()
                if exists:
                    continue
                news_item = News(
                    title=title,
                    link=link,
                    summary=clean_summary,
                    published=datetime.utcnow()
                )
                session.add(news_item)
                count_new += 1
        except Exception as e:
            print(f"⚠️ Erro ao acessar {url}: {e}")
    session.commit()
    return count_new

# =========================================================
# ROTAS
# =========================================================
@app.get("/atualizar")
def atualizar_noticias():
    novas = fetch_news()
    if novas > 0:
        return {"message": f"✅ {novas} novas notícias de saúde adicionadas."}
    else:
        return {"message": "🟢 As notícias já estão atualizadas."}

@app.get("/noticias")
def listar_noticias():
    noticias = session.query(News).order_by(desc(News.published)).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "link": n.link,
            "summary": n.summary,
            "published": n.published.strftime("%Y-%m-%d")
        }
        for n in noticias
    ]
