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
# 🌐 Web Server (สำหรับ Koyeb / Render / UptimeRobot)
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
# ⚙️ Config System (ระบบบันทึกค่า)
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
        await interaction.response.send_message("❌ **คุณไม่มีสิทธิ์** (ต้องเป็น Administrator)", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ ใจเย็นๆ รออีก {error.retry_after:.2f} วินาที", ephemeral=True)
    else:
        print(f"⚠️ Error: {error}")
        traceback.print_exc()

# =================================================================
# 🛠️ Slash Commands
# =================================================================

@bot.tree.command(name="setup", description="ตั้งค่าห้องแจ้งเตือนคนบูสต์")
@app_commands.describe(channel="เลือกห้องที่ต้องการให้แจ้งเตือน")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    if not channel.permissions_for(interaction.guild.me).send_messages:
        return await interaction.response.send_message(f"❌ บอทไม่มีสิทธิ์ส่งข้อความในห้อง {channel.mention}", ephemeral=True)
    update_guild_config(interaction.guild_id, {"channel_id": channel.id})
    await interaction.response.send_message(embed=discord.Embed(title="✅ ตั้งค่าห้องเรียบร้อย", description=f"แจ้งเตือนที่: {channel.mention}", color=0x00ff00), ephemeral=True)

@bot.tree.command(name="add_role", description="ตั้งค่ายศที่จะแจกรางวัล")
@app_commands.checks.has_permissions(administrator=True)
async def add_role(interaction: discord.Interaction, role1: discord.Role, role2: discord.Role=None, role3: discord.Role=None, role4: discord.Role=None):
    await save_roles(interaction, role1, role2, role3, role4)

@bot.tree.command(name="edit_role", description="แก้ไขยศที่จะแจกรางวัล")
@app_commands.checks.has_permissions(administrator=True)
async def edit_role(interaction: discord.Interaction, role1: discord.Role, role2: discord.Role=None, role3: discord.Role=None, role4: discord.Role=None):
    await save_roles(interaction, role1, role2, role3, role4)

async def save_roles(interaction, r1, r2, r3, r4):
    roles = [r for r in [r1, r2, r3, r4] if r is not None]
    
    # เช็คยศบอท
    for r in roles:
        if r >= interaction.guild.me.top_role:
            return await interaction.response.send_message(f"❌ ยศ {r.mention} สูงกว่ายศของบอท! โปรดเลื่อนยศบอทขึ้นไป", ephemeral=True)
            
    update_guild_config(interaction.guild_id, {"role_ids": [r.id for r in roles]})
    
    role_mentions = "\n".join([f"• {r.mention}" for r in roles])
    embed = discord.Embed(title="✅ บันทึกยศรางวัลเรียบร้อย", description=f"รายการยศ:\n{role_mentions}", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="list_role", description="ดูรายชื่อยศที่ตั้งค่าไว้")
@app_commands.checks.has_permissions(administrator=True)
async def list_role(interaction: discord.Interaction):
    config = get_guild_config(interaction.guild_id)
    role_ids = config.get("role_ids", [])
    
    if not role_ids:
        return await interaction.response.send_message("❌ ยังไม่ได้ตั้งค่ายศเลยครับ ใช้ `/add_role` ก่อนนะ", ephemeral=True)
    
    text_list = []
    for r_id in role_ids:
        role = interaction.guild.get_role(r_id)
        if role:
            text_list.append(f"✅ {role.mention}")
        else:
            text_list.append(f"❌ ยศที่ถูกลบไปแล้ว (ID: {r_id})")
            
    embed = discord.Embed(
        title="📋 รายชื่อยศรางวัล Boost",
        description="\n".join(text_list),
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="test", description="ทดสอบระบบ")
@app_commands.choices(action=[app_commands.Choice(name="🚀 จำลอง Boost", value="boost"), app_commands.Choice(name="📉 จำลอง Unboost", value="unboost")])
@app_commands.checks.has_permissions(administrator=True)
async def test(interaction: discord.Interaction, action: app_commands.Choice[str]):
    await interaction.response.send_message(f"⏳ เริ่มการทดสอบ: **{action.name}**", ephemeral=True)
    if action.value == "boost": await handle_new_boost(interaction.user)
    else: await handle_remove_boost(interaction.user)

# =================================================================
# 📢 Logic (Boost/Unboost)
# =================================================================
@bot.event
async def on_member_update(before, after):
    # เริ่มบูสต์
    if before.premium_since is None and after.premium_since is not None:
        await handle_new_boost(after)
    # เลิกบูสต์
    elif before.premium_since is not None and after.premium_since is None:
        await handle_remove_boost(after)

async def handle_new_boost(member):
    guild = member.guild
    config = get_guild_config(guild.id)
    role_ids = config.get("role_ids", [])
    channel_id = config.get("channel_id")
    added = []
    
    # แจกยศ
    for r_id in role_ids:
        role = guild.get_role(r_id)
        if role:
            try: await member.add_roles(role); added.append(role.name)
            except: pass

    # ส่ง Embed แจ้งเตือน
    if channel_id:
        ch = guild.get_channel(channel_id)
        if ch:
            # ชื่อผู้บูสต์ขึ้นหัวข้อ Embed + Banner ด้านล่าง
            embed = discord.Embed(
                title=f"🚀 {member.name} ได้ทำการบูสต์เซิร์ฟเวอร์!", 
                description=f"ขอบคุณ {member.mention} มากๆ ครับที่บูสต์เซิร์ฟเวอร์ของพวกเรา! 💖",
                color=0xf47fff, 
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # ใส่ Banner เซิร์ฟเวอร์
            if guild.banner: embed.set_image(url=guild.banner.url)
            
            if added: embed.add_field(name="🎁 ยศที่ได้รับ", value="\n".join([f"✅ {n}" for n in added]), inline=False)
            embed.set_footer(text=f"Level: {guild.premium_tier} • Boosts: {guild.premium_subscription_count}")
            await ch.send(embed=embed)
    
    # DM ขอบคุณ
    try: await member.send(embed=discord.Embed(title=f"ขอบคุณที่บูสต์ {guild.name}!", description="คุณได้รับยศรางวัลพิเศษเรียบร้อยแล้วครับ", color=0xf47fff))
    except: pass

async def handle_remove_boost(member):
    guild = member.guild
    config = get_guild_config(guild.id)
    role_ids = config.get("role_ids", [])
    channel_id = config.get("channel_id")
    removed = []

    # ดึงยศคืน
    for r_id in role_ids:
        role = guild.get_role(r_id)
        if role and role in member.roles:
            try: await member.remove_roles(role); removed.append(role.name)
            except: pass
            
    # ส่ง Embed แจ้งเตือน
    if channel_id:
        ch = guild.get_channel(channel_id)
        if ch:
            embed = discord.Embed(
                title=f"📉 {member.name} ยกเลิกการบูสต์", 
                description=f"น่าเสียดายจัง... {member.mention} ได้ถอด Boost ออกแล้ว 😢", 
                color=0xff4d4d, 
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # ใส่ Banner เซิร์ฟเวอร์เหมือนกัน
            if guild.banner: embed.set_image(url=guild.banner.url)
            
            embed.add_field(name="♻️ ระบบทำการดึงยศคืน", value="\n".join([f"❌ {n}" for n in removed]) if removed else "ไม่มี", inline=False)
            embed.set_footer(text=f"Level: {guild.premium_tier} • Remaining: {guild.premium_subscription_count}")
            await ch.send(embed=embed)

# =================================================================
# 🔥 ระบบ Run (Safe Mode: ป้องกัน 429 Rate Limit)
# =================================================================
keep_alive()

token = os.environ.get('TOKEN')

if not token:
    print("❌ Error: ไม่พบ TOKEN (อย่าลืมตั้งค่าใน Environment Variables)")
else:
    while True:
        try:
            bot.run(token)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print("\n🔴 เจอ Rate Limit (429)! บอทจะพัก 30 นาที... (อย่าปิดโปรแกรม)")
                time.sleep(1800)
            else:
                print(f"\n⚠️ HTTP Error: {e}")
                time.sleep(10)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(10)

