import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# Mini servidor HTTP para que Render mantenga el bot activo en la capa gratis
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Ignis esta online!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

Thread(target=run_dummy_server, daemon=True).start()

# Cliente Gemini y Bot de Discord
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

SYSTEM_PROMPT = """
Eres Ignis, el Maestro del Gremio de Caza y Analista Supremo de Metagame de Monster Hunter.
Conoces al detalle las builds de máximo DPS y Speedrun (Time Attack / TA) de toda la saga (MHGU, MHW: Iceborne, MHR: Sunbreak, MH4U, etc.).

PERSONALIDAD:
- Directo, analítico y enfocado en la máxima eficiencia matemática.
- Tratas a los usuarios como "cazadores" o "camaradas".
- Respuestas estructuradas con negritas y listas en viñetas.

REGLAS DE PRECISIÓN TÉCNICA (OBLIGATORIO):
1. ENFOQUE META/TA: Recomienda siempre el meta de máximo DPS del juego solicitado. Ignora habilidades de confort (Salud, Comilón) a menos que se pidan.
2. ADAPTABILIDAD Y LÓGICA DE ARMA:
   - Adapta el set al juego consultado (ej. Fatalis/Safi en Iceborne; Dereliction/Mail of Hell en Sunbreak; Black X / JhoCena / Silver Sol en MHGU).
   - Respeta la lógica del arma: GS requiere Focus y habilidades de desenfunde; armas de combo rápido (LS, Duales) requieren afinidad constante y afilado. NUNCA sugieras Crit Draw en Katana o Duales.
3. CERO ALUCINACIONES: NUNCA inventes piezas, joyas, afilados o slots. No mezcles Peak Performance con Resentment.
4. INDEPENDENCIA TOTAL: Trata cada consulta de forma 100% INDEPENDIENTE. No recicles piezas de la respuesta anterior.

ESTRUCTURA DE RESPUESTA:
- Juego / Arma / Estilo
- Categoría (Meta / TA)
- Arma y Afilado
- Piezas de Armadura
- Habilidades Clave y razón del DPS
- Talismán y Joyas requeridas
"""

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Ignis encendido como {bot.user}")

@bot.tree.command(name="ignis", description="Consulta una build meta/speedrun a Ignis")
async def ignis_cmd(interaction: discord.Interaction, consulta: str):
    await interaction.response.defer()
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=consulta,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            ),
        )
        
        texto = response.text or "No pude procesar la consulta."
    except Exception as e:
        print(f"Error al consultar Gemini: {e}")
        texto = f"⚠️ Ocurrió un error al procesar la respuesta: {e}"
        
    mensajes = [texto[i:i + 1900] for i in range(0, len(texto), 1900)]
    
    await interaction.followup.send(mensajes[0])
    for msg in mensajes[1:]:
        await interaction.channel.send(msg)

bot.run(os.environ["DISCORD_TOKEN"])
