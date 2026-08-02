import os
from fastapi import FastAPI, HTTPException
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
    carbon_footprint = Column(Float)
    manufacturing_date = Column(String, default="2026-01-01")
    status = Column(String, default="Active")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Battery DPP API")

@app.get("/")
def read_root():
    return {"message": "Bateriju sistēma darbojas bez kļūdām!"}

@app.get("/battery/{battery_id}/scan", response_class=HTMLResponse)
def scan_page(battery_id: str):
    db = SessionLocal()
    try:
        # AUTOMĀTISKAIS DROŠĪBAS TĪKLS: Ja baterijas nav, mēs to uzreiz izveidojam demonstrācijai!
        battery = db.query(BatteryModel).filter(BatteryModel.battery_id == battery_id).first()
        if not battery:
            battery = BatteryModel(
                battery_id=battery_id,
                model="Demo Litija Baterija X1",
                manufacturer="EcoBattery SIA",
                chemistry="NMC (Litija niķeļa mangāna kobalta oksīds)",
                carbon_footprint=45.5,
                manufacturing_date="2026-06-01",
                status="Active"
            )
            db.add(battery)
            db.commit()
            db.refresh(battery)
        
        qr_img_endpoint = f"/battery/{battery_id}/qrcode"
        json_endpoint = f"/battery/{battery_id}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Baterijas Digitālā Pase - {battery_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f9; padding: 40px; }}
                .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0px 6px 15px rgba(0,0,0,0.1); display: inline-block; max-width: 450px; width: 100%; }}
                h2 {{ color: #1a1a1a; margin-bottom: 5px; }}
                .badge {{ background: #e1ffec; color: #008738; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; margin-bottom: 15px; }}
                p {{ color: #555; margin: 8px 0; font-size: 14px; text-align: left; }}
                .info-box {{ background: #f9f9fb; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #eee; }}
                img {{ margin: 15px 0; border: 1px solid #ddd; padding: 10px; border-radius: 8px; background: white; }}
                .btn {{ display: block; width: 100%; box-sizing: border-box; margin-top: 15px; padding: 12px 0; background: #007BFF; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; text-align: center; }}
                .btn:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Digitālā Baterijas Pase (DPP)</h2>
                <div class="badge">ES Regulas prasībām atbilstoša</div>
                
                <div class="info-box">
                    <p>ID numurs: <strong>{battery.battery_id}</strong></p>
                    <p>Modelis: <strong>{battery.model}</strong></p>
                    <p>Ražotājs: <strong>{battery.manufacturer}</strong></p>
                    <p>Ķīmiskais sastāvs: <strong>{battery.chemistry}</strong></p>
                    <p>Oglekļa pēda: <strong>{battery.carbon_footprint} kg CO2eq</strong></p>
                    <p>Ražošanas datums: <strong>{battery.manufacturing_date}</strong></p>
                    <p>Statuss: <strong>{battery.status}</strong></p>
                </div>

                <p style="text-align: center; font-size: 13px; color: #777;">Noskenē šo QR kodu ar telefonu:</p>
                <img src="{qr_img_endpoint}" alt="QR Kods" width="200" height="200">
                
                <a class="btn" href="{json_endpoint}" target="_blank">Skatīt API JSON datus</a>
            </div>
        </body>
        </html>
        """
        return html_content
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
        data_url = f"https://battery-dpp-api-production-a9d8.up.railway.app/battery/{battery_id}/scan"
        
        img = qrcode.make(data_url)
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return Response(content=img_io.getvalue(), media_type="image/png")
    finally:
        db.close()
