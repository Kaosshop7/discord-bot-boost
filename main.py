import discord
from discord import app_commands
from discord.ext import commands
import datetime
import json
import os
import traceback
from flask import Flask
from threading import Thread
from dotenv import load_dotenv # เพิ่มตัวนี้เข้ามา

# โหลดค่าจากไฟล์ .env (สำหรับรันในคอมตัวเอง)
load_dotenv()

# =================================================================
# 🌐 ส่วนของ Web Server (Render + UptimeRobot)
# =================================================================
app = Flask('')

@app.route('/')
def home():
    return "I'm alive! Discord Bot is running."

def run():
    # ดึง Port จาก Environment (Render จะส่ง Port มาให้เอง)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# =================================================================
# ⚙️ ระบบจัดการข้อมูล
# =================================================================
CONFIG_FILE = 'config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ ไฟล์ config.json เสียหาย กำลังสร้างใหม่...")
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
# 🤖 ตัวบอท
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
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Bot Discord PDR COMMUNITY"))

bot = BoostBot()

# =================================================================
# 🛡️ Error Handler
# =================================================================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ **คุณไม่มีสิทธิ์ใช้คำสั่งนี้ครับ** (ต้องเป็น Administrator)", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ ใจเย็นๆ ครับ รออีก {error.retry_after:.2f} วินาที", ephemeral=True)
    else:
        print(f"⚠️ เกิดข้อผิดพลาด: {error}")
        traceback.print_exc()
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ เกิดข้อผิดพลาดบางอย่าง", ephemeral=True)

# =================================================================
# 🛠️ Slash Commands
# =================================================================
@bot.tree.command(name="help", description="ดูคำสั่งทั้งหมดและวิธีใช้งาน")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📘 คู่มือการใช้งาน Boost Bot",
        description="ระบบจัดการแจ้งเตือนและแจกยศอัตโนมัติเมื่อมีคน Boost Server",
        color=0x3498db
    )
    embed.add_field(name="⚙️ `/setup`", value="ตั้งค่าห้องแจ้งเตือน", inline=False)
    embed.add_field(name="🎖️ `/add_role`", value="ตั้งค่ายศที่จะแจก", inline=False)
    embed.add_field(name="🧪 `/test`", value="ทดสอบระบบ", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup", description="ตั้งค่าห้องสำหรับแจ้งเตือนคนบูสต์")
@app_commands.describe(channel="เลือกห้องข้อความที่ต้องการให้แจ้งเตือน")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    if not channel.permissions_for(interaction.guild.me).send_messages:
        return await interaction.response.send_message(f"❌ บอทไม่มีสิทธิ์ส่งข้อความในห้อง {channel.mention}", ephemeral=True)

    update_guild_config(interaction.guild_id, {"channel_id": channel.id})
    embed = discord.Embed(title="✅ ตั้งค่าห้องแจ้งเตือนเรียบร้อย", description=f"ห้องแจ้งเตือน: {channel.mention}", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="add_role", description="ตั้งค่ายศที่จะแจกเมื่อคนบูสต์")
@app_commands.checks.has_permissions(administrator=True)
async def add_role(interaction: discord.Interaction, role1: discord.Role, role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None):
    roles = [role1, role2, role3, role4]
    valid_roles = [r for r in roles if r is not None]
    
    bot_top_role = interaction.guild.me.top_role
    for r in valid_roles:
        if r >= bot_top_role:
            return await interaction.response.send_message(f"❌ ยศ {r.mention} สูงกว่ายศบอท!", ephemeral=True)

    valid_roles_ids = [r.id for r in valid_roles]
    update_guild_config(interaction.guild_id, {"role_ids": valid_roles_ids})
    
    role_mentions = [f"<@&{rid}>" for rid in valid_roles_ids]
    embed = discord.Embed(title="✅ บันทึกยศเรียบร้อย", description=f"ยศที่จะจัดการ:\n" + "\n".join(role_mentions), color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="test", description="ทดสอบระบบ")
@app_commands.describe(action="เลือกเหตุการณ์ที่ต้องการจำลอง")
@app_commands.choices(action=[
    app_commands.Choice(name="🚀 จำลองคนบูสต์", value="boost"),
    app_commands.Choice(name="📉 จำลองเลิกบูสต์", value="unboost")
])
@app_commands.checks.has_permissions(administrator=True)
async def test(interaction: discord.Interaction, action: app_commands.Choice[str]):
    await interaction.response.send_message(f"⏳ กำลังทดสอบ: **{action.name}**", ephemeral=True)
    if action.value == "boost":
        await handle_new_boost(interaction.user)
    elif action.value == "unboost":
        await handle_remove_boost(interaction.user)

# =================================================================
# 📢 Logic หลัก
# =================================================================
@bot.event
async def on_member_update(before, after):
    try:
        if before.premium_since is None and after.premium_since is not None:
            await handle_new_boost(after)
        elif before.premium_since is not None and after.premium_since is None:
            await handle_remove_boost(after)
    except Exception as e:
        print(f"🔥 Error: {e}")
        traceback.print_exc()

async def handle_new_boost(member):
    guild = member.guild
    config = get_guild_config(guild.id)
    channel_id = config.get("channel_id")
    role_ids = config.get("role_ids", [])
    
    added_roles_names = []
    
    if role_ids:
        for r_id in role_ids:
            role = guild.get_role(r_id)
            if role:
                try:
                    await member.add_roles(role)
                    added_roles_names.append(role.name)
                except: pass
    
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel and channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title=f"🚀 {guild.name} ได้รับการบูสต์!",
                description=f"ขอบคุณ **{member.mention}** ที่บูสต์ซิร์ฟเวอร์ของเรา! 💖",
                color=0xf47fff,
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            if guild.banner:
                embed.set_image(url=guild.banner.url)
            
            if added_roles_names:
                role_text = "\n".join([f"✅ {name}" for name in added_roles_names])
                embed.add_field(name="🎁 ยศที่ได้รับ", value=role_text, inline=False)
            
            embed.set_footer(text=f"Level: {guild.premium_tier} • Boosts: {guild.premium_subscription_count}")
            await channel.send(embed=embed)

    try:
        dm_embed = discord.Embed(title=f"ขอบคุณที่บูสต์ {guild.name} ครับ! 🚀", description="ระบบมอบยศพิเศษให้แล้วครับ", color=0xf47fff)
        await member.send(embed=dm_embed)
    except: pass

async def handle_remove_boost(member):
    guild = member.guild
    config = get_guild_config(guild.id)
    channel_id = config.get("channel_id")
    role_ids = config.get("role_ids", [])
    
    removed_roles_names = []
    
    if role_ids:
        for r_id in role_ids:
            role = guild.get_role(r_id)
            if role and role in member.roles:
                try:
                    await member.remove_roles(role)
                    removed_roles_names.append(role.name)
                except: pass
    
    if channel_id: 
        channel = guild.get_channel(channel_id)
        if channel and channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title=f"🔴 {member.name} ยกเลิกเม็ดบูสต์เซิร์ฟเวอร์",
                description=f"น่าเสียดายจัง... **{member.mention}** ได้ทำการถอดเม็ดบูสต์ออกแล้ว 😢",
                color=0xff4d4d,
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)

            if guild.banner:
                embed.set_image(url=guild.banner.url)
            
            if removed_roles_names:
                role_text = "\n".join([f"❌ {name}" for name in removed_roles_names])
                embed.add_field(name="♻️ ระบบทำการดึงยศคืน", value=role_text, inline=False)
            else:
                embed.add_field(name="♻️ สถานะยศ", value="ไม่มียศที่ต้องดึงคืน", inline=False)

            embed.set_footer(text=f"Level: {guild.premium_tier} • Remaining: {guild.premium_subscription_count}")
            await channel.send(embed=embed)

# 🚀 เริ่มการทำงาน
keep_alive()

# 🔥 ดึง Token จาก .env หรือ Render Environment Variables
token = os.environ.get('TOKEN')

if token:
    bot.run(token)
else:
    print("❌ Error: ไม่พบ TOKEN! อย่าลืมตั้งค่าใน .env หรือ Render Environment Variables")
      
