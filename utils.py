import os
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import requests
import re
from newsapi_python import NewsApiClient
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

def detect_trend(prices):
    if prices.empty:
        return "Datos insuficientes para detectar tendencia"
    if prices.iloc[-1] > prices.iloc[0]:
        return "Tendencia Alcista"
    elif prices.iloc[-1] < prices.iloc[0]:
        return "Tendencia Bajista"
    else:
        return "Tendencia Lateral"

def get_company_name_from_ticker(ticker):
    try:
        stock_info = yf.Ticker(ticker)
        full_name = stock_info.info.get('longName', ticker)
        full_name_cleaned = re.sub(r'[^\w\s]', '', full_name)
        return ' '.join(full_name_cleaned.split()[:2])
    except Exception as e:
        print(f"Error obteniendo el nombre de la empresa: {e}")
        return ticker

def fetch_news_by_country(company_name, country_code):
    api_key = os.getenv("GNEWS_API_KEY")  # Obtener la clave API de GNews desde el entorno
    url = f"https://gnews.io/api/v4/search?q={company_name}&token={api_key}&lang=es&sortby=relevance&max=10&country={country_code}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        news_data = response.json()
        return news_data.get("articles", [])
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud de noticias para {country_code}: {e}")
        return []

def get_news(ticker):
    company_name = get_company_name_from_ticker(ticker)

    # Inicializar cliente de NewsAPI
    newsapi_key = os.getenv("NEWSAPI_KEY")  # Obtener la clave API de NewsAPI desde el entorno
    newsapi = NewsApiClient(api_key=newsapi_key)

    # Buscar en múltiples fuentes y términos
    news_articles = []

    # Búsqueda en GNews
    mexico_news = fetch_news_by_country(company_name, "mx")
    us_news = fetch_news_by_country(company_name, "us")
    news_articles.extend(mexico_news + us_news)

    # Búsqueda en NewsAPI
    for query in [company_name, ticker, f"{company_name} stock"]:
        try:
            all_articles = newsapi.get_everything(q=query, language='es', sort_by='relevancy')
            news_articles.extend(all_articles['articles'])
        except Exception as e:
            print(f"Error al buscar en NewsAPI para {query}: {e}")

    # Si no se encuentran suficientes noticias, intentar con una versión más corta del nombre
    if len(news_articles) < 5:
        shorter_name = ' '.join(company_name.split()[:1])
        news_articles += fetch_news_by_country(shorter_name, "us")

    return news_articles[:10]

def find_support_resistance(prices, window=5):
    support = prices.rolling(window=window).min()
    resistance = prices.rolling(window=window).max()
    return support, resistance

def generate_chart(data, support, resistance, ticker):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data['Close'],
        hovertext=[f"Fecha: {date}<br>Open: {open}<br>High: {high}<br>Low: {low}<br>Close: {close}<br>Soporte: {support_value}<br>Resistencia: {resistance_value}<br>"
                    for date, open, high, low, close, support_value, resistance_value in zip(
                        data.index, data["Open"], data["High"], data["Low"], data['Close'], support, resistance)],
        hoverinfo='text',
        increasing_line_color='yellow',
        decreasing_line_color='yellowgreen',
        name=f"{ticker} Gráfica de Velas Japonesas"
    ))

    fig.add_trace(go.Scatter(x=data.index, y=support, mode='lines', name='Soporte', line=dict(color='#EE66A6', dash='dash')))
    fig.add_trace(go.Scatter(x=data.index, y=resistance, mode='lines', name='Resistencia', line=dict(color='deepskyblue', dash='dash')))

    fig.update_layout(
        title=f"Indicadores de Tendencia, Soportes y Resistencias de {ticker}",
        xaxis_title="Fecha",
        yaxis_title="Precio",
        template="plotly",
        xaxis_rangeslider_visible=True,
        dragmode='zoom',
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def analyze_ticker(data, ticker):
    if data.empty:
        return {"error": "No hay datos disponibles para el ticker."}
    
    trend = detect_trend(data['Close'])
    support, resistance = find_support_resistance(data['Close'])
    
    if support.empty or resistance.empty:
        return {"error": "No se pudo calcular soporte y resistencia."}

    chart_img = generate_chart(data, support, resistance, ticker)
    news_articles = get_news(ticker)

    return {
        "Tendencia": trend,
        "Soporte": support.iloc[-1] if not support.empty else None,
        "Resistencia": resistance.iloc[-1] if not resistance.empty else None,
        "Grafica": chart_img,
        "news_articles": news_articles
    }
