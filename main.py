import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
import qrcode
import io
from sqlalchemy import create_engine, Column, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./batteries.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class BatteryModel(Base):
    __tablename__ = "batteries"
    
    battery_id = Column(String, primary_key=True, index=True)
    model = Column(String)
    manufacturer = Column(String)
    chemistry = Column(String)
    carbon_footprint = Column(String)
    manufacturing_date = Column(String)
    status = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Battery DPP API")

@app.get("/")
def read_root():
    return {"message": "Bateriju sistēma darbojas. Atver /battery/{id}/scan"}

@app.get("/battery/{battery_id}/scan", response_class=HTMLResponse)
def scan_page(battery_id: str, request: Request):
    db = SessionLocal()
    try:
        battery = db.query(BatteryModel).filter(BatteryModel.battery_id == battery_id).first()
        if not battery:
            battery = BatteryModel(
                battery_id=battery_id,
                model="Li-Ion Industrial Pack 48V | ID: BAT-2026-X984",
                manufacturer="SIA TehnoParts",
                chemistry="Litija dzelzs fosfāts (LiFePO4), 15% otrreizēji pārstrādāti materiāli",
                carbon_footprint="B klase (apzināts visā dzīves ciklā, verificēts)",
                manufacturing_date="Droša izjaukšana pēc rokasgrāmatas 4B, 100% otrreizēji pārstrādājams",
                status="100 Ah / 4.8 kWh, 3500 uzlādes cikli, atbilst EN 62619"
            )
            db.add(battery)
            db.commit()
            db.refresh(battery)
        
        base_url = str(request.base_url).rstrip("/")
        qr_img_endpoint = f"/battery/{battery_id}/qrcode"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>DIGITĀLĀ PRODUKTA PASE - {battery_id}</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
                body {{ font-family: 'Inter', sans-serif; text-align: center; background-color: #fbfaf7; margin: 0; padding: 20px; }}
                .main-container {{ display: flex; flex-direction: column; align-items: center; min-height: 100vh; }}
                
                .card {{ 
                    background: white; 
                    width: 100%; 
                    max-width: 650px; 
                    border-radius: 10px; 
                    box-shadow: 0px 4px 12px rgba(0,0,0,0.03); 
                    padding: 40px 20px; 
                    margin-top: 40px;
                    box-sizing: border-box;
                }}

                h1 {{ font-size: 22px; font-weight: 700; color: #1a1a1a; letter-spacing: 1px; margin: 0 0 5px 0; }}
                .subtitle {{ font-size: 11px; color: #555; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 30px; border-bottom: 1px solid #333; display: inline-block; padding-bottom: 5px; }}

                .section-title {{ font-size: 14px; font-weight: 700; color: #1a1a1a; text-transform: uppercase; text-align: left; margin-bottom: 15px; }}
                .data-box {{ background: #f9f9f8; border-radius: 6px; padding: 25px; margin-bottom: 30px; border: 1px solid #eee; }}
                .data-item {{ text-align: left; font-size: 13.5px; color: #333; margin-bottom: 12px; line-height: 1.5; display: flex; }}
                .data-item strong {{ font-weight: 600; margin-right: 5px; }}
                .item-number {{ font-weight: 700; color: #333; margin-right: 8px; }}

                img {{ margin: 20px 0; border: 1px solid #ddd; padding: 5px; border-radius: 4px; background: white; }}
                .scan-text {{ font-size: 13px; color: #777; margin-bottom: 5px; }}

                .logo-area {{ margin-top: 30px; opacity: 0.6; }}
                .logo-text {{ font-size: 14px; font-weight: 600; color: #4a4a4a; margin-bottom: 3px; }}
                .logo-subtext {{ font-size: 9px; color: #7a7a7a; text-transform: uppercase; }}

                @media (max-width: 600px) {{
                    .card {{ padding: 20px; }}
                    h1 {{ font-size: 18px; }}
                    .data-item {{ font-size: 12px; }}
                    .data-box {{ padding: 15px; }}
                }}
            </style>
        </head>
        <body>
            <div class="main-container">
                <div class="card">
                    <h1>DIGITĀLĀ PRODUKTA PASE</h1>
                    <div class="subtitle">LIFECYCLEPASSPORT · BATERIJU SPECIFIKĀCIJA</div>

                    <div class="section-title">PRODUKTA SPECIFIKĀCIJA UN DATI</div>
                    <div class="data-box">
                        <div class="data-item"><span class="item-number">1.</span><strong>Identifikācija:</strong><span>{battery.model}</span></div>
                        <div class="data-item"><span class="item-number">2.</span><strong>Materiālu Sastāvs:</strong><span>{battery.chemistry}</span></div>
                        <div class="data-item"><span class="item-number">3.</span><strong>Veiktspēja un Ilgtspēja:</strong><span>{battery.status}</span></div>
                        <div class="data-item"><span class="item-number">4.</span><strong>Oglekļa Pēdas Nospiedums:</strong><span>{battery.carbon_footprint}</span></div>
                        <div class="data-item"><span class="item-number">5.</span><strong>Dzīves Cikls un Utilizācija:</strong><span>{battery.manufacturing_date}</span></div>
                    </div>

                    <p class="scan-text">Noskenē šo kodu, lai piekļūtu pasei:</p>
                    <img src="{qr_img_endpoint}" alt="QR Kods" width="180" height="180">
                    
                    <div class="logo-area">
                        <div class="logo-text">LifecyclePassport</div>
                        <div class="logo-subtext">DYNAMIC LIFECYCLE PATH</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content
    finally:
        db.close()

@app.get("/battery/{battery_id}/qrcode")
def generate_qr_code(battery_id: str, request: Request):
    base_url = str(request.base_url).rstrip("/")
    data_url = f"{base_url}/battery/{battery_id}/scan"
    
    img = qrcode.make(data_url)
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return Response(content=img_io.getvalue(), media_type="image/png")
