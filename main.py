import discord
from discord import app_commands
from discord.ext import commands
import datetime
import json
import os
import traceback
import time
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# โหลด .env
load_dotenv()

# =================================================================
# 🌐 Web Server (Render + UptimeRobot)
# =================================================================
app = Flask('')

@app.route('/')
def home():
    return "I'm alive! Discord Bot is running."

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# =================================================================
# ⚙️ Config System
# =================================================================
CONFIG_FILE = 'config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def get_guild_config(guild_id):
    config = load_config()
    return config.get(str(guild_id), {})

def update_guild_config(guild_id, data):
    config = load_config()
    str_id = str(guild_id)
    if str_id not in config:
        config[str_id] = {}
    config[str_id].update(data)
    save_config(config)

# =================================================================
# 🤖 Bot Setup
# =================================================================
class BoostBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Synced Slash Commands เรียบร้อย")

    async def on_ready(self):
        print(f'🤖 Bot User: {self.user}')
        print(f'🚀 Status: Online & Ready!')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="คนบูสต์เซิร์ฟ 🚀"))

bot = BoostBot()

# =================================================================
# 🛡️ Error Handler
# =================================================================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ ต้องเป็น Administrator เท่านั้น", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ รออีก {error.retry_after:.2f} วินาที", ephemeral=True)
    else:
        print(f"⚠️ Error: {error}")
        traceback.print_exc()

# =================================================================
# 🛠️ Slash Commands
# =================================================================
@bot.tree.command(name="setup", description="ตั้งค่าห้องแจ้งเตือน")
@app_commands.describe(channel="เลือกห้อง")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    if not channel.permissions_for(interaction.guild.me).send_messages:
        return await interaction.response.send_message(f"❌ บอทไม่มีสิทธิ์ส่งข้อความในห้อง {channel.mention}", ephemeral=True)
    update_guild_config(interaction.guild_id, {"channel_id": channel.id})
    await interaction.response.send_message(embed=discord.Embed(title="✅ ตั้งค่าเรียบร้อย", description=f"แจ้งเตือนที่: {channel.mention}", color=0x00ff00), ephemeral=True)

@bot.tree.command(name="add_role", description="ตั้งค่ายศแจก/ยึด")
@app_commands.checks.has_permissions(administrator=True)
async def add_role(interaction: discord.Interaction, role1: discord.Role, role2: discord.Role=None, role3: discord.Role=None, role4: discord.Role=None):
    roles = [r for r in [role1, role2, role3, role4] if r is not None]
    for r in roles:
        if r >= interaction.guild.me.top_role:
            return await interaction.response.send_message(f"❌ ยศ {r.mention} สูงกว่ายศบอท!", ephemeral=True)
    update_guild_config(interaction.guild_id, {"role_ids": [r.id for r in roles]})
    await interaction.response.send_message(embed=discord.Embed(title="✅ บันทึกยศเรียบร้อย", description=f"จำนวน: {len(roles)} ยศ", color=0x00ff00), ephemeral=True)

@bot.tree.command(name="test", description="ทดสอบระบบ")
@app_commands.choices(action=[app_commands.Choice(name="🚀 จำลอง Boost", value="boost"), app_commands.Choice(name="📉 จำลอง Unboost", value="unboost")])
@app_commands.checks.has_permissions(administrator=True)
async def test(interaction: discord.Interaction, action: app_commands.Choice[str]):
    await interaction.response.send_message(f"⏳ ทดสอบ: **{action.name}**", ephemeral=True)
    if action.value == "boost": await handle_new_boost(interaction.user)
    else: await handle_remove_boost(interaction.user)

# =================================================================
# 📢 Logic (Boost/Unboost)
# =================================================================
@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        await handle_new_boost(after)
    elif before.premium_since is not None and after.premium_since is None:
        await handle_remove_boost(after)

async def handle_new_boost(member):
    config = get_guild_config(member.guild.id)
    role_ids = config.get("role_ids", [])
    channel_id = config.get("channel_id")
    added = []
    
    for r_id in role_ids:
        role = member.guild.get_role(r_id)
        if role:
            try: await member.add_roles(role); added.append(role.name)
            except: pass

    if channel_id:
        ch = member.guild.get_channel(channel_id)
        if ch:
            embed = discord.Embed(title=f"🚀 {member.guild.name} ได้รับการบูสต์!", color=0xf47fff, timestamp=datetime.datetime.now())
            embed.set_thumbnail(url=member.display_avatar.url)
            if member.guild.banner: embed.set_image(url=member.guild.banner.url)
            if added: embed.add_field(name="🎁 ยศที่ได้รับ", value="\n".join([f"✅ {n}" for n in added]), inline=False)
            embed.set_footer(text=f"Level: {member.guild.premium_tier} • Boosts: {member.guild.premium_subscription_count}")
            await ch.send(embed=embed)
    
    try: await member.send(embed=discord.Embed(title=f"ขอบคุณที่บูสต์ {member.guild.name}!", description="รับยศพิเศษเรียบร้อยครับ", color=0xf47fff))
    except: pass

async def handle_remove_boost(member):
    config = get_guild_config(member.guild.id)
    role_ids = config.get("role_ids", [])
    channel_id = config.get("channel_id")
    removed = []

    for r_id in role_ids:
        role = member.guild.get_role(r_id)
        if role and role in member.roles:
            try: await member.remove_roles(role); removed.append(role.name)
            except: pass
            
    if channel_id:
        ch = member.guild.get_channel(channel_id)
        if ch:
            embed = discord.Embed(title=f"📉 {member.name} ยกเลิกการบูสต์", description=f"เสียดายจัง {member.mention} ถอดบูสต์แล้ว", color=0xff4d4d, timestamp=datetime.datetime.now())
            embed.set_thumbnail(url=member.display_avatar.url)
            if member.guild.banner: embed.set_image(url=member.guild.banner.url)
            embed.add_field(name="♻️ ยึดยศคืน", value="\n".join([f"❌ {n}" for n in removed]) if removed else "ไม่มี", inline=False)
            embed.set_footer(text=f"Remaining: {member.guild.premium_subscription_count}")
            await ch.send(embed=embed)

# =================================================================
# 🔥 ระบบ Run บอทแบบปลอดภัย (Anti-Crash & Rate Limit Protection)
# =================================================================
keep_alive()

token = os.environ.get('TOKEN')

if not token:
    print("❌ Error: ไม่พบ TOKEN")
else:
    # วนลูปเพื่อป้องกันบอทดับถาวร
    while True:
        try:
            bot.run(token)
        except discord.errors.HTTPException as e:
            # ถ้าเจอ Error 429 (Rate Limit) หรือ 1015 (Cloudflare)
            if e.status == 429:
                print("\n🔴 เจอ Rate Limit (429)! บอทจะพัก 30 นาที...")
                print("⏳ กำลังนับถอยหลัง... ห้ามปิดโปรแกรม...")
                time.sleep(1800) # นอนหลับ 30 นาที (1800 วิ)
            else:
                print(f"\n⚠️ HTTP Error: {e}")
                print("♻️ จะลองเชื่อมต่อใหม่ใน 10 วินาที...")
                time.sleep(10)
        except Exception as e:
            print(f"\n❌ เกิดข้อผิดพลาด: {e}")
            print("♻️ จะลองเชื่อมต่อใหม่ใน 10 วินาที...")
            time.sleep(10)
        
