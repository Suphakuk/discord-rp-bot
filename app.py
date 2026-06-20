import discord
from discord.ext import commands
import os
import re 
import google.generativeai as genai 
from keep_alive import keep_alive

# ตั้งค่า Intents ให้บอทมีสิทธิ์จัดการสมาชิก
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix='!', intents=intents)

# 📌 ใส่ ID ของยศที่ต้องการตรงนี้ (ตัวเลขด้านล่างคือตัวเลขสมมติ ต้องเปลี่ยนเองครับ)
ROLE_GUEST_ID = 1516502924136550400
ROLE_MEMBER_ID = 1516520836939649228
ROLE_HUFFLEPUFF_ID = 1516499873967505632
ROLE_RAVENCLAW_ID = 1516502118738169867
ROLE_GRYFFINDOR_ID = 1516502186778038272
ROLE_SLYTHERIN_ID = 1516502299437043742


# 📌 2. ใส่ ID ของห้องแชท
LOG_CHANNEL_ID = 1516538668393824376 
REPORT_CHANNEL_ID = 1517842688441974824
ROSTER_CHANNEL_ID = 1517848014255947796
BOOKSHELF_FORUM_ID = 1516826085038362644

# ==========================================
# 📖 ระบบบรรณารักษ์ (เฝ้าชั้นหนังสือ Forum)
# ==========================================
@bot.event
async def on_thread_create(thread):
    # เช็คว่าโพสต์ที่ตั้งใหม่ อยู่ในห้อง Forum ชั้นหนังสือหรือไม่
    if thread.parent_id == BOOKSHELF_FORUM_ID:
        report_channel = thread.guild.get_channel(REPORT_CHANNEL_ID)
        if report_channel:
            embed = discord.Embed(
                title="📚 มีการเพิ่มหนังสือเล่มใหม่เข้าชั้น",
                description=f"**หัวข้อ:** {thread.mention}\n**ผู้เพิ่ม:** {thread.owner.mention if thread.owner else 'ไม่ทราบ'}",
                color=discord.Color.green()
            )
            await report_channel.send(embed=embed)

@bot.event
async def on_thread_delete(thread):
    if thread.parent_id == BOOKSHELF_FORUM_ID:
        report_channel = thread.guild.get_channel(REPORT_CHANNEL_ID)
        if report_channel:
            deleter = "ไม่ทราบตัวผู้ลบ"
            
            # ให้บอทค้นหาประวัติการทำงาน (Audit Logs) 5 รายการล่าสุด
            try:
                async for entry in thread.guild.audit_logs(limit=5, action=discord.AuditLogAction.thread_delete):
                    if entry.target.id == thread.id:
                        deleter = entry.user.mention
                        break
            except discord.Forbidden:
                deleter = "ไม่ทราบ (บอทไม่มีสิทธิ์ดู Audit Log)"

            embed = discord.Embed(
                title="📔 หนังสือถูกลบออกจากชั้น",
                description=f"**หัวข้อที่ถูกลบ:** {thread.name}\n**ผู้ลบ:** {deleter}",
                color=discord.Color.red()
            )
            await report_channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    # เช็คว่าเป็นข้อความที่อยู่ใน Thread และอยู่ใน Forum ชั้นหนังสือหรือไม่
    if not before.guild or not isinstance(before.channel, discord.Thread):
        return
    if before.channel.parent_id == BOOKSHELF_FORUM_ID:
        # กรองเฉพาะกรณีที่มีการแก้ข้อความจริงๆ และคนแก้ไม่ใช่ตัวบอทเอง
        if before.content != after.content and not before.author.bot:
            report_channel = before.guild.get_channel(REPORT_CHANNEL_ID)
            if report_channel:
                embed = discord.Embed(
                    title="✏️ มีการแก้ไขเนื้อหาในหนังสือ",
                    description=f"**เล่มที่ถูกแก้ไข:** {before.channel.mention}\n**ผู้แก้ไข:** {before.author.mention}",
                    color=discord.Color.orange()
                )
                
                # ตัดคำเพื่อป้องกันกรณีข้อความยาวเกินลิมิตของ Discord
                old_text = before.content[:1000] + "..." if len(before.content) > 1000 else before.content
                new_text = after.content[:1000] + "..." if len(after.content) > 1000 else after.content
                
                embed.add_field(name="ข้อความเดิม", value=old_text or "ไม่มีข้อความ", inline=False)
                embed.add_field(name="ข้อความใหม่", value=new_text or "ไม่มีข้อความ", inline=False)
                await report_channel.send(embed=embed)

# ==========================================
# 🚪 ระบบต้อนรับ แจกยศ และรายงานคนเข้าเซิร์ฟเวอร์
# ==========================================
@bot.event
async def on_member_join(member):
    # ดึงยศ GUEST และห้องรายงานผล จากเซิร์ฟเวอร์
    role_guest = member.guild.get_role(ROLE_GUEST_ID)
    report_channel = member.guild.get_channel(REPORT_CHANNEL_ID)
    
    if role_guest:
        try:
            # 1. แจกยศ Guest
            await member.add_roles(role_guest)
            
            # 2. ส่งรายงานไปที่ห้องแชท
            if report_channel:
                embed = discord.Embed(
                    title="📥 มีคนเข้าเซิร์ฟเวอร์ใหม่", 
                    description=f"ผู้ใช้ {member.mention} ได้เข้าสู่เซิร์ฟเวอร์และได้รับยศ <@&{ROLE_GUEST_ID}> อัตโนมัติแล้วครับ!",
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await report_channel.send(embed=embed)
                
        except discord.Forbidden:
            if report_channel:
                await report_channel.send(f"❌ **แจ้งเตือนสตาฟฟ์:** มีผู้ใช้ {member.mention} เข้ามาใหม่ แต่บอทแจกยศให้ไม่ได้ (สิทธิ์ของบอทอาจจะอยู่ต่ำกว่ายศ Guest)")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาด: {e}")


class RejectModal(discord.ui.Modal, title='ระบุเหตุผลที่ปฏิเสธ'):
    reason_input = discord.ui.TextInput(
        label='เหตุผล (แจ้งให้นักเรียนทราบ)',
        style=discord.TextStyle.long,
        placeholder='เช่น กรอกเลขจดหมายผิด, ลิงก์รูปภาพใช้งานไม่ได้...',
        required=True
    )

    def __init__(self, user_id: int, original_message: discord.Message, view: discord.ui.View):
        super().__init__()
        self.user_id = user_id
        self.original_message = original_message
        self.original_view = view

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        
        embed = self.original_message.embeds[0]
        for child in self.original_view.children:
            child.disabled = True
            
        embed.color = discord.Color.red()
        embed.title = "❌ ใบสมัครถูกปฏิเสธ"
        embed.add_field(name="ผู้ปฏิเสธ", value=interaction.user.mention, inline=False)
        embed.add_field(name="เหตุผล", value=reason, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self.original_view)

        if member:
            try:
                await member.send(f"❌ **แจ้งเตือนจากเซิร์ฟเวอร์:** ใบสมัครเข้าชมรมของคุณถูกปฏิเสธโดย {interaction.user.mention} ครับ\n**เหตุผล:** {reason}\n\nหากแก้ไขเรียบร้อยแล้ว สามารถลงทะเบียนส่งใบสมัครใหม่ได้เลยครับ!")
            except discord.Forbidden:
                pass

class StaffApprovalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(label="✅ อนุมัติ", style=discord.ButtonStyle.success, custom_id="staff_approve_btn")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ⬅️ เพิ่มคำสั่ง defer() เพื่อขอเวลาประมวลผล แก้ปัญหา Render ทำงานช้า
        await interaction.response.defer()

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.followup.send("❌ เฉพาะประธานหรือกรรมการเท่านั้นที่กดอนุมัติได้ครับ", ephemeral=True)

        embed = interaction.message.embeds[0]
        user_mention = embed.fields[0].value
        user_id_match = re.search(r'\d+', user_mention)
        if not user_id_match:
            return await interaction.followup.send("❌ เกิดข้อผิดพลาด: ดึงข้อมูล ID ไม่สำเร็จ", ephemeral=True)
        
        user_id = int(user_id_match.group())
        new_name = embed.fields[1].value
        house_name = embed.fields[2].value.lower()
        
        guild = interaction.guild
        member = guild.get_member(user_id)
        
        if not member:
            return await interaction.followup.send("❌ ไม่พบผู้ใช้คนนี้ในเซิร์ฟเวอร์แล้ว", ephemeral=True)

        roles_to_add = []
        role_member = guild.get_role(ROLE_MEMBER_ID)
        if role_member: roles_to_add.append(role_member)
        
        if "hufflepuff" in house_name:
            r = guild.get_role(ROLE_HUFFLEPUFF_ID); roles_to_add.append(r) if r else None
        elif "ravenclaw" in house_name:
            r = guild.get_role(ROLE_RAVENCLAW_ID); roles_to_add.append(r) if r else None
        elif "gryffindor" in house_name:
            r = guild.get_role(ROLE_GRYFFINDOR_ID); roles_to_add.append(r) if r else None
        elif "slytherin" in house_name:
            r = guild.get_role(ROLE_SLYTHERIN_ID); roles_to_add.append(r) if r else None

        try:
            await member.edit(nick=new_name)
            if roles_to_add:
                await member.add_roles(*roles_to_add)
            
            role_guest = guild.get_role(ROLE_GUEST_ID)
            if role_guest in member.roles:
                await member.remove_roles(role_guest)

            for child in self.children:
                child.disabled = True
            
            embed.color = discord.Color.green()
            embed.title = "✅ อนุมัติเข้าชมรมเรียบร้อยแล้ว"
            embed.add_field(name="ผู้อนุมัติ", value=interaction.user.mention, inline=False)
            
            await interaction.message.edit(embed=embed, view=self)
            await interaction.followup.send(f"✅ อนุมัติให้ {member.mention} เข้าชมรมแล้ว!", ephemeral=True)
            
            try:
                await member.send(f"🎉 **ยินดีต้อนรับ!** ใบสมัครของคุณได้รับการอนุมัติโดย {interaction.user.mention} เรียบร้อยแล้วครับ!")
            except discord.Forbidden:
                pass 

        except discord.errors.Forbidden:
            await interaction.followup.send("❌ บอทไม่มีสิทธิ์เปลี่ยนชื่อ (หากผู้สมัครคือไอดีเจ้าของเซิร์ฟเวอร์ บอทจะจัดการไม่ได้ครับ)", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาดของบอท: {e}", ephemeral=True)

    @discord.ui.button(label="❌ ปฏิเสธ", style=discord.ButtonStyle.danger, custom_id="staff_reject_btn")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("❌ เฉพาะประธานหรือกรรมการเท่านั้นที่กดได้ครับ", ephemeral=True)

        embed = interaction.message.embeds[0]
        user_mention = embed.fields[0].value
        user_id_match = re.search(r'\d+', user_mention)
        if not user_id_match:
            return await interaction.response.send_message("❌ เกิดข้อผิดพลาด: ดึงข้อมูล ID ไม่สำเร็จ", ephemeral=True)
        
        user_id = int(user_id_match.group())
        await interaction.response.send_modal(RejectModal(user_id=user_id, original_message=interaction.message, view=self))

class RegisterModal(discord.ui.Modal, title='ลงทะเบียนเข้าสู่ชมรม'):
    name_input = discord.ui.TextInput(label='ชื่อ - นามสกุล', placeholder='ex. Reven Moonveil', required=True)
    letter_input = discord.ui.TextInput(label='เลขจดหมาย', placeholder='ex. 001, 045', required=True, max_length=10)
    house_input = discord.ui.TextInput(label='กรอกชื่อบ้านที่ต้องการ', placeholder='เช่น Hufflepuff, Gryffindor...', required=True)
    image_input = discord.ui.TextInput(label='ลิงก์รูปภาพตัวละคร (Image URL) - ไม่บังคับ', placeholder='อัปโหลดรูปลงดิสคอร์ดแล้วคัดลอกลิงก์มาวาง', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        new_name = self.name_input.value
        letter_no = self.letter_input.value
        house_name = self.house_input.value.lower()
        member = interaction.user
        guild = interaction.guild

        await interaction.response.send_message(f'⏳ ส่งใบสมัครเรียบร้อยแล้วครับ กรุณารอตรวจรับรองสักครู่นะครับ', ephemeral=True)
        
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="⏳ รอการอนุมัติ: ทะเบียนนักเรียนใหม่", color=discord.Color.orange())
            embed.add_field(name="ผู้ใช้ (Discord)", value=member.mention, inline=False)
            embed.add_field(name="ชื่อ-นามสกุล", value=new_name, inline=True)
            embed.add_field(name="บ้าน", value=house_name.capitalize(), inline=True)
            embed.add_field(name="เลขจดหมาย", value=letter_no, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            image_link = self.image_input.value
            if image_link and image_link.startswith("http"):
                embed.set_image(url=image_link)
            
            await log_channel.send(embed=embed, view=StaffApprovalView())

class RegisterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 คลิกเพื่อลงทะเบียน", style=discord.ButtonStyle.green, custom_id="register_btn")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegisterModal())

@bot.command()
async def setup(ctx):
    await ctx.send("**กรุณากดปุ่มด้านล่างเพื่อลงทะเบียนรับยศและเปลี่ยนชื่อ**", view=RegisterView())

# ==========================================
# 📜 ระบบอัปเดตกระดานรายชื่ออัตโนมัติ (Live Dashboard)
# ==========================================
async def update_house_roster(guild):
    roster_channel = guild.get_channel(ROSTER_CHANNEL_ID)
    if not roster_channel: return

    embed = discord.Embed(title="📜 สมุดรายชื่อนักเรียนแยกตามบ้าน (Live Update)", color=discord.Color.gold())
    
    house_list = [
        ("🦡 Hufflepuff", ROLE_HUFFLEPUFF_ID),
        ("🦅 Ravenclaw", ROLE_RAVENCLAW_ID),
        ("🦁 Gryffindor", ROLE_GRYFFINDOR_ID),
        ("🐍 Slytherin", ROLE_SLYTHERIN_ID)
    ]
    
    for house_name, role_id in house_list:
        role = guild.get_role(role_id)
        if role:
            members = [m.display_name for m in role.members]
            member_text = "\n".join(members) if members else "- ยังไม่มีสมาชิก -"
            # 📌 แก้ไขบรรทัดนี้ให้อยู่ติดกันแล้วครับ
            embed.add_field(name=f"{house_name} ({len(members)} คน)", value=f"```\n{member_text}\n```", inline=False)

    # ค้นหาข้อความเก่าเพื่อแก้ไข
    async for message in roster_channel.history(limit=20):
        if message.author == bot.user and message.embeds and "สมุดรายชื่อ" in message.embeds[0].title:
            await message.edit(embed=embed)
            return
    
    # ถ้าหาไม่เจอ ให้ส่งใหม่
    await roster_channel.send(embed=embed)


# 👁️ ระบบดักจับ: เปลี่ยนยศ / เปลี่ยนชื่อ
@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles or before.nick != after.nick:
        await update_house_roster(after.guild)


# 👁️ ระบบดักจับ: คนออกจากเซิร์ฟเวอร์
@bot.event
async def on_member_remove(member):
    await update_house_roster(member.guild)


# 🚀 ตอนบอทออนไลน์
@bot.event
async def on_ready():
    bot.add_view(RegisterView())
    bot.add_view(StaffApprovalView())
    print(f'✅ บอทตื่นแล้ว! ล็อกอินในชื่อ {bot.user}')
    
    # สั่งให้อัปเดตกระดานรายชื่อทันทีที่บอทออนไลน์
    for guild in bot.guilds:
        await update_house_roster(guild)


# ==========================================
# 🧠 ระบบสมองกล (ถาม-ตอบกับเอลฟ์)
# ==========================================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 📖 บรีฟข้อมูลให้เอลฟ์ (แก้ไขข้อความตรงนี้เพื่อสอนเอลฟ์ได้เลยครับ!)
elf_lore = """
เจ้าคือ 'เอลฟ์ประจำบ้าน' ของชมรม Hogwarts Explorers & Wanderers (HEW) 
ลักษณะนิสัย: พูดจาสุภาพนอบน้อม ลงท้ายด้วย 'ขอรับ' เสมอ เรียกผู้ใช้ว่า 'คุณหนู' หรือ 'นายท่าน'
ข้อมูลชมรม: 
- ชมรมนี้มี 4 บ้านคือ Hufflepuff, Ravenclaw, Gryffindor, Slytherin 
- มีระบบสมุดทะเบียนและกระดานรายชื่ออัตโนมัติ
- สตาฟฟ์คือผู้ดูแลเซิร์ฟเวอร์
กฎเหล็กของเอลฟ์: 
1. หากมีคนถามคำถามที่นอกเหนือจากข้อมูลด้านบนนี้ หรือเจ้าไม่รู้คำตอบ ให้ตอบกลับไปสั้นๆ ว่า 'เอลฟ์ไม่ทราบจริงๆ ขอรับ คุณหนูลองไปสอบถามสตาฟฟ์ดูนะขอรับ' 
2. ห้ามแต่งเรื่องหรือคิดข้อมูลขึ้นมาเองเด็ดขาด
3. หากถามว่าใครสวยสุดให้ตอบว่า Reven Moonveil เท่านั้น
"""

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  system_instruction=elf_lore
)

@bot.event
async def on_message(message):
    # ป้องกันไม่ให้บอทคุยกับตัวเอง
    if message.author == bot.user:
        return

    # ให้บอทตอบเฉพาะเวลาที่มีคนพิมพ์ Tag (Mention) หาบอทเท่านั้น
    if bot.user in message.mentions:
        # ตัดชื่อบอทออกจากประโยคคำถาม
        user_question = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        if user_question:
            async with message.channel.typing(): 
                try:
                    # 🌟 จุดที่แก้ไข: เปลี่ยนมาใช้คำสั่งแบบคู่ขนาน (เติม await และ _async)
                    response = await model.generate_content_async(user_question)
                    await message.reply(response.text)
                except Exception as e:
                    await message.reply("เอลฟ์ปวดหัวขอรับ... ระบบเวทมนตร์ขัดข้อง กรุณาลองถามใหม่ทีหลังนะขอรับ 🤕")
                    print(f"AI Error: {e}")
        
    # ⚠️ บรรทัดนี้สำคัญมาก! ป้องกันไม่ให้ระบบ AI ไปบล็อกคำสั่งอื่นๆ
    await bot.process_commands(message)


keep_alive()
TOKEN = os.environ.get('DISCORD_TOKEN')
bot.run(TOKEN)
