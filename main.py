import os
from fastapi import FastAPI, HTTPException, Request, Form
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
    performance = Column(String)
    carbon_footprint = Column(String)
    lifecycle = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Battery DPP API")

@app.get("/")
def read_root():
    return {"message": "Sistēma darbojas! Dodies uz /battery/add-form, lai reģistrētu bateriju."}

# 1. FORMA DARBINIEKAM (Kur ievadīt datus)
@app.get("/battery/add-form", response_class=HTMLResponse)
def add_battery_form():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Reģistrēt jaunu bateriju - DPP</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
            body { font-family: 'Inter', sans-serif; background-color: #fbfaf7; margin: 0; padding: 40px; display: flex; justify-content: center; }
            .form-card { background: white; width: 100%; max-width: 600px; border-radius: 10px; box-shadow: 0px 4px 12px rgba(0,0,0,0.03); padding: 30px; box-sizing: border-box; }
            h2 { color: #1a1a1a; margin-top: 0; text-align: center; }
            .subtitle { font-size: 11px; color: #555; text-transform: uppercase; text-align: center; margin-bottom: 25px; letter-spacing: 1px; }
            label { display: block; font-weight: 600; font-size: 13px; color: #333; margin-bottom: 5px; margin-top: 15px; }
            input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
            button { width: 100%; margin-top: 25px; background: #007BFF; color: white; border: none; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 15px; cursor: pointer; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="form-card">
            <h2>Jaunas Baterijas Reģistrācija</h2>
            <div class="subtitle">LifecyclePassport · Datu Ievade</div>
            
            <form action="/battery/create" method="POST">
                <label>1. Baterijas ID / Sērijas numurs:</label>
                <input type="text" name="battery_id" placeholder="piem., BAT-2026-X984" required>

                <label>2. Identifikācija (Modelis un Ražotājs):</label>
                <input type="text" name="model" placeholder="piem., Li-Ion Industrial Pack 48V | Ražots Latvijā" required>

                <label>3. Materiālu Sastāvs:</label>
                <input type="text" name="chemistry" placeholder="piem., Litija dzelzs fosfāts (LiFePO4), 15% pārstrādāti" required>

                <label>4. Veiktspēja un Ilgtspēja:</label>
                <input type="text" name="performance" placeholder="piem., 100 Ah / 4.8 kWh, 3500 cikli, EN 62619" required>

                <label>5. Oglekļa Pēdas Nospiedums:</label>
                <input type="text" name="carbon_footprint" placeholder="piem., B klase (verificēts)" required>

                <label>6. Dzīves Cikls un Utilizācija:</label>
                <input type="text" name="lifecycle" placeholder="piem., Droša izjaukšana pēc rokasgrāmatas 4B" required>

                <button type="submit">Ģenerēt DPP un QR Kodu</button>
            </form>
        </div>
    </body>
    </html>
    """

# 2. DATU SAGLABĀŠANA UN PĀRSŪTĪŠANA UZ PASI
@app.post("/battery/create", response_class=HTMLResponse)
def create_battery_from_form(
    battery_id: str = Form(...),
    model: str = Form(...),
    chemistry: str = Form(...),
    performance: str = Form(...),
    carbon_footprint: str = Form(...),
    lifecycle: str = Form(...)
):
    db = SessionLocal()
    try:
        # Pārbaudām vai eksistē, ja jā - atjaunojam, ja nē - izveidojam jaunu
        battery = db.query(BatteryModel).filter(BatteryModel.battery_id == battery_id).first()
        if battery:
            battery.model = model
            battery.chemistry = chemistry
            battery.performance = performance
            battery.carbon_footprint = carbon_footprint
            battery.lifecycle = lifecycle
        else:
            battery = BatteryModel(
                battery_id=battery_id,
                model=model,
                manufacturer="SIA TehnoParts",
                chemistry=chemistry,
                performance=performance,
                carbon_footprint=carbon_footprint,
                lifecycle=lifecycle
            )
            db.add(battery)
        db.commit()
    finally:
        db.close()
    
    # Pēc saglabāšanas uzreiz novirzām darbinieku uz gatavo skenēšanas lapu
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/battery/{battery_id}/scan", status_code=303)

# 3. VIZUĀLĀ PASES LAPA (Ar kuru saskaras klients, noskenējot kodu)
@app.get("/battery/{battery_id}/scan", response_class=HTMLResponse)
def scan_page(battery_id: str, request: Request):
    db = SessionLocal()
    try:
        battery = db.query(BatteryModel).filter(BatteryModel.battery_id == battery_id).first()
        if not battery:
            raise HTTPException(status_code=404, detail="Baterija nav atrasta. Lūdzu reģistrē to /battery/add-form")
        
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

                .back-btn {{ display: inline-block; margin-bottom: 20px; color: #007BFF; text-decoration: none; font-size: 13px; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="main-container">
                <div class="card">
                    <a class="back-btn" href="/battery/add-form">← Reģistrēt jaunu bateriju</a>
                    <h1>DIGITĀLĀ PRODUKTA PASE</h1>
                    <div class="subtitle">LIFECYCLEPASSPORT · BATERIJU SPECifikĀCIJA</div>

                    <div class="section-title">PRODUKTA SPECIFIKĀCIJA UN DATI</div>
                    <div class="data-box">
                        <div class="data-item"><span class="item-number">1.</span><strong>Identifikācija:</strong><span>{battery.model} (ID: {battery.battery_id})</span></div>
                        <div class="data-item"><span class="item-number">2.</span><strong>Materiālu Sastāvs:</strong><span>{battery.chemistry}</span></div>
                        <div class="data-item"><span class="item-number">3.</span><strong>Veiktspēja un Ilgtspēja:</strong><span>{battery.performance}</span></div>
                        <div class="data-item"><span class="item-number">4.</span><strong>Oglekļa Pēdas Nospiedums:</strong><span>{battery.carbon_footprint}</span></div>
                        <div class="data-item"><span class="item-number">5.</span><strong>Dzīves Cikls un Utilizācija:</strong><span>{battery.lifecycle}</span></div>
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
