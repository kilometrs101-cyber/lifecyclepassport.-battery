import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
import qrcode
import io
from sqlalchemy import create_engine, Column, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Drošs lokālās datubāzes dzinējs
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
    carbon_footprint = Column(Float)
    manufacturing_date = Column(String, default="2026-01-01")
    status = Column(String, default="Active")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Battery DPP API")

@app.get("/")
def read_root():
    return {"message": "Bateriju sistēma darbojas bez kļūdām!"}

@app.post("/battery/add")
def add_battery(battery_id: str, model: str, manufacturer: str, chemistry: str, carbon_footprint: float, manufacturing_date: str = "2026-01-01", status: str = "Active"):
    db = SessionLocal()
    try:
        existing = db.query(BatteryModel).filter(BatteryModel.battery_id == battery_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Battery already exists")
        
        new_battery = BatteryModel(
            battery_id=battery_id,
            model=model,
            manufacturer=manufacturer,
            chemistry=chemistry,
            carbon_footprint=carbon_footprint,
            manufacturing_date=manufacturing_date,
            status=status
        )
        db.add(new_battery)
        db.commit()
        return {"status": "success", "battery_id": battery_id}
    finally:
        db.close()

@app.get("/battery/{battery_id}")
def get_battery(battery_id: str):
    db = SessionLocal()
    try:
        battery = db.query(BatteryModel).filter(BatteryModel.battery_id == battery_id).first()
        if not battery:
            raise HTTPException(status_code=404, detail="Battery not found")
        return {
            "battery_id": battery.battery_id,
            "model": battery.model,
            "manufacturer": battery.manufacturer,
            "chemistry": battery.chemistry,
            "carbon_footprint": battery.carbon_footprint,
            "manufacturing_date": battery.manufacturing_date,
            "status": battery.status
        }
    finally:
        db.close()

@app.get("/battery/{battery_id}/qrcode")
def generate_qr_code(battery_id: str):
    db = SessionLocal()
    try:
        battery = db.query(BatteryModel).filter(BatteryModel.battery_id == battery_id).first()
        if not battery:
            raise HTTPException(status_code=404, detail="Battery not found")
        
        data_url = f"https://battery-dpp-api-production-a9d8.up.railway.app/battery/{battery_id}"
        
        img = qrcode.make(data_url)
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return Response(content=img_io.getvalue(), media_type="image/png")
    finally:
        db.close()

@app.get("/battery/{battery_id}/scan", response_class=HTMLResponse)
def scan_page(battery_id: str):
    db = SessionLocal()
    try:
        battery = db.query(BatteryModel).filter(BatteryModel.battery_id == battery_id).first()
        if not battery:
            raise HTTPException(status_code=404, detail="Battery not found")
        
        qr_img_endpoint = f"/battery/{battery_id}/qrcode"
        json_endpoint = f"/battery/{battery_id}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Baterijas QR Kods - {battery_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f9; padding: 50px; }}
                .card {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); display: inline-block; }}
                h2 {{ color: #333; }}
                p {{ color: #666; }}
                img {{ margin: 20px 0; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }}
                .btn {{ display: inline-block; margin-top: 15px; padding: 10px 20px; background: #007BFF; color: white; text-decoration: none; border-radius: 5px; }}
                .btn:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Baterijas Digitālā Pase (DPP)</h2>
                <p>Baterijas ID: <strong>{battery_id}</strong></p>
                <p>Modelis: <strong>{battery.model}</strong> ({battery.manufacturer})</p>
                <p>Noskenē šo kodu ar telefonu, lai atvērtu datus!</p>
                
                <img src="{qr_img_endpoint}" alt="QR Kods" width="250" height="250">
                
                <br>
                <a class="btn" href="{json_endpoint}" target="_blank">Skatīt JSON datus</a>
            </div>
        </body>
        </html>
        """
        return html_content
    finally:
        db.close()
