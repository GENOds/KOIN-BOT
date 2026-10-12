import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import random
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
GUILD_ID = 1558732708866424924
STAFF_ROLE_NAME = "STAFF"
ELITE_ROLE_NAME = "ELITE"
GOD_ROLE_NAME = "GOD"
RICH_ROLE_NAME = "RICH"
KOINS_PER_MINUTE = 10

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

db = sqlite3.connect("koins.db", check_same_thread=False)
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, koins INTEGER DEFAULT 0)")
db.commit()

def get_koins(user_id: int) -> int:
    cur.execute("SELECT koins FROM users WHERE user_id =?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO users (user_id, koins) VALUES (?, 0)", (user_id,))
        db.commit()
        return 0
    return row[0]

def set_koins(user_id: int, amount: int):
    amount = max(0, amount)
    cur.execute("INSERT OR REPLACE INTO users (user_id, koins) VALUES (?,?)", (user_id, amount))
    db.commit()

def add_koins(user_id: int, amount: int):
    current = get_koins(user_id)
    set_koins(user_id, current + amount)

def is_staff():
    async def predicate(interaction: discord.Interaction):
        if any(r.name == STAFF_ROLE_NAME for r in interaction.user.roles):
            return True
        await interaction.response.send_message(f"❌ Solo il ruolo `{STAFF_ROLE_NAME}` può usare questo comando.", ephemeral=True)
        return False
    return app_commands.check(predicate)

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def buy_role(self, interaction: discord.Interaction, role_name: str, price: int):
        user_koins = get_koins(interaction.user.id)
        if user_koins < price:
            await interaction.response.send_message(f"❌ Non hai abbastanza KOINS. Ti servono {price}, tu hai {user_koins}.", ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            await interaction.response.send_message(f"❌ Il ruolo `{role_name}` non esiste. Crealo prima.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message(f"❌ Hai già il ruolo `{role_name}`.", ephemeral=True)
            return
        set_koins(interaction.user.id, user_koins - price)
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"✅ Hai comprato **{role_name}** per **{price} KOINS**!", ephemeral=True)

    @discord.ui.button(label="ELITE - 3000 KOINS", style=discord.ButtonStyle.primary, custom_id="buy_elite")
    async def elite_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_role(interaction, ELITE_ROLE_NAME, 3000)

    @discord.ui.button(label="GOD - 5000 KOINS", style=discord.ButtonStyle.success, custom_id="buy_god")
    async def god_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_role(interaction, GOD_ROLE_NAME, 5000)

    @discord.ui.button(label="RICH - 10000 KOINS", style=discord.ButtonStyle.danger, custom_id="buy_rich")
    async def rich_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_role(interaction, RICH_ROLE_NAME, 10000)

@bot.event
async def on_ready():
    print(f"KOIN~BOT ONLINE come {bot.user}")
    bot.add_view(ShopView())
    if not give_koins_loop.is_running():
        give_koins_loop.start()

@bot.event
async def setup_hook():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print("Slash sincronizzati per KROMA")

@tasks.loop(minutes=1)
async def give_koins_loop():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    for member in guild.members:
        if member.bot:
            continue
        if member.status!= discord.Status.offline:
            add_koins(member.id, KOINS_PER_MINUTE)

@bot.tree.command(name="pay", description="Paga un utente in KOINS")
@app_commands.describe(username="Utente da pagare", numero="Quantità di KOINS")
async def pay(interaction: discord.Interaction, username: discord.Member, numero: int):
    if numero <= 0:
        await interaction.response.send_message("❌ Inserisci un numero maggiore di 0.", ephemeral=True)
        return
    if username.id == interaction.user.id:
        await interaction.response.send_message("❌ Non puoi pagare te stesso.", ephemeral=True)
        return
    if username.bot:
        await interaction.response.send_message("❌ Non puoi pagare un bot.", ephemeral=True)
        return
    sender_koins = get_koins(interaction.user.id)
    if sender_koins < numero:
        await interaction.response.send_message(f"❌ Non hai abbastanza soldi. Hai **{sender_koins} KOINS**, ne servono {numero}.", ephemeral=True)
        return
    set_koins(interaction.user.id, sender_koins - numero)
    add_koins(username.id, numero)
    await interaction.response.send_message(f"✅ Hai pagato **{numero} KOINS** a {username.mention}!")

@bot.tree.command(name="portafoglio", description="Vedi il portafoglio di un utente")
@app_commands.describe(username="Utente di cui vedere il portafoglio")
async def portafoglio(interaction: discord.Interaction, username: discord.Member):
    koins = get_koins(username.id)
    msg = f"🪙—-: PORTAFOGLIO DI {username.display_name.upper()} :—-🪙\n\nKOINS: \"{koins}\""
    await interaction.response.send_message(msg)

@bot.tree.command(name="kshop", description="Apri lo shop dei ruoli")
async def kshop(interaction: discord.Interaction):
    embed = discord.Embed(title="🪙BENVENUTO NELLO SHOP🪙", description=f"Ruolo \"ELITE\" 3000 KOINS\n\nRuolo \"GOD\" 5000 KOINS\n\nRuolo \"RICH\" 10000 KOINS", color=0x2A8BFF)
    await interaction.response.send_message(embed=embed, view=ShopView())

@bot.tree.command(name="koinsadd", description="[STAFF] Aggiungi KOINS a un utente")
@app_commands.describe(username="Utente", amount="Quantità")
@is_staff()
async def koinsadd(interaction: discord.Interaction, username: discord.Member, amount: int):
    add_koins(username.id, amount)
    new_total = get_koins(username.id)
    await interaction.response.send_message(f"✅ Aggiunti **{amount} KOINS** a {username.mention}. Ora ha **{new_total} KOINS**.")

@bot.tree.command(name="koinsremove", description="[STAFF] Rimuovi KOINS a un utente")
@app_commands.describe(username="Utente", amount="Quantità")
@is_staff()
async def koinsremove(interaction: discord.Interaction, username: discord.Member, amount: int):
    current = get_koins(username.id)
    new_amount = max(0, current - amount)
    set_koins(username.id, new_amount)
    await interaction.response.send_message(f"✅ Rimossi **{amount} KOINS** da {username.mention}. Ora ha **{new_amount} KOINS** (era {current}).")

@bot.tree.command(name="koinsgiveaway", description="[STAFF] Giveaway KOINS random")
@app_commands.describe(amount="Quantità di KOINS da regalare")
@is_staff()
async def koinsgiveaway(interaction: discord.Interaction, amount: int):
    guild = interaction.guild
    eligible = [m for m in guild.members if not m.bot]
    if not eligible:
        await interaction.response.send_message("❌ Nessun membro eleggibile.", ephemeral=True)
        return
    winner = random.choice(eligible)
    add_koins(winner.id, amount)
    try:
        await winner.send(f"HAI VINTO UN GIVEAWAY DI KROMA, AGGIUNTI \"{amount}\" KOINS AL TUO CONTO!")
        dm_status = "DM inviato"
    except:
        dm_status = "DM chiusi, ma KOINS aggiunti"
    await interaction.response.send_message(f"🎉 Giveaway di **{amount} KOINS** vinto da {winner.mention}! {dm_status}")

if not TOKEN:
    print("ERRORE: TOKEN non trovato nelle variabili d'ambiente! Mettilo in ENV")
else:
    bot.run(TOKEN)