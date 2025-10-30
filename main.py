from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from datetime import datetime
from typing import List
import httpx
import logging
import random
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import csv
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Inspirational Quote API")

# Configuration for llama.cpp server
LLAMA_CPP_URL = os.getenv("LLAMA_CPP_URL", "http://llama:8080")  # Docker/K8s service name
COMPLETION_ENDPOINT = f"{LLAMA_CPP_URL}/completion"

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://quotes_user:quotes_password@localhost:5432/quotes_db")

# Theme variation
THEMES = [
    # Achievement & Success
    "success", "achievement", "excellence", "victory", "accomplishment",

    # Personal Growth
    "growth", "development", "improvement", "transformation", "evolution",

    # Mental Strength
    "perseverance", "resilience", "determination", "persistence", "tenacity",
    "grit", "endurance", "fortitude",

    # Emotional Qualities
    "courage", "bravery", "confidence", "self-belief", "inner strength",
    "strength", "power", "boldness",

    # Vision & Aspiration
    "dreams", "ambition", "goals", "vision", "aspiration", "purpose",
    "potential", "possibilities",

    # Positive Change
    "change", "innovation", "progress", "renewal", "reinvention",
    "adaptation", "flexibility",

    # Wisdom & Learning
    "wisdom", "knowledge", "learning", "understanding", "insight",
    "awareness", "enlightenment",

    # Optimism & Hope
    "hope", "optimism", "positivity", "faith", "trust", "belief",

    # Action & Energy
    "action", "momentum", "drive", "energy", "initiative", "movement",

    # Creativity & Innovation
    "creativity", "imagination", "innovation", "originality", "inspiration",

    # Leadership & Influence
    "leadership", "influence", "impact", "legacy", "contribution",

    # Balance & Peace
    "balance", "harmony", "peace", "serenity", "mindfulness",

    # Overcoming Challenges
    "obstacles", "challenges", "adversity", "struggle", "difficulty",

    # Time & Opportunity
    "opportunity", "timing", "present moment", "new beginnings", "fresh starts",

    # Passion & Purpose
    "passion", "enthusiasm", "dedication", "commitment", "devotion"
]

class QuoteResponse(BaseModel):
    id: int
    quote: str
    date: str
    theme: str

class QuoteListItem(BaseModel):
    id: int
    quote: str
    generated_at: str
    theme: str

def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )

def store_quote(quote: str, generated_at: str, theme: str):
    """Store a quote in the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO quotes (quote, generated_at, theme) VALUES (%s, %s, %s) RETURNING id;",
            (quote, generated_at, theme)
        )
        quote_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return quote_id
    except Exception as e:
        logger.error(f"Failed to store quote: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to store quote in database"
        )

@app.get("/quote", response_model=QuoteResponse)
async def get_inspirational_quote():
    """
    Generate an inspirational quote using the llama.cpp model.
    Returns a JSON response with the quote and generation date.
    """
    try:
        # Prepare the prompt for the model
        theme = random.choice(THEMES)

        user_message = f"""Generate a unique and inspiring quote about {theme} (maximum 20 words) without punctuation or quotation marks.
        Only return the quote itself."""

        # Apply Llama 3.2 chat template manually
        prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

        # Prepare request payload for llama.cpp completion endpoint
        payload = {
            "prompt": prompt,
            "n_predict": 50,  # Max tokens to generate,
            "temperature": 0.9,  # Creativity level
            "top_p": 0.95, # More diverse
            "top_k": 40, # More variety
            "repeat_penalty": "1.2", # Reduce repetition
            "stop": ["<|eot_id|>", "<|end_of_text|>", "\n"], #  Stop sequences
            "stream": False,
        }

        # Make async HTTP request to llama.cpp server
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info(f"Sending request to {COMPLETION_ENDPOINT}")
            response = await client.post(COMPLETION_ENDPOINT, json=payload)
            logger.info(f"Full response from llama.cpp: {response.json()}")
            response.raise_for_status()

            # Parse the response
            result = response.json()
            logger.info(f"Received response: {result}")

            # Extract the generated text
            generated_text = result.get("content", "").strip()

            # Clean up the quote (remove any extra whitespace or newlines)
            quote = " ".join(generated_text.split())
            logger.info(f"Cleaned quote: '{quote}'")

            # If quote is empty or too short, provide a fallback
            if not quote or len(quote) < 10:
                quote = "Believe in yourself and all that you are capable of achieving."

            # Get current date in ISO format
            current_date = datetime.now().isoformat()

            # Store in database
            quote_id = store_quote(quote, current_date, theme)

            return QuoteResponse(id=quote_id, quote=quote, date=current_date, theme=theme)

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Error communicating with llama.cpp server: {str(e)}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to llama.cpp server: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/quotes", response_model=List[QuoteListItem])
async def list_quotes(limit: int = 50):
    """
    Retrieve stored quotes from the database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT id, quote, generated_at, theme FROM quotes ORDER BY generated_at DESC LIMIT %s;",
            (limit,)
        )
        quotes = cursor.fetchall()
        cursor.close()
        conn.close()

        return [
            QuoteListItem(
                id=q['id'],
                quote=q['quote'],
                generated_at=q['generated_at'].isoformat() if hasattr(q['generated_at'], 'isoformat') else str(q['generated_at']),
                theme=q['theme']
            )
            for q in quotes
        ]
    except Exception as e:
        logger.error(f"Failed to retrieve quotes: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve quotes from database"
        )

@app.get("/quotes/export/csv")
async def export_quotes_csv():
    """
    Export all stored quotes as CSV file.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT id, quote, generated_at, theme FROM quotes ORDER BY generated_at DESC;"
        )
        quotes = cursor.fetchall()
        cursor.close()
        conn.close()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Quote', 'Generated At', 'Theme'])

        for quote in quotes:
            writer.writerow([
                quote['id'],
                quote['quote'],
                quote['generated_at'],
                quote['theme']
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=quotes.csv"}
        )
    except Exception as e:
        logger.error(f"Failed to export quotes: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export quotes"
        )

@app.get("/quotes/export/json")
async def export_quotes_json():
    """
    Export all stored quotes as JSON file.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT id, quote, generated_at, theme FROM quotes ORDER BY generated_at DESC;"
        )
        quotes = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert to JSON-serializable format
        quotes_data = [
            {
                'id': q['id'],
                'quote': q['quote'],
                'generated_at': q['generated_at'].isoformat() if hasattr(q['generated_at'], 'isoformat') else str(q['generated_at']),
                'theme': q['theme']
            }
            for q in quotes
        ]

        json_data = json.dumps(quotes_data, indent=2)
        return StreamingResponse(
            iter([json_data]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=quotes.json"}
        )
    except Exception as e:
        logger.error(f"Failed to export quotes: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export quotes"
        )

@app.delete("/quotes/{quote_id}")
async def delete_quote(quote_id: int):
    """
    Delete a specific quote from the database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM quotes WHERE id = %s;", (quote_id,))
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": f"Quote {quote_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete quote: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete quote"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.close()
        conn.close()
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint serving HTML page."""
    return FileResponse("index.html")
