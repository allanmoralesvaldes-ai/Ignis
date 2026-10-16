import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# Cambia aquí el modelo si te sale error de cuota (429):
# prueba "gemini-2.5-flash-lite"
MODELO = "gemini-3.8-flash"

# Mini servidor HTTP para que Render mantenga el bot activo en la capa gratis
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Ignis esta online!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

Thread(target=run_dummy_server, daemon=True).start()

# Cliente Gemini
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
3. CERO ALUCINACIONES: NUNCA inventes piezas, joyas, afilados o slots. No mezcles Peak Performance con Resentment. Si no estás seguro de una pieza o joya, dilo en vez de inventarla.
4. INDEPENDENCIA TOTAL: Trata cada consulta de forma 100% INDEPENDIENTE. No recicles piezas de la respuesta anterior.
5. DATOS FALTANTES: Si el cazador no indica el juego o el arma, pregúntalo antes de dar una build.

ESTRUCTURA DE RESPUESTA:
- Juego / Arma / Estilo
- Categoría (Meta / TA)
- Arma y Afilado
- Piezas de Armadura
- Habilidades Clave y razón del DPS
- Talismán y Joyas requeridas
"""

# Los comandos slash no necesitan message_content
intents = discord.Intents.default()

class IgnisBot(commands.Bot):
    async def setup_hook(self):
        # Se ejecuta una sola vez al arrancar
        await self.tree.sync()

bot = IgnisBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Ignis encendido como {bot.user}", flush=True)

@bot.tree.command(name="ignis", description="Consulta una build meta/speedrun a Ignis")
async def ignis_cmd(interaction: discord.Interaction, consulta: str):
    await interaction.response.defer()

    try:
        # asyncio.to_thread evita que el bot se congele mientras Gemini responde
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODELO,
            contents=consulta,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
            ),
        )
        texto = response.text or "No pude procesar la consulta."
    except Exception as e:
        print(f"Error al consultar Gemini: {e}", flush=True)
        if "429" in str(e):
            texto = "⚠️ Ignis alcanzó su límite de consultas por ahora. Intenta de nuevo en unos minutos."
        else:
            texto = "⚠️ Ocurrió un error al procesar la consulta."

    mensajes = [texto[i:i + 1900] for i in range(0, len(texto), 1900)]

    await interaction.followup.send(mensajes[0])
    for msg in mensajes[1:]:
        await interaction.followup.send(msg)

bot.run(os.environ["DISCORD_TOKEN"])
