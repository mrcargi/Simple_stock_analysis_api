from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import yfinance as yf
import os
from utils import analyze_ticker 






app = FastAPI()
templates = Jinja2Templates(directory = "templates")
API_KEY  = os.getenv("API_KEY")

@app.get("/analizar/{ticker}",response_class=HTMLResponse)
async def analizar(request :Request,ticker :str):
    try:   
        data = yf.download(ticker, period="1mo")
        
        if data.empty:
            raise HTTPException(status_code=404 , detail="Ticker no encontrado o no encontrado ")
        
        result = analyze_ticker(data , ticker)
        
        return templates.TemplateResponse("template.html", {
            "request": request,
            "ticker": ticker,
            "trend": result["Tendencia"],
            "support": result["Soporte"],
            "resistance": result["Resistencia"],
            "chart_img": result["Grafica"],
            "news_articles": result["news_articles"]  # Aquí deben pasar las noticias
    

            
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))