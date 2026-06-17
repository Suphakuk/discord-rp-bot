import discord
from discord.ext import commands
import os 
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
LOG_CHANNEL_ID = 123456789012345678  # ⬅️ เปลี่ยนเลขห้องตรงนี้

# สร้างหน้าต่างฟอร์ม (Modal) ให้คนกรอก
class RegisterModal(discord.ui.Modal, title='ลงทะเบียนเข้าสู่ชมรม'):
    name_input = discord.ui.TextInput(
        label='ชื่อ - นามสกุล',
        placeholder='ex. Reven Moonveil',
        required=True
    )
    letter_input = discord.ui.TextInput(
        label='เลขจดหมาย',
        placeholder='ex. AIN201',
        required=True,
        max_length=10
    )
    house_input = discord.ui.TextInput(
        label='กรอกชื่อบ้านที่ตนเองอยู่', 
        placeholder='เช่น Hufflepuff, Gryffindor, Ravenclaw, Slytherin',
        required=True
    )
    image_input = discord.ui.TextInput(
        label='ลิงก์รูปภาพตัวละคร (Image URL) - ไม่บังคับ',
        placeholder='อัปโหลดรูปลงดิสคอร์ดแล้วคัดลอกลิงก์มาวางที่นี่',
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        new_name = self.name_input.value
        letter_no = self.letter_input.value
        house_name = self.house_input.value.lower()
        member = interaction.user
        guild = interaction.guild

        role_member = guild.get_role(ROLE_MEMBER_ID)
        roles_to_add = [role_member] if role_member else []
        
        if "hufflepuff" in house_name:
            role = guild.get_role(ROLE_HUFFLEPUFF_ID)
            if role: roles_to_add.append(role)
        elif "ravenclaw" in house_name:
            role = guild.get_role(ROLE_RAVENCLAW_ID)
            if role: roles_to_add.append(role)
        elif "gryffindor" in house_name:
            role = guild.get_role(ROLE_GRYFFINDOR_ID)
            if role: roles_to_add.append(role)
        elif "slytherin" in house_name:
            role = guild.get_role(ROLE_SLYTHERIN_ID)
            if role: roles_to_add.append(role)

        try:
            # 1. เปลี่ยนชื่อ และ แจกยศ
            await member.edit(nick=new_name)
            if roles_to_add:
                await member.add_roles(*roles_to_add)
            
            # 2. ถอดยศ GUEST ออก
            role_guest = guild.get_role(ROLE_GUEST_ID)
            if role_guest in member.roles:
                await member.remove_roles(role_guest)
            
            # 3. แจ้งเตือนคนกดว่าสำเร็จ
            await interaction.response.send_message(f'✅ ลงทะเบียนสำเร็จ! **{new_name}** ได้รับเข็มกลัดและเข้าสู่ชมรมเรียบร้อยแล้วครับ', ephemeral=True)
            
            # 4. ส่งข้อมูลเข้าห้องสมุดทะเบียน
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(title="📝 ทะเบียนนักเรียนใหม่", color=discord.Color.green())
                embed.add_field(name="ผู้ใช้ (Discord)", value=member.mention, inline=False)
                embed.add_field(name="ชื่อ-นามสกุล", value=new_name, inline=True)
                embed.add_field(name="บ้าน", value=house_name.capitalize(), inline=True)
                embed.add_field(name="เลขจดหมาย", value=letter_no, inline=True)
                embed.set_thumbnail(url=member.display_avatar.url)
                
                # โชว์รูปใหญ่ถ้าใส่ลิงก์รูปมา
                image_link = self.image_input.value
                if image_link: 
                    if image_link.startswith("http"):
                        embed.set_image(url=image_link)
                
                await log_channel.send(embed=embed)

        except discord.errors.Forbidden:
            await interaction.response.send_message('❌ เกิดข้อผิดพลาด: ยศของบอทอยู่ต่ำกว่าผู้ใช้ หรือบอทไม่มีสิทธิ์จัดการยศ', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'❌ เกิดข้อผิดพลาด: {e} ติดต่อประธานชมรม', ephemeral=True)

# โค้ดส่วนนี้แหละครับที่หายไป (ตัวสร้างปุ่ม)
class RegisterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 คลิกเพื่อลงทะเบียน", style=discord.ButtonStyle.green, custom_id="register_btn")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegisterModal())

# คำสั่งสำหรับสตาฟฟ์ เสกปุ่มลงทะเบียนออกมา...
@bot.command()
async def setup(ctx):
    await ctx.send("**กรุณากดปุ่มด้านล่างเพื่อลงทะเบียนรับยศและเปลี่ยนชื่อ**", view=RegisterView())

keep_alive()
TOKEN = os.environ.get('DISCORD_TOKEN')
bot.run(TOKEN)