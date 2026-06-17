import discord
from discord.ext import commands
import os
import re 
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


# 📌 2. ใส่ ID ของห้องแชทที่จะให้บอทส่งประวัติลงสมุดทะเบียน
LOG_CHANNEL_ID = 1516538668393824376  # ⬅️ เปลี่ยนเลขห้องตรงนี้

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

@bot.event
async def on_ready():
    bot.add_view(RegisterView())
    bot.add_view(StaffApprovalView())
    print(f'✅ บอทตื่นแล้ว! ล็อกอินในชื่อ {bot.user}')

@bot.command()
async def setup(ctx):
    await ctx.send("**กรุณากดปุ่มด้านล่างเพื่อลงทะเบียนรับยศและเปลี่ยนชื่อ**", view=RegisterView())

keep_alive()
TOKEN = os.environ.get('DISCORD_TOKEN')
bot.run(TOKEN)
