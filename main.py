from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sqlite3
import os
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="API Inteligente - Reseñas de Negocio Local", version="1.0")

# --- BASE DE DATOS SQLITE---
def init_db():
    conn = sqlite3.connect("resenas.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resenas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            comentario TEXT NOT NULL,
            calificacion INTEGER NOT NULL,
            sentimiento TEXT,
            resumen_ia TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- MODELOS PYDANTIC (Validaciones) ---
class ResenaCreate(BaseModel):
    cliente: str = Field(..., min_length=2, description="Nombre del cliente")
    comentario: str = Field(..., min_length=5, description="Comentario o reseña")
    calificacion: int = Field(..., ge=1, le=5, description="Calificación de 1 a 5")

#POST: Crear una nueva reseña
@app.post("/resenas/", status_code=201)
def crear_resena(resena: ResenaCreate):
    conn = sqlite3.connect("resenas.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO resenas (cliente, comentario, calificacion) VALUES (?, ?, ?)",
        (resena.cliente, resena.comentario, resena.calificacion)
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return {"id": nuevo_id, "mensaje": "Reseña creada con éxito", **resena.dict()}

#Listar todas las reseñas registradas
@app.get("/resenas/")
def listar_resenas():
    conn = sqlite3.connect("resenas.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, cliente, comentario, calificacion, sentimiento, resumen_ia FROM resenas")
    filas = cursor.fetchall()
    conn.close()
    
    resultado = []
    for f in filas:
        resultado.append({
            "id": f[0], "cliente": f[1], "comentario": f[2],
            "calificacion": f[3], "sentimiento": f[4], "resumen_ia": f[5]
        })
    return resultado

#Obtener una reseña específica
@app.get("/resenas/{resena_id}")
def obtener_resena(resena_id: int):
    conn = sqlite3.connect("resenas.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, cliente, comentario, calificacion, sentimiento, resumen_ia FROM resenas WHERE id = ?", (resena_id,))
    fila = cursor.fetchone()
    conn.close()
    
    if not fila:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")
    
    return {
        "id": fila[0], "cliente": fila[1], "comentario": fila[2],
        "calificacion": fila[3], "sentimiento": fila[4], "resumen_ia": fila[5]
    }

#DELETE: Eliminar una reseña por su ID
@app.delete("/resenas/{resena_id}")
def eliminar_resena(resena_id: int):
    conn = sqlite3.connect("resenas.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM resenas WHERE id = ?", (resena_id,))
    fila = cursor.fetchone()
    
    if not fila:
        conn.close()
        raise HTTPException(status_code=404, detail="Reseña no encontrada")
    
    cursor.execute("DELETE FROM resenas WHERE id = ?", (resena_id,))
    conn.commit()
    conn.close()
    
    return {"mensaje": f"Reseña con ID {resena_id} eliminada con éxito"}

#ENDPOINT INTELIGENTE GLOBAL (IA): Analiza todas las reseñas acumuladas
@app.post("/resenas/analizar-todas-ia")
def analizar_todas_las_resenas():
    conn = sqlite3.connect("resenas.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, comentario, calificacion FROM resenas")
    filas = cursor.fetchall()
    
    if not filas:
        conn.close()
        raise HTTPException(status_code=404, detail="No hay reseñas registradas para analizar")
    
    total_resenas = len(filas)
    positivos = 0
    neutrales = 0
    negativos = 0
    
    for fila in filas:
        resena_id = fila[0]
        comentario = fila[1]
        calificacion = fila[2]
        
        #detección de sentimientos
        if calificacion >= 4 or "excelente" in comentario.lower() or "bueno" in comentario.lower() or "encantó" in comentario.lower():
            sentimiento = "Positivo"
            positivos += 1
        elif calificacion == 3:
            sentimiento = "Neutral"
            neutrales += 1
        else:
            sentimiento = "Negativo"
            negativos += 1
            
        resumen_parcial = f"Resumen IA: Cliente satisfecho con calificación {calificacion}." if sentimiento == "Positivo" else f"Resumen IA: Experiencia evaluada como {sentimiento.lower()}."
        
        cursor.execute(
            "UPDATE resenas SET sentimiento = ?, resumen_ia = ? WHERE id = ?",
            (sentimiento, resumen_parcial, resena_id)
        )
        
    conn.commit()
    conn.close()
    
    resumen_global = f"Análisis general del negocio basado en {total_resenas} opiniones: {positivos} comentarios positivos, {neutrales} neutrales y {negativos} negativos."
    
    return {
        "total_reseñas_procesadas": total_resenas,
        "balance_sentimientos": {
            "positivos": positivos,
            "neutrales": neutrales,
            "negativos": negativos
        },
        "resumen_general_del_negocio": resumen_global
    }